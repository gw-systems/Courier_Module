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

def test_slab(config, source, dest, weight, desc):
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
        print(f"Zone: {res['zone']}")
        print(f"Charged Weight: {bk.get('charged_weight')}")
        print(f"Rate/Kg: {bk.get('base_rate_per_kg')}")
        print(f"Base Freight: {bk.get('base_freight')}")
        print(f"ECC Charge: {bk.get('ecc_charge')}")
        print(f"Final Total (Inc GST): {res['total_cost']}")
        
    except Exception as e:
        print(f"ERROR: {e}")

def run_tests():
    with open("slab_verification_results.txt", "w") as f:
        sys.stdout = f
        
        if not zones.PINCODE_LOOKUP:
            zones.PINCODE_LOOKUP = zones.initialize_pincode_lookup()
            
        config = load_carrier_config()
        bhiwandi = 421308
        north_pin = 122506 # Rate 9.5
        south_pin = 516001 # Rate 9.0
        
        # ZONE 1: NORTH
        print("=== checking NORTH Zone (Rate 9.5) ===")
        # Case 1: Below Min (5kg) -> Should charge 10kg
        test_slab(config, bhiwandi, north_pin, 5, "North Below Min (5kg)")
        
        # Case 2: Above Slab (15kg) -> Should charge 15kg
        test_slab(config, bhiwandi, north_pin, 15, "North Above Slab (15kg)")
        
        # ZONE 2: SOUTH 1
        print("\n=== checking SOUTH Zone (Rate 9.0) ===")
        # Case 3: Below Min (8kg) -> Should charge 10kg
        test_slab(config, bhiwandi, south_pin, 8, "South Below Min (8kg)")
        
        # Case 4: Above Slab (25kg) -> Should charge 25kg
        test_slab(config, bhiwandi, south_pin, 25, "South Above Slab (25kg)")
        
    sys.stdout = sys.__stdout__

if __name__ == "__main__":
    run_tests()
