"""
Fix BlueDart pricing configuration.

BlueDart uses Region_CSV logic which requires:
1. serviceable_pincode_csv field to be set
2. routing_logic['type'] to be set to 'pincode_region_csv'

This script fixes the database configuration and the model code.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier
from django.core.cache import cache


def fix_bluedart_config():
    """Fix BlueDart database configuration."""
    print("=" * 60)
    print("FIXING BLUEDART CONFIGURATION")
    print("=" * 60)
    
    try:
        bd = Courier.objects.get(name="Blue Dart")
        print(f"\nFound BlueDart carrier: {bd.name}")
        print(f"  Current rate_logic: {bd.rate_logic}")
        print(f"  Current serviceable_pincode_csv: {bd.serviceable_pincode_csv}")
        
        # Update serviceable_pincode_csv
        bd.serviceable_pincode_csv = "BlueDart_Servicable Pincodes.csv"
        bd.save()
        
        print(f"\n✓ Updated BlueDart configuration:")
        print(f"  serviceable_pincode_csv: {bd.serviceable_pincode_csv}")
        
        # Verify the rate_dict now includes csv_file
        rate_dict = bd.get_rate_dict()
        routing_logic = rate_dict.get("routing_logic", {})
        
        print(f"\n  Verification:")
        print(f"    csv_file in routing_logic: {routing_logic.get('csv_file')}")
        print(f"    type in routing_logic: {routing_logic.get('type')}")
        
        if not routing_logic.get('type'):
            print(f"\n  ⚠ WARNING: routing_logic['type'] is still None!")
            print(f"    This needs to be fixed in models.py")
            return False
        
        return True
        
    except Courier.DoesNotExist:
        print("\n✗ ERROR: Blue Dart not found in database!")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: Failed to update BlueDart: {e}")
        import traceback
        traceback.print_exc()
        return False


def clear_cache():
    """Clear rate card cache."""
    print("\n" + "=" * 60)
    print("CLEARING RATE CARD CACHE")
    print("=" * 60)
    
    try:
        cache.delete('carrier_rate_cards')
        print("\n✓ Successfully cleared carrier rate card cache")
        return True
    except Exception as e:
        print(f"\n✗ ERROR: Failed to clear cache: {e}")
        return False


def test_bluedart_pricing():
    """Test BlueDart pricing."""
    print("\n" + "=" * 60)
    print("TESTING BLUEDART PRICING")
    print("=" * 60)
    
    try:
        from courier.engine import calculate_cost
        from courier.zones import get_zone
        
        bd = Courier.objects.get(name="Blue Dart")
        carrier_data = bd.get_rate_dict()
        
        # Test route: Mumbai (400001) to Delhi (110001)
        source = 400001
        dest = 110001
        weight = 10.0
        
        print(f"\nTest Parameters:")
        print(f"  Source: {source} (Mumbai)")
        print(f"  Destination: {dest} (Delhi)")  
        print(f"  Weight: {weight} kg")
        
        # Get zone
        zone_id, zone_desc, logic_type = get_zone(source, dest, carrier_data)
        
        print(f"\nZone Calculation:")
        print(f"  Logic Type: {logic_type}")
        print(f"  Zone ID: {zone_id}")
        print(f"  Zone Description: {zone_desc}")
        
        if not zone_id:
            print(f"\n✗ Zone lookup failed: {zone_desc}")
            return False
        
        # Calculate cost
        result = calculate_cost(
            weight=weight,
            source_pincode=source,
            dest_pincode=dest,
            carrier_data=carrier_data,
            is_cod=False,
            order_value=0
        )
        
        print(f"\nPricing Result:")
        print(f"  Serviceable: {result.get('servicable', False)}")
        print(f"  Total Cost: ₹{result.get('total_cost', 0)}")
        print(f"  Zone: {result.get('zone', 'N/A')}")
        
        if result.get('servicable') and result.get('total_cost', 0) > 0:
            print(f"\n  ✓ SUCCESS: BlueDart pricing is working!")
            return True
        else:
            error = result.get('error', 'Unknown')
            print(f"\n  ✗ FAILED: {error}")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 18 + "BLUEDART PRICING FIX" + " " * 20 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = {
        "config": fix_bluedart_config(),
        "cache": clear_cache(),
    }
    
    if all(results.values()):
        results["test"] = test_bluedart_pricing()
    else:
        results["test"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Config Fix:  {'✓ SUCCESS' if results['config'] else '✗ FAILED'}")
    print(f"  Cache Clear: {'✓ SUCCESS' if results['cache'] else '✗ FAILED'}")
    print(f"  Pricing Test: {'✓ PASSED' if results['test'] else '✗ FAILED'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n✓ BLUEDART FIX COMPLETED SUCCESSFULLY!")
    else:
        print("\n✗ BLUEDART FIX COMPLETED WITH ERRORS")
        print("  Check output above for details")
    
    print()


if __name__ == "__main__":
    main()
