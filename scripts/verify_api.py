import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/compare-rates"

def test_single_box_legacy():
    print("\n--- Testing Legacy Single Weight ---")
    payload = {
        "source_pincode": 400001,
        "dest_pincode": 110001,
        "weight": 10,
        "is_cod": False,
        "order_value": 0,
        "mode": "Both"
    }
    try:
        res = requests.post(API_URL, json=payload)
        if res.status_code == 200:
            print("SUCCESS: Legacy request works.")
            print(f"Rates count: {len(res.json())}")
        else:
            print(f"FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR: {e}")

def test_multi_box_payload():
    print("\n--- Testing Multi-Box Payload ---")
    # Box 1: 5kg, 10x10x10 (Vol ~ 0.02) -> Applicable 5
    # Box 2: 2kg, 40x40x40 (Vol ~ 64000/5000 = 12.8) -> Applicable 12.8
    # Total should be 17.8
    
    payload = {
        "source_pincode": 400001,
        "dest_pincode": 110001,
        "is_cod": False,
        "order_value": 0,
        "mode": "Both",
        "orders": [
            {"weight": 5, "length": 10, "width": 10, "height": 10},
            {"weight": 2, "length": 40, "width": 40, "height": 40}
        ]
    }
    try:
        res = requests.post(API_URL, json=payload)
        if res.status_code == 200:
            rates = res.json()
            print("SUCCESS: Multi-box request works.")
            print(f"Rates count: {len(rates)}")
            if rates:
                print(f"Sample Total Cost: {rates[0]['total_cost']}")
        else:
            print(f"FAILED: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_single_box_legacy()
    test_multi_box_payload()
