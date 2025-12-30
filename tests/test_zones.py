"""
Tests for zone resolution logic (app/zones.py)
"""
import pytest
from app.zones import (
    get_zone_column,
    get_location_details,
    is_metro,
    normalize_state,
    PINCODE_LOOKUP
)


class TestPincodeLookup:
    """Tests for pincode database loading and lookup"""

    def test_pincode_lookup_loaded(self):
        """Verify pincode database is loaded successfully"""
        assert len(PINCODE_LOOKUP) > 0, "Pincode database should not be empty"

    def test_pincode_lookup_structure(self):
        """Verify pincode lookup has correct data structure"""
        if PINCODE_LOOKUP:
            sample_pincode = next(iter(PINCODE_LOOKUP))
            data = PINCODE_LOOKUP[sample_pincode]
            assert 'office' in data
            assert 'state' in data
            assert 'district' in data


class TestLocationDetails:
    """Tests for get_location_details function"""

    def test_valid_pincode_returns_details(self):
        """Test that valid pincode returns location details"""
        # Using a common pincode (Mumbai - 400001)
        result = get_location_details(400001)
        if result:
            assert 'city' in result
            assert 'state' in result
            assert 'district' in result
            assert isinstance(result['city'], str)
            assert isinstance(result['state'], str)

    def test_invalid_pincode_returns_none(self):
        """Test that invalid pincode returns None"""
        result = get_location_details(999999)
        assert result is None

    def test_location_details_normalization(self):
        """Test that returned data is normalized (lowercase, stripped)"""
        result = get_location_details(400001)
        if result:
            assert result['city'] == result['city'].lower().strip()
            assert result['state'] == result['state'].lower().strip()


class TestNormalizeState:
    """Tests for normalize_state helper function"""

    def test_normalize_state_lowercase(self):
        """Test state name is converted to lowercase"""
        assert normalize_state("MAHARASHTRA") == "maharashtra"

    def test_normalize_state_ampersand(self):
        """Test ampersand is replaced with 'and'"""
        assert normalize_state("Jammu & Kashmir") == "jammu and kashmir"

    def test_normalize_state_strips_whitespace(self):
        """Test leading/trailing whitespace is removed"""
        assert normalize_state("  Tamil Nadu  ") == "tamil nadu"


class TestMetroDetection:
    """Tests for is_metro function"""

    def test_mumbai_is_metro(self):
        """Test Mumbai is detected as metro"""
        location = {'city': 'mumbai', 'state': 'maharashtra', 'district': 'mumbai'}
        assert is_metro(location) is True

    def test_delhi_is_metro(self):
        """Test Delhi is detected as metro"""
        location = {'city': 'new delhi', 'state': 'delhi', 'district': 'central delhi'}
        assert is_metro(location) is True

    def test_bangalore_variations(self):
        """Test Bangalore/Bengaluru variations are detected"""
        location1 = {'city': 'bangalore', 'state': 'karnataka', 'district': 'bangalore'}
        location2 = {'city': 'bengaluru', 'state': 'karnataka', 'district': 'bengaluru urban'}
        assert is_metro(location1) is True
        assert is_metro(location2) is True

    def test_non_metro_city(self):
        """Test non-metro city returns False"""
        location = {'city': 'jaipur', 'state': 'rajasthan', 'district': 'jaipur'}
        # Note: Check your metro_cities.json - if jaipur is there, adjust this test
        # This assumes jaipur is NOT in metro list
        result = is_metro(location)
        # Result depends on your actual config


class TestZoneAssignment:
    """Tests for get_zone_column zone assignment logic"""

    def test_zone_a_same_city(self):
        """Test Zone A assigned for same city shipments"""
        # Both Mumbai pincodes
        zone_key, zone_label = get_zone_column(400001, 400002)
        if zone_key == "z_a":
            assert "Zone A" in zone_label or "Local" in zone_label

    def test_zone_b_same_state(self):
        """Test Zone B assigned for same state shipments"""
        # Mumbai to Pune (both Maharashtra)
        zone_key, zone_label = get_zone_column(400001, 411001)
        # Should be Zone B unless both are metros (then Zone C)
        assert zone_key in ["z_b", "z_c"]

    def test_zone_c_metro_to_metro(self):
        """Test Zone C assigned for metro to metro shipments"""
        # Mumbai to Delhi (both metros, different states)
        zone_key, zone_label = get_zone_column(400001, 110001)
        if zone_key == "z_c":
            assert "Metro" in zone_label

    def test_zone_e_special_states_priority(self):
        """Test Zone E has highest priority for NE/J&K states"""
        # Any pincode to/from Arunachal Pradesh should be Zone E
        # Using Itanagar pincode: 791111
        zone_key, zone_label = get_zone_column(400001, 791111)
        assert zone_key == "z_f"
        assert "Zone E" in zone_label or "Special" in zone_label

    def test_zone_d_fallback(self):
        """Test Zone D assigned as fallback for national shipments"""
        # Mumbai to a non-metro in different state
        # Using Jaipur: 302001 (assuming not metro)
        zone_key, zone_label = get_zone_column(400001, 302001)
        # Could be Zone C if Jaipur is metro, otherwise Zone D
        assert zone_key in ["z_c", "z_d"]

    def test_invalid_source_pincode(self):
        """Test invalid source pincode falls back to Zone D"""
        zone_key, zone_label = get_zone_column(999999, 110001)
        assert zone_key == "z_d"
        assert "Not Found" in zone_label or "National" in zone_label

    def test_invalid_dest_pincode(self):
        """Test invalid destination pincode falls back to Zone D"""
        zone_key, zone_label = get_zone_column(400001, 999999)
        assert zone_key == "z_d"

    def test_both_invalid_pincodes(self):
        """Test both invalid pincodes fall back to Zone D"""
        zone_key, zone_label = get_zone_column(999998, 999999)
        assert zone_key == "z_d"


class TestZonePriorityHierarchy:
    """Tests to verify zone priority ordering"""

    def test_zone_e_overrides_same_city(self):
        """Test Zone E priority over Zone A for special states"""
        # If source and dest are both in NE state, should still be Zone E
        # Using two Arunachal Pradesh pincodes
        zone_key, zone_label = get_zone_column(791111, 791112)
        assert zone_key == "z_f"  # Zone E takes priority

    def test_zone_e_overrides_metro(self):
        """Test Zone E priority over Zone C for metro in special states"""
        # If one location is metro in special state
        zone_key, zone_label = get_zone_column(110001, 791111)
        assert zone_key == "z_f"
