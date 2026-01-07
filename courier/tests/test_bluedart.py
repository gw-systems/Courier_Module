
import pytest
from courier import engine, zones
import json
import os

# Helper to load config
def load_carrier_config():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "master_card.json")
    with open(path, "r", encoding='utf-8') as f:
        data = json.load(f)
    # Return Blue Dart config
    for c in data:
        if c.get("carrier_name") == "Blue Dart":
            return c
    return {}

# Mock zones.get_bluedart_details to avoid dependency on full CSV for unit tests?
# Ideally we test with real data if available, but for stability let's mock specific cases if needed.
# However, integration test using the real CSV is better for this task.

def test_bluedart_serviceable_basic():
    """Test standard serviceable pincode (Delhi)"""
    config = load_carrier_config()
    
    # 110001 is NORTH, Non-EDL
    # Rate for NORTH is 9.5
    res = engine.calculate_cost(
        weight=10,
        source_pincode=421302, # Bhiwandi (Source logic assumes destination based routing for BlueDart)
        dest_pincode=110001,
        carrier_data=config,
        is_cod=False,
        order_value=5000
    )
    
    assert res["servicable"] is True
    assert res["zone"] == "Region: NORTH"
    # New Logic:
    # Base Freight: 95.0
    # Surcharges: 
    #   Docket: 0
    #   AWB: 300
    #   Fuel: 95 * 0.556 = 52.82
    #   FOD: 100
    #   Risk: 100
    #   Total Surcharges: 552.82
    #
    # Escalation: 15% on CAREEER PAYABLE BASE (95) = 14.25
    #
    # Customer Subtotal: 95 + 14.25 + 552.82 = 662.07
    # GST 18%: 119.17
    # Final: 781.24
    
    # Old logic was compounding 15% on everything. Now it's much lower margin.
    
    assert res["breakdown"]["base_freight"] == 95.0
    assert res["breakdown"]["fod_charge"] == 100
    assert res["breakdown"]["risk_charge"] == 100
    assert res["breakdown"]["profit_margin"] == 14.25

def test_bluedart_edl_charge():
    """Test EDL Pincode (121103 - 55km)"""
    config = load_carrier_config()
    
    # 121103: NORTH, EDL=Y, Dist=55
    # Matrix: 51-100km. Weight 10kg (Slab 100). Rate -> 825
    
    res = engine.calculate_cost(
        weight=10,
        source_pincode=421302,
        dest_pincode=121103,
        carrier_data=config,
        is_cod=False,
        order_value=1000
    )
    
    assert res["servicable"] is True
    assert res["breakdown"]["edl_charge"] == 825.0
    
    # Fuel should include EDL?
    # Base (95) + EDL (825) = 920
    # Fuel = 920 * 0.556 = 511.52
    assert res["breakdown"]["fuel_surcharge"] == 511.52
    
    # Escalation Check:
    # Logic: 15% on FREIGHT ONLY (95). Not on EDL (825)
    # 95 * 0.15 = 14.25
    assert res["breakdown"]["profit_margin"] == 14.25

def test_bluedart_cod_dod():
    """Test COD and DOD charges"""
    config = load_carrier_config()
    
    # DOD: 0.5% or 200. Value 10000 -> 50. Min 200 -> 200.
    # COD: Should be skipped if DOD is present?
    # Our logic: if is_cod and dod_charge -> skip standard COD.
    
    res = engine.calculate_cost(
        weight=5,
        source_pincode=421302,
        dest_pincode=110001,
        carrier_data=config,
        is_cod=True,
        order_value=10000
    )
    
    
    assert res["breakdown"]["dod_charge"] == 200.0
    assert res["breakdown"]["cod_fee"] == 0 # Standard COD skipped

def test_bluedart_edl_special_region():
    """Test J&K Special Region EDL (Weight*15 vs 3000)"""
    config = load_carrier_config()
    
    # 114145: NORTH, JAMMU AND KASHMIR, Y, 50, N, 216
    # Rate: Max(10*15=150, 3000) -> 3000
    
    res = engine.calculate_cost(
        weight=10,
        source_pincode=421302,
        dest_pincode=114145, # J&K Pincode from CSV
        carrier_data=config,
        is_cod=False,
        order_value=1000
    )
    
    assert res["servicable"] is True
    assert res["breakdown"]["edl_charge"] == 3000.0

def test_bluedart_edl_overflow_dist():
    """Test EDL Overflow (Distance > 500km)"""
    config = load_carrier_config()
    
    # We need a pincode with >500km EDL.
    # CSV might not have one, so we mock zones.get_csv_region_details
    # Or inject a mock into the zones cache.
    
    # Ensure cache entry exists
    csv_file = "BlueDart_Servicable Pincodes.csv"
    if csv_file not in zones.CSV_CACHE:
        zones.CSV_CACHE[csv_file] = {}

    zones.CSV_CACHE[csv_file][999999] = {
        "REGION": "NORTH",
        "STATE": "HARYANA",
        "Extended Delivery Location": "Y",
        "EDL Distance": "600",
        "Embargo": "N"
    }
    
    # Dist 600. 
    # Charge A: 600 * 14 = 8400
    # Charge B: 10 * 5 = 50
    # Max -> 8400
    
    res = engine.calculate_cost(
        weight=10,
        source_pincode=421302,
        dest_pincode=999999,
        carrier_data=config,
        is_cod=False,
        order_value=1000
    )
    
    assert res["breakdown"]["edl_charge"] == 8400.0

def test_bluedart_edl_overflow_weight():
    """Test EDL Overflow (Weight > 1500kg)"""
    config = load_carrier_config()
    
    # Pincode with small distance but high weight.
    # 121103 (55km).
    # Weight 2000kg.
    
    # Charge A: 55 * 14 = 770
    # Charge B: 2000 * 5 = 10000
    # Max -> 10000
    
    res = engine.calculate_cost(
        weight=2000,
        source_pincode=421302,
        dest_pincode=121103,
        carrier_data=config,
        is_cod=False,
        order_value=1000
    )
    
    assert res["breakdown"]["edl_charge"] == 10000.0

def test_bluedart_restricted_origin():
    """Test that Blue Dart is NOT available from non-Bhiwandi source"""
    config = load_carrier_config()
    
    # 110001 (Delhi) is NOT Bhiwandi
    res = engine.calculate_cost(
        weight=10,
        source_pincode=110001, 
        dest_pincode=400001,
        carrier_data=config,
        is_cod=False,
        order_value=1000
    )
    
    assert res["servicable"] is False
    assert "Service only available from bhiwandi" in res["error"]
