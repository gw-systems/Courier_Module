
import pytest
from rest_framework.test import APIClient
from unittest.mock import patch

@pytest.mark.django_db
def test_get_ftl_routes_structure():
    """
    Test that get_ftl_routes returns the correct nested structure:
    { "Source": { "Dest": ["Type1", "Type2"] } }
    """
    client = APIClient()
    
    # Mock FTL data
    mock_data = {
        "Bhiwandi": {
            "Delhi": {
                "32 FT SXL": 1000,
                "20 FT": 500
            },
            "Mumbai": {
                "10 FT": 200
            }
        }
    }
    
    with patch('courier.views.ftl.load_ftl_rates', return_value=mock_data):
        res = client.get('/api/ftl/routes')
        assert res.status_code == 200
        data = res.json()
        
        # Check structure
        assert "Bhiwandi" in data
        assert "Delhi" in data["Bhiwandi"]
        assert "Mumbai" in data["Bhiwandi"]
        
        # Check container types
        delhi_types = data["Bhiwandi"]["Delhi"]
        assert isinstance(delhi_types, list)
        assert "32 FT SXL" in delhi_types
        assert "20 FT" in delhi_types
        
        mumbai_types = data["Bhiwandi"]["Mumbai"]
        assert "10 FT" in mumbai_types
