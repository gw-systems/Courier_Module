
import pytest
from rest_framework.test import APIClient
from unittest.mock import patch

@pytest.mark.django_db
def test_ftl_calculator_keys():
    """
    Test FTL Rate Calculator API to ensure it returns the expected keys
    that the frontend now relies on (base_price, gst_amount, total_price).
    """
    client = APIClient()
    
    mock_data = {
        "Bhiwandi": {
            "Delhi": {
                "32 FT SXL": 50000
            }
        }
    }
    
    # helper for calculate_ftl_price if we want to mock it, or just use real one
    # Real one adds GST and Escalation. Let's use real one to ensure integration.
    # But we need to mock load_ftl_rates.
    
    with patch('courier.views.ftl.load_ftl_rates', return_value=mock_data):
        payload = {
            "source_city": "Bhiwandi",
            "destination_city": "Delhi",
            "container_type": "32 FT SXL"
        }
        res = client.post('/api/ftl/calculate-rate', data=payload)
        assert res.status_code == 200
        data = res.json()
        
        # Verify Keys
        assert "base_price" in data
        assert "gst_amount" in data
        assert "total_price" in data
        
        # Verify values roughly (non-zero)
        assert data["base_price"] == 50000.0
        assert data["total_price"] > 50000.0

        
        # Verify "fuel_surcharge" is NOT present (unless added by me, which it shouldn't be)
        assert "fuel_surcharge" not in data
