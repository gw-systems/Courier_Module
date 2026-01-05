import math
import json
import os
from courier import zones  # The refactored zones module

# 1. Load Global Settings
def load_json(filename):
    path = os.path.join(os.path.dirname(__file__), "config", filename)
    with open(path, "r") as f:
        return json.load(f)

SETTINGS = load_json("settings.json")

def calculate_cost(
    weight: float,
    source_pincode: int,
    dest_pincode: int,
    carrier_data: dict,
    is_cod: bool = False,
    order_value: float = 0,
):
    """
    Calculates shipping cost with industry-standard charge sequencing:
    1. Base Freight (zone/weight based)
    2. Carrier Surcharges (fuel, hamali, FOV, COD, docket)
    3. Subtotal
    4. Escalation (15% profit margin)
    5. GST (18%)
    6. Final Total
    
    Supports 3 routing models:
    - City-to-City (Per KG)
    - Zone Matrix (Per KG)
    - Standard Zonal (Slab Based)
    """
    
    # --- STEP 1: IDENTIFY ZONE ---
    zone_id, zone_desc, logic_type = zones.get_zone(source_pincode, dest_pincode, carrier_data)
    
    if not zone_id:
        return {
            "carrier": carrier_data["carrier_name"],
            "error": zone_desc,
            "servicable": False
        }

    # --- STEP 1.5: WEIGHT LIMIT CHECK ---
    max_weight = carrier_data.get("max_weight", 99999.0)
    # Also considering min_weight for strict filtering? 
    # Generally, paying for min weight is allowed (e.g. shipping 45kg on 50kg rate).
    # But max weight is a hard limit (e.g. bike can't carry 50kg).
    if weight > max_weight:
        return {
            "carrier": carrier_data["carrier_name"],
            "error": f"Weight {weight}kg exceeds limit ({max_weight}kg)",
            "servicable": False
        }

    # --- STEP 2: BASE FREIGHT CALCULATION ---
    routing = carrier_data.get("routing_logic", {})
    freight_min = carrier_data.get("min_freight", 0)
    
    freight_cost = 0
    breakdown = {}

    # MODEL A: Per KG Pricing (City-Specific or Matrix)
    if logic_type in ["city_specific", "matrix"]:
        rate_per_kg = 0
        if logic_type == "city_specific":
            rate_per_kg = routing.get("city_rates", {}).get(zone_id, 0)
        elif logic_type == "matrix":
            origin, dest = zone_id
            rate_per_kg = routing.get("zonal_rates", {}).get(origin, {}).get(dest, 0)
            
        charged_weight = max(weight, carrier_data.get("min_weight", 0))
        raw_freight = charged_weight * rate_per_kg
        freight_cost = max(raw_freight, freight_min)
        
        breakdown["rate_per_kg"] = rate_per_kg
        breakdown["charged_weight"] = charged_weight

    # MODEL B: Slab Based Pricing (Standard Zonal)
    elif logic_type == "standard":
        slab = carrier_data.get("min_weight", 0.5)
        
        # Support both old and new JSON formats
        if routing.get("zonal_rates"):
            forward_rates = routing["zonal_rates"].get("forward", {})
            additional_rates = routing["zonal_rates"].get("additional", {})
        else:
            forward_rates = carrier_data.get("forward_rates", {})
            additional_rates = carrier_data.get("additional_rates", {})
        
        base_rate = forward_rates.get(zone_id, 0)
        extra_rate = additional_rates.get(zone_id, 0)
        
        # Calculate freight
        freight_cost = base_rate
        if weight > slab:
            extra_weight = weight - slab
            slab_step = slab
            units = math.ceil(extra_weight / slab_step)
            extra_cost = units * extra_rate
            freight_cost += extra_cost
            breakdown["extra_weight_units"] = units
            breakdown["extra_weight_charge"] = extra_cost
            
        breakdown["base_slab_rate"] = base_rate
        breakdown["additional_rate"] = extra_rate

    breakdown["base_freight"] = round(freight_cost, 2)

    # --- STEP 3: CARRIER-SPECIFIC SURCHARGES ---
    fixed_fees = carrier_data.get("fixed_fees", {})
    var_fees = carrier_data.get("variable_fees", {})
    
    # 3.1 Docket Fee
    docket_fee = fixed_fees.get("docket_fee", 0)
    
    # 3.2 Fuel Surcharge (carrier-specific, applied on base freight)
    fuel_config = carrier_data.get("fuel_config", {})
    fuel_surcharge = 0
    
    if fuel_config.get("is_dynamic"):
        # Dynamic fuel based on diesel price
        base_diesel = fuel_config.get("base_diesel_price", 90)
        diesel_ratio = fuel_config.get("diesel_ratio", 0.625)
        # For now, use base price (in production, fetch current diesel price)
        current_diesel = base_diesel
        fuel_pct = (current_diesel - base_diesel) * diesel_ratio / 100
        fuel_surcharge = freight_cost * fuel_pct
    else:
        # Flat percentage
        fuel_pct = fuel_config.get("flat_percent", 0)
        fuel_surcharge = freight_cost * fuel_pct
    
    # 3.3 Hamali (Labor Charge)
    hamali_per_kg = var_fees.get("hamali_per_kg", 0)
    min_hamali = var_fees.get("min_hamali", 0)
    hamali_charge = max(weight * hamali_per_kg, min_hamali) if hamali_per_kg > 0 else 0
    
    # 3.4 FOV (Freight on Value / Insurance)
    fov_charge = 0
    if order_value > 0:
        fov_pct = var_fees.get("fov_insured_percent", 0)
        fov_min = var_fees.get("fov_min", 0)
        fov_charge = max(order_value * fov_pct, fov_min)
    
    # 3.5 COD Charges
    cod_fee = 0
    if is_cod:
        # Try new format first
        cod_fixed = fixed_fees.get("cod_fixed", 0)
        cod_percent = var_fees.get("cod_percent", 0)
        
        # Fallback to old format
        if cod_fixed == 0:
            cod_fixed = carrier_data.get("cod_fixed", 0)
        if cod_percent == 0:
            cod_percent = carrier_data.get("cod_percent", 0)
        
        # Normalize percentage (if > 1, assume it's like 1.5% not 0.015)
        if cod_percent > 1:
            cod_percent = cod_percent / 100
            
        cod_fee = max(cod_fixed, order_value * cod_percent)

    # --- STEP 4: SUBTOTAL (Before Escalation) ---
    subtotal = (
        freight_cost + 
        docket_fee + 
        fuel_surcharge + 
        hamali_charge + 
        fov_charge + 
        cod_fee
    )

    # --- STEP 5: ESCALATION (15% Profit Margin) ---
    escalation_rate = SETTINGS.get("ESCALATION_RATE", 0.15)
    escalation_amount = subtotal * escalation_rate
    amount_after_escalation = subtotal + escalation_amount

    # --- STEP 6: GST (18%) ---
    gst_rate = SETTINGS.get("GST_RATE", 0.18)
    gst_amount = amount_after_escalation * gst_rate
    final_total = amount_after_escalation + gst_amount

    # --- STEP 7: FINAL ASSEMBLY ---
    return {
        "carrier": carrier_data["carrier_name"],
        "zone": zone_desc,
        "total_cost": round(final_total, 2),
        "breakdown": {
            **breakdown,
            # Carrier Charges
            "docket_fee": round(docket_fee, 2),
            "fuel_surcharge": round(fuel_surcharge, 2),
            "hamali_charge": round(hamali_charge, 2),
            "fov_charge": round(fov_charge, 2),
            "cod_fee": round(cod_fee, 2),
            
            # Subtotals
            "subtotal": round(subtotal, 2),
            "escalation_rate": f"{escalation_rate * 100}%",
            "escalation_amount": round(escalation_amount, 2),
            "amount_after_escalation": round(amount_after_escalation, 2),
            
            # Tax
            "gst_rate": f"{gst_rate * 100}%",
            "gst_amount": round(gst_amount, 2),
            
            # Final
            "final_total": round(final_total, 2)
        },
        "servicable": True
    }
