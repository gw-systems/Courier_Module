
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

def test_combination(config, source, dest, desc):
    print(f"Testing {desc} (Source: {source} -> Dest: {dest})")
    try:
        res = engine.calculate_cost(
            weight=10,
            source_pincode=source,
            dest_pincode=dest,
            carrier_data=config,
            is_cod=False,
            order_value=5000
        )
        status = "AVAILABLE" if res["servicable"] else "UNAVAILABLE"
        reason = "" if res["servicable"] else f"Reason: {res.get('error')}"
        print(f"  -> Result: {status} {reason}")
    except Exception as e:
        print(f"  -> ERROR: {e}")
    print("-" * 40)

def run_tests():
    # Redirect stdout to a file for reliable capture
    with open("verification_results_custom.txt", "w") as f:
        sys.stdout = f

        
        print("Initializing Pincode Lookup...")
        if not zones.PINCODE_LOOKUP:
            zones.PINCODE_LOOKUP = zones.initialize_pincode_lookup()
            
        config = load_carrier_config()
        print(f"Loaded Config for: {config.get('carrier_name')}")
        print(f"Required Source: {config.get('required_source_city')}\n")
    
        bhiwandi = 421308
        loc = zones.get_location_details(bhiwandi)
        print(f"DEBUG: Internal details for {bhiwandi}: {loc}")
    
        zones_map = {
            "North": 122506,
            "West 1": 416610,
            "West 2": 360006,
            "South 1": 516001,
            "South 2": 515865,
            "East": 721638
        }
    
        # 1. Bhiwandi to Zones
        print("\n[TEST SET 1] Bhiwandi to Zones (EXPECTED: AVAILABLE)")
        for name, pincode in zones_map.items():
            test_combination(config, bhiwandi, pincode, f"Bhiwandi -> {name}")
    
        # 2. Zones to Bhiwandi
        print("\n[TEST SET 2] Zones to Bhiwandi (EXPECTED: UNAVAILABLE)")
        for name, pincode in zones_map.items():
            test_combination(config, pincode, bhiwandi, f"{name} -> Bhiwandi")
    
        # 3. Zone X to Zone Y
        print("\n[TEST SET 3] Zone X to Zone Y (EXPECTED: UNAVAILABLE)")
        test_combination(config, zones_map["North"], zones_map["South 1"], "North -> South 1")
        test_combination(config, zones_map["East"], zones_map["West 1"], "East -> West 1")
    
    # Restore stdout (optional, but good practice)
    sys.stdout = sys.__stdout__

    

if __name__ == "__main__":
    run_tests()
