"""
Migrate BlueDart configuration from legacy master_card.json.bak to database.

This script populates:
1. Forward rates for all BlueDart regions
2. Fuel configuration
3. Fixed fees (AWB fee)
4. Variable fees (FOD, DOD, Owner's Risk, ECC)
5. EDL configuration and matrix
"""

import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier, CourierZoneRate
from django.core.cache import cache


# BlueDart configuration from master_card.json.bak (line 1184+)
BLUEDART_CONFIG = {
    "carrier_name": "Blue Dart",
    "required_source_city": "bhiwandi",
    "min_weight": 10.0,
    "forward_rates": {
        "CENTRAL": 7,
        "EAST": 12.5,
        "NORTH": 9.5,
        "NORTH EAST": 18,
        "SOUTH": 9,
        "SOUTH1": 9,
        "SOUTH2": 9,
        "WEST": 7,
        "WEST1": 7,
        "WEST2": 7
    },
    "fuel_config": {
        "is_dynamic": False,
        "flat_percent": 0.556  # 55.6% fuel surcharge
    },
    "fixed_fees": {
        "awb_fee": 300,
        "docket_fee": 0
    },
    "variable_fees": {
        "fod_charge": {
            "slab_weight": 100,
            "lte_charge": 100,
            "gt_charge": 250
        },
        "dod_charge": {
            "percent": 0.005,  # 0.5%
            "min_amount": 200
        },
        "owners_risk": {
            "percent": 0.002,  # 0.2%
            "min_amount": 100
        },
        "ecc_charge": [
            {"max": 50, "charge": 75},
            {"max": 100, "charge": 125},
            {"max": 999999, "charge": 175}
        ]
    },
    "edl_config": {
        "special_regions": {
            "states": ["JAMMU AND KASHMIR"],
            "regions": ["NORTH EAST"],
            "rate_per_kg": 15,
            "min_amount": 3000
        },
        "overflow_rates": {
            "dist_limit": 500,
            "dist_rate_per_km": 14,
            "weight_limit": 1500,
            "weight_rate_per_kg": 5
        }
    },
    "edl_matrix": [
        {
            "dist_min": 20, "dist_max": 50,
            "rates": {"100": 550, "250": 990, "500": 1100, "1000": 1375, "1500": 1650}
        },
        {
            "dist_min": 51, "dist_max": 100,
            "rates": {"100": 825, "250": 1210, "500": 1375, "1000": 1650, "1500": 1925}
        },
        {
            "dist_min": 101, "dist_max": 150,
            "rates": {"100": 1100, "250": 1650, "500": 1925, "1000": 2200, "1500": 2750}
        },
        {
            "dist_min": 151, "dist_max": 200,
            "rates": {"100": 1375, "250": 1925, "500": 2200, "1000": 2475, "1500": 3300}
        },
        {
            "dist_min": 201, "dist_max": 250,
            "rates": {"100": 1650, "250": 2200, "500": 2475, "1000": 2750, "1500": 3850}
        },
        {
            "dist_min": 251, "dist_max": 300,
            "rates": {"100": 1925, "250": 2475, "500": 2750, "1000": 3025, "1500": 4400}
        },
        {
            "dist_min": 301, "dist_max": 350,
            "rates": {"100": 2200, "250": 2750, "500": 3025, "1000": 3300, "1500": 4950}
        },
        {
            "dist_min": 351, "dist_max": 400,
            "rates": {"100": 2475, "250": 3025, "500": 3300, "1000": 3575, "1500": 5500}
        },
        {
            "dist_min": 401, "dist_max": 450,
            "rates": {"100": 2750, "250": 3300, "500": 3575, "1000": 3850, "1500": 6050}
        },
        {
            "dist_min": 451, "dist_max": 500,
            "rates": {"100": 3025, "250": 3575, "500": 3850, "1000": 4125, "1500": 6600}
        }
    ]
}


def migrate_bluedart_rates():
    """Create CourierZoneRate entries for BlueDart."""
    print("=" * 60)
    print("MIGRATING BLUEDART FORWARD RATES")
    print("=" * 60)
    
    try:
        bd = Courier.objects.get(name="Blue Dart")
        
        # Delete existing rates (if any)
        existing_count = bd.zone_rates.count()
        if existing_count > 0:
            print(f"\n⚠ Deleting {existing_count} existing rates...")
            bd.zone_rates.all().delete()
        
        # Create new rates
        forward_rates = BLUEDART_CONFIG["forward_rates"]
        created_count = 0
        
        print(f"\nCreating {len(forward_rates)} forward rates:")
        for zone_code, rate in forward_rates.items():
            CourierZoneRate.objects.create(
                courier=bd,
                zone_code=zone_code,
                rate_type=CourierZoneRate.RateType.FORWARD,
                rate=rate
            )
            print(f"  ✓ {zone_code}: ₹{rate}/kg")
            created_count += 1
        
        print(f"\n✓ Successfully created {created_count} zone rates")
        return True
        
    except Courier.DoesNotExist:
        print("\n✗ ERROR: Blue Dart courier not found!")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_bluedart_config():
    """Update BlueDart configuration fields."""
    print("\n" + "=" * 60)
    print("UPDATING BLUEDART CONFIGURATION")
    print("=" * 60)
    
    try:
        bd = Courier.objects.get(name="Blue Dart")
        
        # Update fields
        bd.min_weight = BLUEDART_CONFIG["min_weight"]
        bd.required_source_city = BLUEDART_CONFIG["required_source_city"]
        
        # Fuel config
        fuel = BLUEDART_CONFIG["fuel_config"]
        bd.fuel_is_dynamic = fuel["is_dynamic"]
        bd.fuel_surcharge_percent = fuel["flat_percent"]
        
        # Fixed fees
        fees = BLUEDART_CONFIG["fixed_fees"]
        bd.docket_fee = fees["docket_fee"]
        # AWB fee is stored in fixed_fees dict in legacy_rate_card_backup
        
        # Store complex configurations in legacy_rate_card_backup
        bd.legacy_rate_card_backup = {
            "variable_fees": BLUEDART_CONFIG["variable_fees"],
            "edl_config": BLUEDART_CONFIG["edl_config"],
            "edl_matrix": BLUEDART_CONFIG["edl_matrix"],
            "required_source_city": BLUEDART_CONFIG["required_source_city"],
            "fixed_fees": BLUEDART_CONFIG["fixed_fees"]
        }
        
        bd.save()
        
        print(f"\n✓ Updated BlueDart configuration:")
        print(f"  min_weight: {bd.min_weight} kg")
        print(f"  required_source_city: {bd.required_source_city}")
        print(f"  fuel_surcharge_percent: {bd.fuel_surcharge_percent * 100}%")
        print(f"  docket_fee: ₹{bd.docket_fee}")
        print(f"  legacy_rate_card_backup: {len(bd.legacy_rate_card_backup)} keys stored")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bluedart_pricing():
    """Test BlueDart pricing with the new rates."""
    print("\n" + "=" * 60)
    print("TESTING BLUEDART PRICING")
    print("=" * 60)
    
    try:
        from courier.engine import calculate_cost
        from courier.zones import get_zone
        
        bd = Courier.objects.get(name="Blue Dart")
        carrier_data = bd.get_rate_dict()
        
        # Test: Mumbai (400001) to Delhi (110001)
        source = 400001
        dest = 110001
        weight = 100.0
        
        print(f"\nTest Parameters:")
        print(f"  Source: {source} (Mumbai)")
        print(f"  Destination: {dest} (Delhi)")
        print(f"  Weight: {weight} kg")
        
        # Get zone
        zone_id, zone_desc, logic_type = get_zone(source, dest, carrier_data)
        print(f"\nZone: {zone_id} - {zone_desc}")
        
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
        
        if result.get('servicable') and result.get('total_cost', 0) > 0:
            breakdown = result.get('breakdown', {})
            print(f"\n  Breakdown:")
            print(f"    Base rate per kg: ₹{breakdown.get('base_rate_per_kg', 0)}")
            print(f"    Base freight: ₹{breakdown.get('base_freight', 0)}")
            print(f"    Fuel surcharge: ₹{breakdown.get('fuel_surcharge', 0)}")
            print(f"\n  ✓ SUCCESS: BlueDart pricing is working!")
            return True
        else:
            error = result.get('error', 'Unknown')
            print(f"\n  ✗ FAILED: {error}")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 12 + "BLUEDART DATA MIGRATION" + " " * 23 + "║")
    print("╚" + "═" * 58 + "╝")
    
    results = {
        "rates": migrate_bluedart_rates(),
        "config": update_bluedart_config(),
    }
    
    # Clear cache
    if all(results.values()):
        try:
            cache.delete('carrier_rate_cards')
            print("\n✓ Cleared rate card cache")
            results["cache"] = True
        except Exception as e:
            print(f"\n✗ Failed to clear cache: {e}")
            results["cache"] = False
        
        # Test pricing
        results["test"] = test_bluedart_pricing()
    else:
        results["cache"] = False
        results["test"] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  Rate Migration: {'✓ SUCCESS' if results['rates'] else '✗ FAILED'}")
    print(f"  Config Update:  {'✓ SUCCESS' if results['config'] else '✗ FAILED'}")
    print(f"  Cache Clear:    {'✓ SUCCESS' if results['cache'] else '✗ FAILED'}")
    print(f"  Pricing Test:   {'✓ PASSED' if results['test'] else '✗ FAILED'}")
    print("=" * 60)
    
    if all(results.values()):
        print("\n✓ BLUEDART MIGRATION COMPLETED SUCCESSFULLY!")
        print("\nBlueDart is now ready to use:")
        print("  - Forward rates loaded for all regions")
        print("  - Fuel surcharge: 55.6%")
        print("  - FOD, DOD, Owner's Risk, ECC configured")
        print("  - EDL logic ready for extended delivery locations")
    else:
        print("\n✗ MIGRATION COMPLETED WITH ERRORS")
    
    print()


if __name__ == "__main__":
    main()
