"""
Migration script to fix ACPL and V-Trans pricing logic configuration.

This script updates the Courier model records to enable their
unique pricing logic instead of falling back to standard zonal pricing.

Fixes:
1. ACPL: Sets hub_city and serviceable_pincode_csv fields
2. V-Trans: Changes rate_logic from Zonal_Standard to Zonal_Custom
3. Clears rate card cache to force reload
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier
from django.core.cache import cache


def fix_acpl():
    """Fix ACPL Surface 50kg configuration."""
    print("=" * 60)
    print("FIXING ACPL CONFIGURATION")
    print("=" * 60)
    
    try:
        acpl = Courier.objects.get(name="ACPL Surface 50kg")
        print(f"\nFound ACPL carrier: {acpl.name}")
        print(f"  Current rate_logic: {acpl.rate_logic}")
        print(f"  Current hub_city: {acpl.hub_city}")
        print(f"  Current serviceable_pincode_csv: {acpl.serviceable_pincode_csv}")
        print(f"  Current required_source_city: {acpl.required_source_city}")
        
        # Update fields
        acpl.hub_city = "bhiwandi"
        acpl.serviceable_pincode_csv = "ACPL_Serviceable_Pincodes.csv"
        acpl.required_source_city = "bhiwandi"
        acpl.save()
        
        print("\n✓ Updated ACPL configuration:")
        print(f"  hub_city: {acpl.hub_city}")
        print(f"  serviceable_pincode_csv: {acpl.serviceable_pincode_csv}")
        print(f"  required_source_city: {acpl.required_source_city}")
        
        return True
        
    except Courier.DoesNotExist:
        print("\n✗ ERROR: ACPL Surface 50kg not found in database!")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: Failed to update ACPL: {e}")
        return False


def fix_vtrans():
    """Fix V-Trans 100kg configuration."""
    print("\n" + "=" * 60)
    print("FIXING V-TRANS CONFIGURATION")
    print("=" * 60)
    
    try:
        vtrans = Courier.objects.get(name="V-Trans 100kg")
        print(f"\nFound V-Trans carrier: {vtrans.name}")
        print(f"  Current rate_logic: {vtrans.rate_logic}")
        print(f"  CustomZones count: {vtrans.custom_zones.count()}")
        print(f"  CustomZoneRates count: {vtrans.custom_zone_rates.count()}")
        
        # Verify zone data exists
        if vtrans.custom_zones.count() == 0 or vtrans.custom_zone_rates.count() == 0:
            print("\n✗ ERROR: V-Trans has no zone mapping data in database!")
            print("  Please populate CustomZone and CustomZoneRate tables first.")
            return False
        
        # Update rate_logic
        vtrans.rate_logic = "Zonal_Custom"
        vtrans.save()
        
        print("\n✓ Updated V-Trans configuration:")
        print(f"  rate_logic: {vtrans.rate_logic}")
        
        # Show sample zone mappings
        print("\n  Sample zone mappings (first 5):")
        for zone in vtrans.custom_zones.all()[:5]:
            print(f"    {zone.location_name} → {zone.zone_code}")
        
        print("\n  Sample zone rates (first 5):")
        for rate in vtrans.custom_zone_rates.all()[:5]:
            print(f"    {rate.from_zone} → {rate.to_zone}: ₹{rate.rate_per_kg}/kg")
        
        return True
        
    except Courier.DoesNotExist:
        print("\n✗ ERROR: V-Trans 100kg not found in database!")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: Failed to update V-Trans: {e}")
        return False


def clear_cache():
    """Clear rate card cache to force reload."""
    print("\n" + "=" * 60)
    print("CLEARING RATE CARD CACHE")
    print("=" * 60)
    
    try:
        cache.delete('carrier_rate_cards')
        print("\n✓ Successfully cleared carrier rate card cache")
        print("  Rates will be reloaded from database on next request")
        return True
    except Exception as e:
        print(f"\n✗ ERROR: Failed to clear cache: {e}")
        return False


def verify_fixes():
    """Verify the configuration changes are correct."""
    print("\n" + "=" * 60)
    print("VERIFYING CONFIGURATION")
    print("=" * 60)
    
    all_ok = True
    
    # Verify ACPL
    try:
        acpl = Courier.objects.get(name="ACPL Surface 50kg")
        rate_dict = acpl.get_rate_dict()
        routing_logic = rate_dict.get("routing_logic", {})
        
        print("\n✓ ACPL Verification:")
        print(f"  rate_logic: {acpl.rate_logic}")
        print(f"  is_city_specific: {routing_logic.get('is_city_specific')}")
        print(f"  hub_city in routing_logic: {'hub_city' in routing_logic}")
        print(f"  pincode_csv in routing_logic: {'pincode_csv' in routing_logic}")
        
        if acpl.hub_city != "bhiwandi":
            print(f"  ✗ WARNING: hub_city is '{acpl.hub_city}', expected 'bhiwandi'")
            all_ok = False
        if acpl.serviceable_pincode_csv != "ACPL_Serviceable_Pincodes.csv":
            print(f"  ✗ WARNING: serviceable_pincode_csv is '{acpl.serviceable_pincode_csv}'")
            all_ok = False
            
    except Exception as e:
        print(f"\n✗ ACPL Verification FAILED: {e}")
        all_ok = False
    
    # Verify V-Trans
    try:
        vtrans = Courier.objects.get(name="V-Trans 100kg")
        rate_dict = vtrans.get_rate_dict()
        
        print("\n✓ V-Trans Verification:")
        print(f"  rate_logic: {vtrans.rate_logic}")
        print(f"  zone_mapping in rate_dict: {'zone_mapping' in rate_dict}")
        print(f"  zone_mapping type: {type(rate_dict.get('zone_mapping'))}")
        
        zone_mapping = rate_dict.get('zone_mapping')
        if zone_mapping and isinstance(zone_mapping, dict):
            print(f"  zone_mapping entries: {len(zone_mapping)}")
        
        if vtrans.rate_logic != "Zonal_Custom":
            print(f"  ✗ WARNING: rate_logic is '{vtrans.rate_logic}', expected 'Zonal_Custom'")
            all_ok = False
            
    except Exception as e:
        print(f"\n✗ V-Trans Verification FAILED: {e}")
        all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✓ ALL VERIFICATIONS PASSED")
    else:
        print("✗ SOME VERIFICATIONS FAILED - CHECK WARNINGS ABOVE")
    print("=" * 60)
    
    return all_ok


def main():
    """Main execution function."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "ACPL & V-TRANS PRICING FIX MIGRATION" + " " * 11 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = {
        "acpl": fix_acpl(),
        "vtrans": fix_vtrans(),
        "cache": clear_cache(),
    }
    
    # Verify if all succeeded
    if all(results.values()):
        verify_fixes()
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  ACPL Fix:      {'✓ SUCCESS' if results['acpl'] else '✗ FAILED'}")
    print(f"  V-Trans Fix:   {'✓ SUCCESS' if results['vtrans'] else '✗ FAILED'}")
    print(f"  Cache Clear:   {'✓ SUCCESS' if results['cache'] else '✗ FAILED'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n✓ MIGRATION COMPLETED SUCCESSFULLY!")
        print("\nNext steps:")
        print("  1. Test ACPL pricing from Bhiwandi to any serviceable city")
        print("  2. Test V-Trans pricing between different states")
        print("  3. Verify Zone C no longer appears for ACPL/V-Trans")
    else:
        print("\n✗ MIGRATION COMPLETED WITH ERRORS")
        print("  Please review the error messages above and fix manually")
    
    print()


if __name__ == "__main__":
    main()
