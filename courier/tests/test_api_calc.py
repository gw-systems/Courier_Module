
import pytest
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

@pytest.mark.django_db
def test_compare_rates_bluedart_integration():
    """
    Test compare-rates API to ensure it passes pincodes correctly to engine.
    We mock `load_rates` to return a fake Blue Dart carrier that requires 'bhiwandi'.
    """
    client = APIClient()
    
    # Mock Carrier Data
    mock_bluedart = {
        "carrier_name": "Blue Dart",
        "active": True,
        "mode": "Air",
        "required_source_city": "bhiwandi",
        "routing_logic": {},
        # Minimal data to pass verification
        "min_weight": 0.5,
        "forward_rates": {"A": 50},
    }
    
    # We need to mock 'courier.views.public.load_rates' 
    # AND 'courier.engine.zones.get_location_details' to return Bhiwandi or nothing
    
    with patch('courier.views.public.load_rates', return_value=[mock_bluedart]):
        with patch('courier.engine.zones.get_location_details') as mock_loc:
            # Scenario 1: Source is Bhiwandi (421302) -> Should Service
            mock_loc.side_effect = lambda pin: {"city": "Bhiwandi"} if pin == 421302 else {"city": "Delhi"}
            
            # Using standard engine logic, if we pass 421302, it should assume Bhiwandi
            # The engine relies on get_location_details OR hardcoded '4213' check.
            
            payload_success = {
                "source_pincode": 421302,
                "dest_pincode": 110001, 
                "weight": 5,
                "is_cod": False,
                "order_value": 2000,
                "mode": "Both"
            }
            
            # We also need to mock engine.calculate_cost call? 
            # NO, we want to test THAT compare_rates calls calculate_cost with pincodes.
            # If compare_rates used the OLD logic (zone_key), calculate_cost would receive zone_key.
            # If it uses NEW logic, it receives source_pincode.
            
            # Actually, the best way to verify the FIX is to mock calculate_cost and check arguments.
            with patch('courier.views.public.calculate_cost') as mock_calc:
                mock_calc.return_value = {
                    "carrier": "Blue Dart",
                    "total_cost": 100,
                    "servicable": True,
                    "zone": "A"
                }
                
                res = client.post('/api/compare-rates', data=payload_success, format='json')
                assert res.status_code == 200
                
                # VERIFY: Did calculate_cost get called with source_pincode?
                args, kwargs = mock_calc.call_args
                assert kwargs.get('source_pincode') == 421302
                assert kwargs.get('dest_pincode') == 110001
                # If it was using old logic, these keys might be missing or different
