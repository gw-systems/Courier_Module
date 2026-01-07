
import os
import sys
import json

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from courier import engine, zones

def load_carrier_config():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "master_card.json")
    with open(path, "r", encoding='utf-8') as f:
        data = json.load(f)
    for c in data:
        if c.get("carrier_name") == "Blue Dart":
            return c
    return {}

def test_pricing(config, source, dest, weight, desc):
    print(f"\n--- Testing {desc} ---")
    print(f"Params: Source={source}, Dest={dest}, Weight={weight}kg")
    try:
        res = engine.calculate_cost(
            weight=weight,
            source_pincode=source,
            dest_pincode=dest,
            carrier_data=config,
            is_cod=False,
            order_value=5000
        )
        
        if not res["servicable"]:
            print(f"Result: UNAVAILABLE ({res.get('error')})")
            return

        bk = res["breakdown"]
        print(f"Result: AVAILABLE")
        print(f"Zone: {res['zone']}")
        print(f"Base Freight: {bk['base_freight']}")
        print(f"Fuel Surcharge: {bk['fuel_surcharge']}")
        print(f"ECC Charge: {bk.get('ecc_charge', 'MISSING')}")
        print(f"AWB Fee: {bk.get('docket_fee')} (Includes Docket)")
        print(f"FOD: {bk.get('fod_charge')}")
        print(f"Risk: {bk.get('risk_charge')}")
        print(f"Total Cost (Before Tax): {bk['amount_before_tax']}")
        print(f"Final Total (Inc GST): {res['total_cost']}")
        
    except Exception as e:
        print(f"ERROR: {e}")

def run_tests():
    # Redirect stdout capture
    with open("pricing_verification_results.txt", "w") as f:
        sys.stdout = f
        
        print("Initializing Logic...")
        if not zones.PINCODE_LOOKUP:
            zones.PINCODE_LOOKUP = zones.initialize_pincode_lookup()
            
        config = load_carrier_config()
        bhiwandi = 421308
        
        # Test Cases based on user prompt inputs
        # 1. Zone Check (Rate Verification)
        # North (9.5)
        # Note: 122506 is North.
        test_pricing(config, bhiwandi, 122506, 10, "Rate Check: North (10kg)")

        # 2. ECC Slab Check
        # Slab 1: 1-50kg -> 75
        test_pricing(config, bhiwandi, 122506, 40, "ECC Check: Slab 1 (40kg)")
        
        # Slab 2: 51-100kg -> 125
        test_pricing(config, bhiwandi, 122506, 60, "ECC Check: Slab 2 (60kg)")
        
        # Slab 3: 100+ -> 175
        test_pricing(config, bhiwandi, 122506, 110, "ECC Check: Slab 3 (110kg)")
        
        # 3. Fuel Check
        # Verify if Fuel is present (should be ~55.6% of Freight+EDL)
        
    sys.stdout = sys.__stdout__

if __name__ == "__main__":
    run_tests()
