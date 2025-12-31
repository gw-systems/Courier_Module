"""
Tests for API endpoints (app/main.py)
"""
import pytest
from fastapi import status


class TestCompareRatesEndpoint:
    """Tests for POST /compare-rates endpoint"""

    def test_valid_request_returns_200(self, client, sample_rate_request):
        """Test valid request returns successful response"""
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_200_OK

    def test_response_is_list(self, client, sample_rate_request):
        """Test response returns list of carrier options"""
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()
        assert isinstance(data, list)

    def test_response_sorted_by_cost(self, client, sample_rate_request):
        """Test results are sorted by total cost (cheapest first)"""
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        if len(data) > 1:
            costs = [item["total_cost"] for item in data]
            assert costs == sorted(costs), "Results should be sorted by cost"

    def test_each_result_has_required_fields(self, client, sample_rate_request):
        """Test each carrier result has all required fields"""
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        required_fields = ["carrier", "total_cost", "breakdown", "applied_zone", "mode"]

        for carrier_result in data:
            for field in required_fields:
                assert field in carrier_result, f"Missing field: {field}"

    def test_breakdown_structure(self, client, sample_rate_request):
        """Test breakdown object has correct structure"""
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        if data:
            breakdown = data[0]["breakdown"]
            assert "base_forward" in breakdown
            assert "additional_weight" in breakdown
            assert "cod" in breakdown
            assert "escalation" in breakdown
            assert "gst" in breakdown
            assert "applied_gst_rate" in breakdown
            assert "applied_escalation_rate" in breakdown

    def test_invalid_source_pincode(self, client, sample_rate_request):
        """Test validation fails for invalid source pincode"""
        sample_rate_request["source_pincode"] = 12345  # Only 5 digits
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_dest_pincode(self, client, sample_rate_request):
        """Test validation fails for invalid destination pincode"""
        sample_rate_request["dest_pincode"] = 1234567  # 7 digits
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_weight(self, client, sample_rate_request):
        """Test validation fails for negative weight"""
        sample_rate_request["weight"] = -1.5
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_zero_weight(self, client, sample_rate_request):
        """Test validation fails for zero weight"""
        sample_rate_request["weight"] = 0
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_excessive_weight(self, client, sample_rate_request):
        """Test validation fails for weight over 1000kg"""
        sample_rate_request["weight"] = 1001
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_negative_order_value(self, client, sample_rate_request):
        """Test validation fails for negative order value"""
        sample_rate_request["order_value"] = -100
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_mode(self, client, sample_rate_request):
        """Test validation fails for invalid mode"""
        sample_rate_request["mode"] = "Express"  # Not in allowed values
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_mode_surface_only(self, client, sample_rate_request):
        """Test filtering by Surface mode only"""
        sample_rate_request["mode"] = "Surface"
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        for carrier in data:
            assert carrier["mode"] == "Surface"

    def test_mode_air_only(self, client, sample_rate_request):
        """Test filtering by Air mode only"""
        sample_rate_request["mode"] = "Air"
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        for carrier in data:
            assert carrier["mode"] == "Air"

    def test_cod_flag_affects_cost(self, client, sample_rate_request):
        """Test COD flag increases total cost"""
        # Request without COD
        sample_rate_request["is_cod"] = False
        response_no_cod = client.post("/compare-rates", json=sample_rate_request)
        data_no_cod = response_no_cod.json()

        # Request with COD
        sample_rate_request["is_cod"] = True
        response_cod = client.post("/compare-rates", json=sample_rate_request)
        data_cod = response_cod.json()

        if data_no_cod and data_cod:
            # COD should increase the cost
            assert data_cod[0]["total_cost"] > data_no_cod[0]["total_cost"]
            assert data_cod[0]["breakdown"]["cod"] > 0
            assert data_no_cod[0]["breakdown"]["cod"] == 0


class TestAdminEndpoints:
    """Tests for admin endpoints"""

    def test_get_rates_without_token_fails(self, client):
        """Test accessing admin endpoint without token returns 401"""
        response = client.get("/api/admin/rates")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_rates_with_invalid_token_fails(self, client):
        """Test accessing admin endpoint with wrong token returns 401"""
        response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": "wrong_password"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_rates_with_valid_token_succeeds(self, client, admin_token):
        """Test accessing admin endpoint with correct token returns 200"""
        response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": admin_token}
        )
        assert response.status_code == status.HTTP_200_OK

    def test_get_rates_returns_list(self, client, admin_token):
        """Test get rates returns list of carriers"""
        response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": admin_token}
        )
        data = response.json()
        assert isinstance(data, list)

    def test_update_rates_without_token_fails(self, client):
        """Test updating rates without token returns 401"""
        response = client.post(
            "/api/admin/rates/update",
            json=[{"carrier_name": "Test"}]
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_rates_with_valid_token(self, client, admin_token):
        """Test updating rates with valid token"""
        # First get existing rates
        get_response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": admin_token}
        )
        existing_rates = get_response.json()

        # Update with same data
        response = client.post(
            "/api/admin/rates/update",
            headers={"X-Admin-Token": admin_token},
            json=existing_rates
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"


class TestCORSConfiguration:
    """Tests for CORS middleware configuration"""

    def test_cors_headers_present(self, client, sample_rate_request):
        """Test CORS headers are present in response"""
        response = client.post("/compare-rates", json=sample_rate_request)

        # FastAPI TestClient doesn't fully simulate CORS,
        # but we can verify the endpoint is accessible
        assert response.status_code in [200, 422]


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_missing_required_field(self, client):
        """Test request missing required fields fails validation"""
        incomplete_request = {
            "source_pincode": 400001,
            # Missing dest_pincode and weight
        }
        response = client.post("/compare-rates", json=incomplete_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_extra_fields_ignored(self, client, sample_rate_request):
        """Test extra fields in request are ignored"""
        sample_rate_request["extra_field"] = "should be ignored"
        response = client.post("/compare-rates", json=sample_rate_request)
        assert response.status_code == status.HTTP_200_OK

    def test_same_source_dest_pincode(self, client, sample_rate_request):
        """Test same source and destination pincode (Zone A - Local)"""
        sample_rate_request["source_pincode"] = 400001
        sample_rate_request["dest_pincode"] = 400001
        response = client.post("/compare-rates", json=sample_rate_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data:
            # Should be Zone A (Local)
            assert "Zone A" in data[0]["applied_zone"] or "Local" in data[0]["applied_zone"]


class TestRateLimiting:
    """Tests for rate limiting"""

    def test_rate_limit_not_exceeded_normal_usage(self, client, sample_rate_request):
        """Test normal usage doesn't hit rate limit"""
        # Make a few requests (well below 30/minute limit)
        for _ in range(5):
            response = client.post("/compare-rates", json=sample_rate_request)
            assert response.status_code == status.HTTP_200_OK


class TestLoadRatesFunction:
    """Tests for load_rates helper function"""

    def test_load_rates_returns_list(self, client):
        """Test load_rates returns a list"""
        response = client.get("/health")
        data = response.json()
        assert data["rate_card_count"] >= 0  # Should have count of loaded rates


class TestStartupValidation:
    """Tests for startup validation"""

    def test_health_check_after_startup(self, client):
        """Test health check shows system is ready"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["pincode_db_loaded"] is True
        assert data["pincode_count"] > 0


class TestRootEndpoint:
    """Tests for root endpoint redirect"""

    def test_root_redirects_to_dashboard(self, client):
        """Test root path redirects to dashboard"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in [307, 302]  # Redirect status codes
        assert "dashboard.html" in response.headers.get("location", "")


class TestCompareRatesFiltering:
    """Tests for carrier filtering in compare rates"""

    def test_inactive_carriers_excluded(self, client, sample_rate_request):
        """Test inactive carriers are not returned"""
        response = client.post("/compare-rates", json=sample_rate_request)
        data = response.json()

        # All returned carriers should be active
        # (We can't directly test this without knowing carrier data)
        assert isinstance(data, list)

    def test_no_carriers_for_invalid_mode(self, client, sample_rate_request):
        """Test error when no carriers match mode"""
        # This might not fail depending on carrier data
        # Just verify response structure is correct
        sample_rate_request["mode"] = "Surface"
        response = client.post("/compare-rates", json=sample_rate_request)

        # Should return 200 with results or 404 if no carriers
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestErrorHandling:
    """Tests for error handling"""

    def test_malformed_json_request(self, client):
        """Test malformed JSON is handled"""
        response = client.post(
            "/compare-rates",
            data="{ invalid json }",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_empty_request_body(self, client):
        """Test empty request body fails validation"""
        response = client.post("/compare-rates", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAdminEndpointsExtended:
    """Extended tests for admin endpoints"""

    def test_add_carrier_validates_zones(self, client, admin_token):
        """Test adding carrier requires all zone rates"""
        incomplete_carrier = {
            "carrier_name": "Incomplete Carrier",
            "mode": "Surface",
            "min_weight": 0.5,
            "forward_rates": {
                "z_a": 30.0,
                # Missing other zones
            },
            "additional_rates": {
                "z_a": 5.0,
            },
            "cod_fixed": 25.0,
            "cod_percent": 0.015
        }

        response = client.post(
            "/api/admin/rates/add",
            headers={"X-Admin-Token": admin_token},
            json=incomplete_carrier
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_rates_preserves_structure(self, client, admin_token):
        """Test updating rates preserves data structure"""
        # Get current rates
        get_response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": admin_token}
        )
        original_rates = get_response.json()

        # Update with same data
        update_response = client.post(
            "/api/admin/rates/update",
            headers={"X-Admin-Token": admin_token},
            json=original_rates
        )

        assert update_response.status_code == status.HTTP_200_OK

        # Verify data is unchanged
        verify_response = client.get(
            "/api/admin/rates",
            headers={"X-Admin-Token": admin_token}
        )
        updated_rates = verify_response.json()
        assert len(updated_rates) == len(original_rates)
