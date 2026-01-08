"""
Verification script to confirm migration 0021 applied correctly.
Run this to verify carrier configurations after migration.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier


def verify_configurations():
    print("=" * 70)
    print("VERIFYING MIGRATION 0021: FIX CARRIER CONFIGURATIONS")
    print("=" * 70)
    
    all_passed = True
    
    # Test 1: BlueDart
    print("\n1. BlueDart Configuration")
    print("-" * 70)
    try:
        bd = Courier.objects.get(name="Blue Dart")
        csv_file = bd.serviceable_pincode_csv
        expected_csv = "BlueDart_Servicable Pincodes.csv"
        
        if csv_file == expected_csv:
            print(f"✓ PASS: serviceable_pincode_csv = '{csv_file}'")
        else:
            print(f"✗ FAIL: Expected '{expected_csv}', got '{csv_file}'")
            all_passed = False
    except Courier.DoesNotExist:
        print("⚠ WARNING: BlueDart carrier not found in database")
        all_passed = False
    
    # Test 2: ACPL
    print("\n2. ACPL Surface 50kg Configuration")
    print("-" * 70)
    try:
        acpl = Courier.objects.filter(name__icontains='ACPL').first()
        if not acpl:
            print("✗ FAIL: ACPL carrier not found")
            all_passed = False
        else:
            checks = {
                "hub_city": ("bhiwandi", acpl.hub_city),
                "required_source_city": ("bhiwandi", acpl.required_source_city),
                "serviceable_pincode_csv": ("ACPL_Serviceable_Pincodes.csv", acpl.serviceable_pincode_csv),
                "min_weight": (50.0, acpl.min_weight),
            }
            
            for field, (expected, actual) in checks.items():
                if actual == expected:
                    print(f"✓ PASS: {field} = {actual}")
                else:
                    print(f"✗ FAIL: {field} - Expected {expected}, got {actual}")
                    all_passed = False
            
            # Check rate_card structure
            rc = acpl.rate_card or {}
            if 'fixed_fees' in rc and 'docket_fee' in rc['fixed_fees']:
                print(f"✓ PASS: docket_fee = {rc['fixed_fees']['docket_fee']}")
            else:
                print("✗ FAIL: docket_fee not configured")
                all_passed = False
                
            if 'variable_fees' in rc and 'owners_risk' in rc['variable_fees']:
                print(f"✓ PASS: owners_risk configured")
            else:
                print("✗ FAIL: owners_risk not configured")
                all_passed = False
                
    except Exception as e:
        print(f"✗ ERROR: {e}")
        all_passed = False
    
    # Test 3: V-Trans
    print("\n3. V-Trans 100kg Configuration")
    print("-" * 70)
    try:
        vtrans = Courier.objects.get(name="V-Trans 100kg")
        zone_count = vtrans.custom_zones.count()
        
        print(f"  Custom zones in DB: {zone_count}")
        
        if zone_count > 0:
            if vtrans.rate_logic == "Zonal_Custom":
                print(f"✓ PASS: rate_logic = {vtrans.rate_logic}")
            else:
                print(f"✗ FAIL: Expected 'Zonal_Custom', got '{vtrans.rate_logic}'")
                all_passed = False
        else:
            if vtrans.rate_logic == "Zonal_Standard":
                print(f"✓ PASS: rate_logic = {vtrans.rate_logic} (no zones, kept standard)")
            else:
                print(f"⚠ WARNING: No custom zones but rate_logic is '{vtrans.rate_logic}'")
        
        rc = vtrans.rate_card or {}
        if 'variable_fees' in rc and 'hamali_per_kg' in rc['variable_fees']:
            hamali = rc['variable_fees']['hamali_per_kg']
            if hamali == 0.2:
                print(f"✓ PASS: hamali_per_kg = {hamali}")
            else:
                print(f"✗ FAIL: Expected hamali_per_kg=0.2, got {hamali}")
                all_passed = False
        else:
            print("✗ FAIL: hamali_per_kg not configured")
            all_passed = False
            
    except Courier.DoesNotExist:
        print("⚠ WARNING: V-Trans 100kg carrier not found in database")
        all_passed = False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL VERIFICATIONS PASSED")
        print("Migration 0021 was successfully applied!")
    else:
        print("✗ SOME VERIFICATIONS FAILED")
        print("Review the output above for details.")
    print("=" * 70)
    print()
    
    return all_passed


if __name__ == "__main__":
    verify_configurations()
