import requests
import json

url = "http://127.0.0.1:8000/api/compare-rates"
payload = {
    "source_pincode": 400001,
    "dest_pincode": 400708,
    "weight": 1.0,
    "mode": "Both",
    "is_cod": False,
    "order_value": 1000.0
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        results = response.json()
        print(f"Total results returned: {len(results)}")
        for r in results:
            print(f"- {r['carrier']}: {r['total_cost']}")
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
