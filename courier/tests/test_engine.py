"""
Tests for pricing calculation engine
Refactored for Multi-Carrier Logic (Per KG, Matrix, Slab)
Tests use Standard Zonal logic which uses the pincode_master.csv database.
"""

import pytest
from courier.engine import calculate_cost

# --- MOCK DATA ---
# Standard Model (Slab) - Shadowfax style
# Uses Standard Zonal logic which relies on pincode_master.csv
CARRIER_STANDARD = {
    "carrier_name": "Standard Carrier",
    "min_weight": 0.5,
    "routing_logic": {
        "is_city_specific": False,
        "zonal_rates": {
            "forward": {"z_a": 30, "z_b": 40, "z_c": 50, "z_d": 60, "z_f": 80},
            "additional": {"z_a": 20, "z_b": 25, "z_c": 30, "z_d": 35, "z_f": 50}
        }
    },
    "fixed_fees": {"docket_fee": 20, "cod_fixed": 30},
    "variable_fees": {"cod_percent": 0.02},  # 2%
    "fuel_config": {}
}

# Standard carrier with heavier weight slab (like Delhivery 10kg)
CARRIER_HEAVY = {
    "carrier_name": "Heavy Carrier",
    "min_weight": 10.0,
    "routing_logic": {
        "is_city_specific": False,
        "zonal_rates": {
            "forward": {"z_a": 200, "z_b": 250, "z_c": 300, "z_d": 350, "z_f": 450},
            "additional": {"z_a": 18, "z_b": 22, "z_c": 26, "z_d": 30, "z_f": 40}
        }
    },
    "fixed_fees": {"docket_fee": 0},
    "variable_fees": {},
    "fuel_config": {}
}

# Real Pincodes for Lookup (All verified to exist in pincode_master.csv)
MUMBAI = 400001       # Maharashtra, Metro
DELHI = 110001        # Delhi, Metro
PUNE = 411001         # Maharashtra, Metro
NASHIK = 422001       # Maharashtra, Non-Metro (for Zone B testing)
CHENNAI = 600001      # Tamil Nadu, Metro
KOLKATA = 700001      # West Bengal, Metro


class TestZoneDetermination:
    """Tests that verify zone logic works correctly."""
    
    def test_zone_a_metro_to_metro(self):
        """Mumbai -> Delhi (both metros) should be Zone A."""
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        assert res["servicable"] is True
        assert res["zone"] == "Zone A (Metropolitan)"
    
    def test_zone_b_same_state(self):
        """Mumbai -> Nashik (same state, non-metro) should be Zone B."""
        res = calculate_cost(0.5, MUMBAI, NASHIK, CARRIER_STANDARD, is_cod=False)
        
        assert res["servicable"] is True
        assert res["zone"] == "Zone B (Regional)"
    
    def test_zone_c_intercity(self):
        """Chennai -> Kolkata (different metros, different states) - Zone C or A."""
        res = calculate_cost(0.5, CHENNAI, KOLKATA, CARRIER_STANDARD, is_cod=False)
        
        assert res["servicable"] is True
        # Both are metros, so should be Zone A
        assert res["zone"] == "Zone A (Metropolitan)"


class TestStandardSlabPricing:
    """Tests for slab-based pricing calculations."""
    
    def test_base_slab_only(self):
        """Weight at or below min_weight uses base forward rate only."""
        # 0.5kg shipment, Mumbai->Delhi (Zone A)
        # Forward rate z_a = 30
        # Docket = 20
        # Freight = 30
        # Transport cost = 30
        # Courier Payable = 30 + 20 = 50
        
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        assert res["servicable"] is True
        assert res["breakdown"]["base_slab_rate"] == 30
        assert "extra_weight_charge" not in res["breakdown"]
        assert res["breakdown"]["base_transport_cost"] == 30
        assert res["breakdown"]["docket_fee"] == 20
        assert res["breakdown"]["courier_payable"] == 50
    
    def test_extra_weight_calculation(self):
        """Weight above min_weight incurs additional charges."""
        # 1.5kg shipment, Mumbai->Delhi (Zone A)
        # Base slab = 0.5kg, forward = 30
        # Extra weight = 1.0kg, 2 units @ 20 each = 40
        # Freight = 30 + 40 = 70
        # Docket = 20
        # Courier Payable = 70 + 20 = 90
        
        res = calculate_cost(1.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        assert res["servicable"] is True
        assert res["breakdown"]["base_slab_rate"] == 30
        assert res["breakdown"]["extra_weight_units"] == 2
        assert res["breakdown"]["extra_weight_charge"] == 40
        assert res["breakdown"]["base_transport_cost"] == 70
        assert res["breakdown"]["courier_payable"] == 90
    
    def test_heavy_carrier_slab(self):
        """Test carrier with larger min_weight slab."""
        # 15kg shipment with 10kg min slab
        # Forward rate z_a = 200
        # Extra weight = 5kg = 5 units @ 18 = 90
        # Total freight = 290
        # Docket = 0
        # Courier Payable = 290
        
        res = calculate_cost(15, MUMBAI, DELHI, CARRIER_HEAVY, is_cod=False)
        
        assert res["servicable"] is True
        assert res["breakdown"]["base_slab_rate"] == 200
        assert res["breakdown"]["extra_weight_units"] == 5
        assert res["breakdown"]["extra_weight_charge"] == 90
        assert res["breakdown"]["base_transport_cost"] == 290
        assert res["breakdown"]["courier_payable"] == 290


class TestCODLogic:
    """Tests for COD fee calculations."""
    
    def test_cod_fixed_fee_higher(self):
        """When fixed COD fee > percentage, use fixed fee."""
        # Fixed = 30, Percent = 2% of 1000 = 20
        # Max(30, 20) = 30
        
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=True, order_value=1000)
        assert res["breakdown"]["cod_fee"] == 30
    
    def test_cod_percent_higher(self):
        """When percentage COD > fixed, use percentage."""
        # Fixed = 30, Percent = 2% of 5000 = 100
        # Max(30, 100) = 100
        
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=True, order_value=5000)
        assert res["breakdown"]["cod_fee"] == 100
    
    def test_no_cod_no_fee(self):
        """When is_cod=False, no COD fee should be charged."""
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False, order_value=5000)
        assert res["breakdown"]["cod_fee"] == 0


class TestPricingMarkups:
    """Tests for escalation and GST calculations."""
    
    def test_escalation_applied(self):
        """Verify escalation (profit margin) is applied."""
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        # Escalation is applied on freight_cost (base_transport - edl)
        # Default escalation is 15%
        assert res["breakdown"]["profit_margin"] > 0
        assert res["breakdown"]["escalation_amount"] == res["breakdown"]["profit_margin"]
    
    def test_gst_calculated(self):
        """Verify 18% GST is applied."""
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        # GST = 18%
        assert "18" in res["breakdown"]["gst_rate"]
        assert res["breakdown"]["gst_amount"] > 0
    
    def test_total_cost_structure(self):
        """Verify final_total = amount_before_tax + gst."""
        res = calculate_cost(0.5, MUMBAI, DELHI, CARRIER_STANDARD, is_cod=False)
        
        expected_total = res["breakdown"]["amount_before_tax"] + res["breakdown"]["gst_amount"]
        assert abs(res["breakdown"]["final_total"] - expected_total) < 0.01
        assert res["total_cost"] == res["breakdown"]["final_total"]
