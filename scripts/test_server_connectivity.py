import urllib.request
import urllib.error
import json

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(path):
    url = f"{BASE_URL}{path}"
    print(f"Checking {url}...")
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            print(f"Status: {response.status}")
            data = response.read()
            print(f"Response: {data[:100]}...")
            return True
    except urllib.error.URLError as e:
        print(f"Failed: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

print("Testing Server Connectivity...")
if check_endpoint("/api/health"):
    print("Health Check Passed.")
else:
    print("Health Check Failed.")

if check_endpoint("/api/orders/"):
    print("Orders API Accessible.")
else:
    print("Orders API Failed.")
