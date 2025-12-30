from pydantic import BaseModel, Field, field_validator
from typing import Literal, Dict

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