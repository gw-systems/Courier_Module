"""
Test script to verify ACPL and V-Trans pricing logic is working correctly.

This script simulates the pricing calculation that happens when booking
orders in the shipment section.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier
from courier.engine import calculate_cost
from courier.zones import get_zone


def test_acpl_pricing():
    """Test ACPL pricing from Bhiwandi to Mumbai."""
    print("=" * 60)
    print("TESTING ACPL PRICING")
    print("=" * 60)
    
    try:
        acpl = Courier.objects.get(name="ACPL Surface 50kg")
        carrier_data = acpl.get_rate_dict()
        
        # Test route: Bhiwandi (421302) to Mumbai (400001)
        source_pincode = 421302
        dest_pincode = 400001
        weight = 100.0  # 100kg
        
        print(f"\nTest Parameters:")
        print(f"  Carrier: {acpl.name}")
        print(f"  Source: {source_pincode} (Bhiwandi)")
        print(f"  Destination: {dest_pincode} (Mumbai)")
        print(f"  Weight: {weight} kg")
        
        # Get zone first
        zone_id, zone_desc, logic_type = get_zone(source_pincode, dest_pincode, carrier_data)
        
        print(f"\nZone Calculation:")
        print(f"  Logic Type: {logic_type}")
        print(f"  Zone ID: {zone_id}")
        print(f"  Zone Description: {zone_desc}")
        
        # Calculate cost
        result = calculate_cost(
            weight=weight,
            source_pincode=source_pincode,
            dest_pincode=dest_pincode,
            carrier_data=carrier_data,
            is_cod=False,
            order_value=0
        )
        
        print(f"\nPricing Result:")
        print(f"  Serviceable: {result.get('servicable', False)}")
        print(f"  Total Cost: ₹{result.get('total_cost', 0)}")
        print(f"  Zone: {result.get('zone', 'N/A')}")
        
        if result.get('servicable', False):
            breakdown = result.get('breakdown', {})
            print(f"\n  Breakdown:")
            print(f"    Rate per kg: ₹{breakdown.get('rate_per_kg', 0)}")
            print(f"    Charged weight: {breakdown.get('charged_weight', 0)} kg")
            print(f"    Base freight: ₹{breakdown.get('base_freight', 0)}")
            
            # Check if it's NOT using standard zonal logic
            if logic_type == "city_specific" and zone_id and zone_id != "z_c":
                print(f"\n  ✓ SUCCESS: Using city-specific pricing logic")
                print(f"    Zone shows city name: {zone_id}")
                return True
            else:
                print(f"\n  ✗ FAILED: Still using standard zonal logic")
                print (f"    Expected city-specific, got: {logic_type}")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n  ✗ FAILED: Route not serviceable - {error}")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vtrans_pricing():
    """Test V-Trans pricing between different states."""
    print("\n" + "=" * 60)
    print("TESTING V-TRANS PRICING")
    print("=" * 60)
    
    try:
        vtrans = Courier.objects.get(name="V-Trans 100kg")
        carrier_data = vtrans.get_rate_dict()
        
        # Test route: Maharashtra (421302 Bhiwandi) to Gujarat (380001 Ahmedabad)
        source_pincode = 421302
        dest_pincode = 380001
        weight = 150.0  # 150kg
        
        print(f"\nTest Parameters:")
        print(f"  Carrier: {vtrans.name}")
        print(f"  Source: {source_pincode} (Bhiwandi, Maharashtra)")
        print(f"  Destination: {dest_pincode} (Ahmedabad, Gujarat)")
        print(f"  Weight: {weight} kg")
        
        # Get zone first
        zone_id, zone_desc, logic_type = get_zone(source_pincode, dest_pincode, carrier_data)
        
        print(f"\nZone Calculation:")
        print(f"  Logic Type: {logic_type}")
        print(f"  Zone ID: {zone_id}")
        print(f"  Zone Description: {zone_desc}")
        
        # Calculate cost
        result = calculate_cost(
            weight=weight,
            source_pincode=source_pincode,
            dest_pincode=dest_pincode,
            carrier_data=carrier_data,
            is_cod=False,
            order_value=0
        )
        
        print(f"\nPricing Result:")
        print(f"  Serviceable: {result.get('servicable', False)}")
        print(f"  Total Cost: ₹{result.get('total_cost', 0)}")
        print(f"  Zone: {result.get('zone', 'N/A')}")
        
        if result.get('servicable', False):
            breakdown = result.get('breakdown', {})
            print(f"\n  Breakdown:")
            print(f"    Rate per kg: ₹{breakdown.get('rate_per_kg', 0)}")
            print(f"    Charged weight: {breakdown.get('charged_weight', 0)} kg")
            print(f"    Base freight: ₹{breakdown.get('base_freight', 0)}")
            
            # Check if it's using matrix logic (not standard zonal)
            if logic_type == "matrix" and isinstance(zone_id, tuple):
                print(f"\n  ✓ SUCCESS: Using zone matrix pricing logic")
                print(f"    Origin zone: {zone_id[0]}, Dest zone: {zone_id[1]}")
                return True
            else:
                print(f"\n  ✗ FAILED: Still using standard zonal logic")
                print(f"    Expected matrix, got: {logic_type}")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n  ✗ FAILED: Route not serviceable - {error}")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "PRICING LOGIC TEST SUITE" + " " * 19 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = {
        "acpl": test_acpl_pricing(),
        "vtrans": test_vtrans_pricing()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  ACPL Test:     {'✓ PASSED' if results['acpl'] else '✗ FAILED'}")
    print(f"  V-Trans Test:  {'✓ PASSED' if results['vtrans'] else '✗ FAILED'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n✓ ALL TESTS PASSED!")
        print("  ACPL is using city-specific pricing")
        print("  V-Trans is using zone matrix pricing")
        print("  Both carriers should now show correct prices in dashboard")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("  Please review the test output above for details")
    
    print()


if __name__ == "__main__":
    main()
