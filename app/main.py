from fastapi import FastAPI, HTTPException, APIRouter, Depends, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .schemas import RateRequest, NewCarrier
from .engine import calculate_cost
from .zones import get_zone_column
import json
import os
from dotenv import load_dotenv
import shutil
import logging
from logging.handlers import RotatingFileHandler

load_dotenv() # Loads the .env file

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Validate environment variables with strong password requirements
if not ADMIN_PASSWORD:
    raise RuntimeError(
        "CRITICAL: ADMIN_PASSWORD not set in .env file. "
        "Set a strong password (12+ characters, mix of letters/numbers/symbols)."
    )
elif len(ADMIN_PASSWORD) < 12:
    raise RuntimeError(
        "CRITICAL: ADMIN_PASSWORD is too weak. "
        "Password must be at least 12 characters long."
    )
elif ADMIN_PASSWORD in ["Transportwale", "admin", "password", "12345678", "admin123"]:
    raise RuntimeError(
        "CRITICAL: ADMIN_PASSWORD is a common/default password. "
        "Use a strong, unique password for production."
    )
elif ADMIN_PASSWORD.isalpha() or ADMIN_PASSWORD.isdigit():
    raise RuntimeError(
        "CRITICAL: ADMIN_PASSWORD is too simple. "
        "Password must contain a mix of letters, numbers, and symbols."
    )

# --- 1. LOGGING CONFIGURATION ---
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = "app.log"

# Rotating file handler: 5MB per file, keeps 2 backups
my_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=2)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)

app_logger = logging.getLogger("root")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(my_handler)

# Also show logs in the console for development
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
app_logger.addHandler(console_handler)

# --- 2. GLOBAL PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RATE_CARD_PATH = os.path.join(BASE_DIR, "data", "rate_cards.json")

# --- 3. ADMIN ROUTER ---

async def verify_admin_token(x_admin_token: str = Header(None)):
    """
    Dependency to verify the admin password from the request header.
    """
    if x_admin_token != ADMIN_PASSWORD:
        app_logger.warning(f"UNAUTHORIZED_ACCESS_ATTEMPT: Invalid token provided.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Admin Token",
        )
    return x_admin_token

admin_router = APIRouter(
    prefix="/api/admin", 
    tags=["Admin"],
    dependencies=[Depends(verify_admin_token)]
)

@admin_router.get("/rates")
async def get_all_rates():
    with open(RATE_CARD_PATH, "r") as f:
        return json.load(f)

@admin_router.post("/rates/update")
async def update_rates(new_data: list[dict]):
    try:
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(new_data, f, indent=4)

        app_logger.info("ADMIN_ACTION: Rates updated successfully.")
        return {"status": "success", "message": "Rates updated successfully"}
    except Exception as e:
        app_logger.error(f"ADMIN_ERROR: Failed to update rates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update rates: {str(e)}")

@admin_router.post("/rates/add")
async def add_carrier(carrier: NewCarrier):
    """Add a new carrier to the rate cards"""
    try:
        # Load existing rates
        existing_rates = load_rates()

        # Check for duplicate carrier name
        carrier_names = [c.get("carrier_name", "").lower() for c in existing_rates]
        if carrier.carrier_name.lower() in carrier_names:
            app_logger.warning(f"ADMIN_ACTION: Duplicate carrier name attempted: {carrier.carrier_name}")
            raise HTTPException(
                status_code=400,
                detail=f"Carrier '{carrier.carrier_name}' already exists. Please use a unique name."
            )

        # Convert Pydantic model to dict for JSON serialization
        new_carrier_data = carrier.model_dump()

        # Append new carrier
        existing_rates.append(new_carrier_data)

        # Backup and save
        if os.path.exists(RATE_CARD_PATH):
            shutil.copy(RATE_CARD_PATH, RATE_CARD_PATH + ".bak")

        with open(RATE_CARD_PATH, "w") as f:
            json.dump(existing_rates, f, indent=4)

        app_logger.info(f"ADMIN_ACTION: New carrier added: {carrier.carrier_name}")
        return {
            "status": "success",
            "message": f"Carrier '{carrier.carrier_name}' added successfully",
            "carrier": new_carrier_data
        }

    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"ADMIN_ERROR: Failed to add carrier: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to add carrier: {str(e)}")

# --- 4. MAIN APP INITIALIZATION ---
app = FastAPI(
    title="LogiRate API",
    description="Shipping cost comparison engine for Indian logistics",
    version="1.0.0",
    contact={"email": "support@example.com"},
    license_info={"name": "MIT"}
)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)

# Mount static files
STATIC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

def load_rates():
    """Load rate cards with error handling"""
    try:
        if not os.path.exists(RATE_CARD_PATH):
            app_logger.warning(f"Rate card file not found at {RATE_CARD_PATH}, returning empty list")
            return []

        with open(RATE_CARD_PATH, "r") as f:
            return json.load(f)

    except json.JSONDecodeError as e:
        app_logger.error(f"Invalid JSON in rate card file: {e}")
        return []
    except Exception as e:
        app_logger.error(f"Unexpected error loading rate cards: {e}")
        return []


# --- 5. STARTUP VALIDATION ---
@app.on_event("startup")
async def startup_validation():
    """Validate critical resources on startup"""
    from .zones import PINCODE_LOOKUP

    if len(PINCODE_LOOKUP) == 0:
        app_logger.critical("STARTUP FAILED: No pincodes loaded from database")
        raise RuntimeError("Database initialization failed - no pincodes available")

    app_logger.info(f"Server started successfully - {len(PINCODE_LOOKUP)} pincodes loaded")

    rates = load_rates()
    if len(rates) == 0:
        app_logger.warning("No carrier rates loaded - API will return empty results")
    else:
        app_logger.info(f"{len(rates)} carrier rate cards loaded")


# --- 6. HEALTH CHECK ENDPOINT ---
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    from .zones import PINCODE_LOOKUP

    return {
        "status": "healthy",
        "pincode_db_loaded": len(PINCODE_LOOKUP) > 0,
        "pincode_count": len(PINCODE_LOOKUP),
        "rate_cards_loaded": len(load_rates()) > 0,
        "rate_card_count": len(load_rates())
    }


# --- 7. PUBLIC API ROUTES ---
@app.post("/compare-rates")
@limiter.limit("30/minute")
def compare_rates(request: Request, rate_request: RateRequest):
    zone_key, zone_label = get_zone_column(rate_request.source_pincode, rate_request.dest_pincode)

    rates = load_rates()
    results = []

    for carrier in rates:
        if not carrier.get("active", True):
            continue

        req_mode = rate_request.mode.lower()
        car_mode = carrier.get("mode", "Surface").lower()
        if req_mode != "both" and car_mode != req_mode:
            continue

        try:
            res = calculate_cost(
                weight=rate_request.weight,
                zone_key=zone_key,
                carrier_data=carrier,
                is_cod=rate_request.is_cod,
                order_value=rate_request.order_value
            )
            
            res["applied_zone"] = zone_label
            res["mode"] = carrier.get("mode", "Surface")
            results.append(res)
        except Exception as e:
            app_logger.error(f"CALCULATION_ERROR: Carrier {carrier.get('carrier_name')} failed. Error: {str(e)}")
            continue

    # Validate that we have results to return
    if not results:
        app_logger.warning(f"No carriers matched for mode: {rate_request.mode}")
        raise HTTPException(
            status_code=404,
            detail=f"No active carriers found for mode '{rate_request.mode}'. Please check carrier availability or try 'Both' mode."
        )

    return sorted(results, key=lambda x: x["total_cost"])