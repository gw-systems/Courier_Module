"""
Tests for pricing calculation engine (app/engine.py)
"""
import pytest
from app.engine import calculate_cost, SETTINGS


class TestCalculateCost:
    """Tests for calculate_cost function"""

    def test_base_rate_calculation(self, sample_carrier_data):
        """Test base forward charge for minimum weight"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        assert result["carrier"] == "Test Carrier"
        assert result["breakdown"]["base_forward"] == 30.0
        assert result["breakdown"]["additional_weight"] == 0.0

    def test_additional_weight_calculation(self, sample_carrier_data):
        """Test additional weight charges are calculated correctly"""
        # 1.5kg = 0.5kg base + 1.0kg additional = 2 units of 0.5kg
        result = calculate_cost(
            weight=1.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # 1.0kg extra / 0.5kg slab = 2 units
        # 2 units * 25.0 (z_a additional rate) = 50.0
        assert result["breakdown"]["additional_weight"] == 50.0

    def test_weight_slab_ceiling(self, sample_carrier_data):
        """Test that partial weight slabs are rounded up"""
        # 0.8kg = 0.5kg base + 0.3kg additional
        # 0.3kg should be rounded up to 1 unit (0.5kg)
        result = calculate_cost(
            weight=0.8,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # 0.3kg extra rounds up to 1 unit * 25.0 = 25.0
        assert result["breakdown"]["additional_weight"] == 25.0

    def test_cod_fixed_fee(self, sample_carrier_data):
        """Test COD fixed fee is applied when higher than percentage"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=True,
            order_value=100  # Low value, fixed fee should be higher
        )

        # Fixed: 30.0, Percentage: 100 * 0.015 = 1.5
        # Should use fixed (30.0)
        assert result["breakdown"]["cod"] == 30.0

    def test_cod_percentage_fee(self, sample_carrier_data):
        """Test COD percentage fee is applied when higher than fixed"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=True,
            order_value=5000  # High value, percentage should be higher
        )

        # Fixed: 30.0, Percentage: 5000 * 0.015 = 75.0
        # Should use percentage (75.0)
        assert result["breakdown"]["cod"] == 75.0

    def test_no_cod_fee(self, sample_carrier_data):
        """Test no COD fee when is_cod is False"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=5000
        )

        assert result["breakdown"]["cod"] == 0.0

    def test_escalation_calculation(self, sample_carrier_data):
        """Test 15% escalation is applied before GST"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # Base: 30.0, Additional: 0, COD: 0
        # Subtotal: 30.0
        # Escalation: 30.0 * 0.15 = 4.5
        expected_escalation = round(30.0 * 0.15, 2)
        assert result["breakdown"]["escalation"] == expected_escalation
        assert result["breakdown"]["applied_escalation_rate"] == "15%"

    def test_gst_calculation(self, sample_carrier_data):
        """Test GST is calculated correctly at 18% on escalated amount"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # Base: 30.0, Additional: 0, COD: 0
        # Subtotal: 30.0
        # Escalation: 30.0 * 0.15 = 4.5
        # After Escalation: 34.5
        # GST: 34.5 * 0.18 = 6.21
        expected_gst = round(34.5 * 0.18, 2)
        assert result["breakdown"]["gst"] == expected_gst
        assert result["breakdown"]["applied_gst_rate"] == "18%"

    def test_total_cost_calculation(self, sample_carrier_data):
        """Test total cost includes all components plus escalation and GST"""
        result = calculate_cost(
            weight=1.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=True,
            order_value=100
        )

        # Base: 30.0
        # Additional: 50.0 (2 units * 25.0)
        # COD: 30.0 (fixed is higher)
        # Subtotal: 110.0
        # Escalation: 110.0 * 0.15 = 16.5
        # After Escalation: 126.5
        # GST: 126.5 * 0.18 = 22.77
        # Total: 149.27
        expected_total = round(126.5 * 1.18, 2)
        assert result["total_cost"] == expected_total

    def test_different_zones(self, sample_carrier_data):
        """Test that different zones use different rates"""
        result_a = calculate_cost(
            weight=0.5, zone_key="z_a", carrier_data=sample_carrier_data,
            is_cod=False, order_value=0
        )

        result_d = calculate_cost(
            weight=0.5, zone_key="z_d", carrier_data=sample_carrier_data,
            is_cod=False, order_value=0
        )

        # Zone D should be more expensive than Zone A
        assert result_d["total_cost"] > result_a["total_cost"]
        assert result_d["breakdown"]["base_forward"] == 45.0
        assert result_a["breakdown"]["base_forward"] == 30.0

    def test_zone_e_premium_pricing(self, sample_carrier_data):
        """Test Zone E (special states) has highest rates"""
        result_e = calculate_cost(
            weight=0.5, zone_key="z_f", carrier_data=sample_carrier_data,
            is_cod=False, order_value=0
        )

        result_a = calculate_cost(
            weight=0.5, zone_key="z_a", carrier_data=sample_carrier_data,
            is_cod=False, order_value=0
        )

        # Zone E should be most expensive
        assert result_e["total_cost"] > result_a["total_cost"]
        assert result_e["breakdown"]["base_forward"] == 60.0

    def test_rounding_precision(self, sample_carrier_data):
        """Test that all monetary values are rounded to 2 decimal places"""
        result = calculate_cost(
            weight=1.3,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=True,
            order_value=333.33
        )

        # Check all breakdown values are rounded to 2 decimals
        assert len(str(result["breakdown"]["base_forward"]).split('.')[-1]) <= 2
        assert len(str(result["breakdown"]["additional_weight"]).split('.')[-1]) <= 2
        assert len(str(result["breakdown"]["gst"]).split('.')[-1]) <= 2
        assert len(str(result["total_cost"]).split('.')[-1]) <= 2

    def test_settings_integration(self):
        """Test that function uses settings from settings.json"""
        assert SETTINGS["GST_RATE"] == 0.18
        assert SETTINGS["ESCALATION_RATE"] == 0.15
        assert SETTINGS["DEFAULT_WEIGHT_SLAB"] == 0.5
        assert SETTINGS["VOLUMETRIC_DIVISOR"] == 5000


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    def test_zero_order_value_with_cod(self, sample_carrier_data):
        """Test COD with zero order value uses fixed fee"""
        result = calculate_cost(
            weight=0.5,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=True,
            order_value=0
        )

        # Should use fixed fee when percentage is 0
        assert result["breakdown"]["cod"] == 30.0

    def test_very_heavy_package(self, sample_carrier_data):
        """Test calculation for very heavy packages"""
        result = calculate_cost(
            weight=50.0,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # 50kg - 0.5kg base = 49.5kg additional
        # 49.5 / 0.5 = 99 units
        # 99 units * 25.0 = 2475.0
        assert result["breakdown"]["additional_weight"] == 2475.0

    def test_exact_slab_weight(self, sample_carrier_data):
        """Test weight that exactly matches slab multiples"""
        # 1.0kg = 0.5kg base + 0.5kg additional = exactly 1 additional unit
        result = calculate_cost(
            weight=1.0,
            zone_key="z_a",
            carrier_data=sample_carrier_data,
            is_cod=False,
            order_value=0
        )

        # Exactly 1 unit * 25.0 = 25.0
        assert result["breakdown"]["additional_weight"] == 25.0
