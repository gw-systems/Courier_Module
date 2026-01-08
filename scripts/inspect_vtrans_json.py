import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
json_path = BASE_DIR / "data" / "sqlite_data.json"

with open(json_path, 'r') as f:
    data = json.load(f)

for entry in data:
    if entry['model'] == 'courier.courier':
        props = entry['fields']
        if 'V-Trans' in props.get('name', ''):
            print(f"Found: {props['name']}")
            print(f"Keys: {list(props.keys())}")
            # Print legacy zonal keys
            zonal_keys = [k for k in props.keys() if 'z_' in k]
            print(f"Legacy Zonal Keys: {zonal_keys}")
            for k in zonal_keys:
                print(f"  {k}: {props[k]}")
            
            # Print rate_card zonal 
            rc = props.get('rate_card', {})
            rl = rc.get('routing_logic', {})
            zr = rl.get('zonal_rates', {})
            print(f"JSON Zonal Rates: {zr}")
            # Continue searching in case of duplicates or multiple entries
