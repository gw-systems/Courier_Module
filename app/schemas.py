from pydantic import BaseModel, Field, field_validator
from typing import Literal, Dict, Optional
from datetime import datetime

class RateRequest(BaseModel):
    source_pincode: int = Field(..., description="6-digit origin pincode")
    dest_pincode: int = Field(..., description="6-digit destination pincode")
    weight: float = Field(..., gt=0, lt=1000, description="Weight in kg")
    is_cod: bool = False
    order_value: float = Field(0.0, ge=0)
    # Using Literal ensures ONLY these three strings are accepted
    mode: Literal["Both", "Surface", "Air"] = "Both"

    @field_validator('source_pincode', 'dest_pincode')
    @classmethod
    def validate_pincodes(cls, v: int) -> int:
        if not (100000 <= v <= 999999):
            raise ValueError('Pincode must be exactly 6 digits.')
        return v

# --- NEW: Breakdown Nested Schema ---
class CostBreakdown(BaseModel):
    base_forward: float
    additional_weight: float
    cod: float
    gst: float
    applied_gst_rate: str

# --- Updated: To match your engine.py output exactly ---
class CarrierResponse(BaseModel):
    carrier: str
    total_cost: float
    breakdown: CostBreakdown
    applied_zone: str  # Important for user transparency
    mode: str


# --- Zone Rates Schema ---
class ZoneRates(BaseModel):
    z_a: float = Field(..., gt=0, description="Zone A rate (must be positive)")
    z_b: float = Field(..., gt=0, description="Zone B rate (must be positive)")
    z_c: float = Field(..., gt=0, description="Zone C rate (must be positive)")
    z_d: float = Field(..., gt=0, description="Zone D rate (must be positive)")
    z_f: float = Field(..., gt=0, description="Zone E/F rate (must be positive)")


# --- New Carrier Schema ---
class NewCarrier(BaseModel):
    carrier_name: str = Field(..., min_length=1, description="Unique carrier name")
    mode: Literal["Surface", "Air"] = Field(..., description="Shipping mode")
    min_weight: float = Field(..., gt=0, description="Minimum weight in kg")
    forward_rates: ZoneRates = Field(..., description="Forward shipping rates per zone")
    additional_rates: ZoneRates = Field(..., description="Additional weight rates per zone")
    cod_fixed: float = Field(..., ge=0, description="Fixed COD fee")
    cod_percent: float = Field(..., ge=0, le=1, description="COD percentage (0-1)")
    active: bool = Field(default=True, description="Whether carrier is active")

    @field_validator('carrier_name')
    @classmethod
    def validate_carrier_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Carrier name cannot be empty')
        return v


# --- Order Management Schemas ---

class OrderCreate(BaseModel):
    # Recipient Details
    recipient_name: str = Field(..., min_length=1)
    recipient_contact: str = Field(..., min_length=10, description="Contact number (mandatory)")
    recipient_address: str = Field(..., min_length=5)
    recipient_pincode: int = Field(..., description="6-digit pincode")
    recipient_city: Optional[str] = None  # Auto-filled from pincode
    recipient_state: Optional[str] = None  # Auto-filled from pincode
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None

    # Sender Details
    sender_pincode: int = Field(..., description="6-digit sender pincode")
    sender_name: Optional[str] = None
    sender_address: Optional[str] = None
    sender_phone: Optional[str] = None

    # Box Details (all mandatory)
    weight: float = Field(..., gt=0, description="Actual weight in kg")
    length: float = Field(..., gt=0, description="Length in cm (mandatory)")
    width: float = Field(..., gt=0, description="Width in cm (mandatory)")
    height: float = Field(..., gt=0, description="Height in cm (mandatory)")

    # Payment
    payment_mode: Literal["cod", "prepaid"] = "prepaid"
    order_value: float = Field(0.0, ge=0)

    # Items Info
    item_type: Optional[str] = None
    sku: Optional[str] = None
    quantity: int = Field(1, gt=0)
    item_amount: float = Field(0.0, ge=0)

    # Additional
    notes: Optional[str] = None

    @field_validator('recipient_name', 'sender_name')
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return v
        # Allow alphabets, spaces, dots, and hyphens
        if not all(c.isalpha() or c in ' .-' for c in v):
            raise ValueError('Name must contain only letters, spaces, dots, and hyphens')
        return v

    @field_validator('recipient_contact')
    @classmethod
    def validate_contact(cls, v: str) -> str:
        v = v.strip()
        # Remove spaces and dashes
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.isdigit():
            raise ValueError('Contact number must contain only digits')
        if len(cleaned) != 10:
            raise ValueError('Contact number must be exactly 10 digits')
        return cleaned

    @field_validator('recipient_phone', 'sender_phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        cleaned = v.replace(' ', '').replace('-', '')
        if not cleaned.isdigit():
            raise ValueError('Phone number must contain only digits')
        if len(cleaned) != 10:
            raise ValueError('Phone number must be exactly 10 digits')
        return cleaned

    @field_validator('recipient_address', 'sender_address')
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return v if v == '' else None
        # Allow alphanumeric, spaces, and common punctuation
        if not all(c.isalnum() or c in ' .,/-#()' for c in v):
            raise ValueError('Address contains invalid characters')
        return v

    @field_validator('recipient_pincode', 'sender_pincode')
    @classmethod
    def validate_pincodes(cls, v: int) -> int:
        if not (100000 <= v <= 999999):
            raise ValueError('Pincode must be exactly 6 digits')
        return v

    @field_validator('recipient_email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None
        v = v.strip()
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v


class OrderUpdate(BaseModel):
    recipient_name: Optional[str] = None
    recipient_contact: Optional[str] = None
    recipient_address: Optional[str] = None
    recipient_pincode: Optional[int] = None
    recipient_city: Optional[str] = None
    recipient_state: Optional[str] = None
    recipient_phone: Optional[str] = None
    recipient_email: Optional[str] = None
    sender_pincode: Optional[int] = None
    sender_name: Optional[str] = None
    sender_address: Optional[str] = None
    sender_phone: Optional[str] = None
    weight: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    payment_mode: Optional[Literal["cod", "prepaid"]] = None
    order_value: Optional[float] = None
    item_type: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[int] = None
    item_amount: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[Literal["draft", "pending", "booked", "in_transit", "delivered", "cancelled"]] = None
    selected_carrier: Optional[str] = None
    mode: Optional[Literal["Surface", "Air"]] = None
    zone_applied: Optional[str] = None
    total_cost: Optional[float] = None


class OrderResponse(BaseModel):
    id: int
    order_number: str
    recipient_name: str
    recipient_contact: str
    recipient_address: str
    recipient_pincode: int
    recipient_city: Optional[str]
    recipient_state: Optional[str]
    recipient_phone: Optional[str]
    recipient_email: Optional[str]
    sender_pincode: int
    sender_name: Optional[str]
    sender_address: Optional[str]
    sender_phone: Optional[str]
    weight: float
    length: float
    width: float
    height: float
    volumetric_weight: Optional[float]
    applicable_weight: Optional[float]
    payment_mode: str
    order_value: float
    item_type: Optional[str]
    sku: Optional[str]
    quantity: int
    item_amount: float
    status: str
    selected_carrier: Optional[str]
    total_cost: Optional[float]
    cost_breakdown: Optional[Dict]
    awb_number: Optional[str]
    zone_applied: Optional[str]
    mode: Optional[str]
    created_at: datetime
    updated_at: datetime
    booked_at: Optional[datetime]
    notes: Optional[str]

    class Config:
        from_attributes = True


class CarrierSelectionRequest(BaseModel):
    order_ids: list[int] = Field(..., min_length=1, description="List of order IDs to book")
    carrier_name: str = Field(..., min_length=1)
    mode: Literal["Surface", "Air"] = Field(..., description="Shipping mode")