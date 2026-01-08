"""
Test ACPL bidirectional routing logic.

This test verifies that ACPL routes work in both directions:
- Bhiwandi (hub) -> Gandhidham (serviceable city)
- Gandhidham (serviceable city) -> Bhiwandi (hub)

Both should return 'gandhidham' as the zone_id for rate card lookup.
"""
import os
import sys
from django.test import TestCase

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from courier import zones


class ACPLBidirectionalRoutingTest(TestCase):
    """Test ACPL city-to-city bidirectional routing."""
    
    def setUp(self):
        """Set up test carrier configuration."""
        self.acpl_config = {
            "carrier_name": "ACPL Surface 50kg",
            "routing_logic": {
                "type": "city_specific",
                "is_city_specific": True,
                "hub_city": "bhiwandi",
                "pincode_csv": "ACPL_Serviceable_Pincodes.csv"
            }
        }
        
        # Test pincodes
        self.bhiwandi_pincode = 421308
        self.gandhidham_pincode = 370201
        self.kakinada_pincode = 533433  # Not in ACPL CSV
    
    def test_bhiwandi_to_gandhidham(self):
        """Test Bhiwandi -> Gandhidham returns 'gandhidham' as zone_id."""
        zone_id, desc, logic_type = zones.get_zone(
            self.bhiwandi_pincode,
            self.gandhidham_pincode,
            self.acpl_config
        )
        
        self.assertEqual(zone_id, "gandhidham", 
                        "Should return serviceable city as zone_id")
        self.assertEqual(logic_type, "city_specific")
        self.assertIn("<->", desc, "Description should indicate bidirectional route")
    
    def test_gandhidham_to_bhiwandi(self):
        """Test Gandhidham -> Bhiwandi returns 'gandhidham' as zone_id (THE BUG FIX)."""
        zone_id, desc, logic_type = zones.get_zone(
            self.gandhidham_pincode,
            self.bhiwandi_pincode,
            self.acpl_config
        )
        
        self.assertEqual(zone_id, "gandhidham", 
                        "Should return serviceable city (not hub) as zone_id")
        self.assertEqual(logic_type, "city_specific")
        self.assertIn("<->", desc, "Description should indicate bidirectional route")
    
    def test_non_serviceable_pincode(self):
        """Test that non-serviceable pincodes are rejected."""
        zone_id, desc, logic_type = zones.get_zone(
            self.bhiwandi_pincode,
            self.kakinada_pincode,
            self.acpl_config
        )
        
        self.assertIsNone(zone_id, "Non-serviceable pincode should return None")
        self.assertIn("not identified", desc.lower(), 
                     "Error message should indicate city not found")
    
    def test_symmetry(self):
        """Test that both directions return the same zone_id."""
        zone_id_forward, _, _ = zones.get_zone(
            self.bhiwandi_pincode,
            self.gandhidham_pincode,
            self.acpl_config
        )
        
        zone_id_reverse, _, _ = zones.get_zone(
            self.gandhidham_pincode,
            self.bhiwandi_pincode,
            self.acpl_config
        )
        
        self.assertEqual(zone_id_forward, zone_id_reverse,
                        "Both directions should return the same zone_id for rate lookup")
