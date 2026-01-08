import os
import sys
import json
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

def restore_data():
    json_path = BASE_DIR / "data" / "sqlite_data.json"
    print(f"Reading backup from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    couriers_created = 0
    errors = 0
    
    print(f"Found {len(data)} entries in backup.")
    
    # Get valid fields for Courier model
    model_fields = {f.name for f in Courier._meta.get_fields()}
    
    # Known legacy fields handled by CourierManager.create (based on inspection)
    # Re-listing them here to be safe or we can rely on create() to pop them if we pass them.
    # But keys that create() does NOT pop will cause error.
    # We should trust create() to pop what it uses, and WE pop what it doesn't use but exists in dump.
    
    legacy_zonal_keys = [
        'fwd_z_a', 'fwd_z_b', 'fwd_z_c', 'fwd_z_d', 'fwd_z_e', 'fwd_z_f',
        'add_z_a', 'add_z_b', 'add_z_c', 'add_z_d', 'add_z_e', 'add_z_f'
    ]
    
    for entry in data:
        if entry['model'] == 'courier.courier':
            fields = entry['fields']
            
            # Remove keys that assume columns exist but don't anymore, 
            # and are NOT handled by Manager.create.
            sanitized_fields = fields.copy()
            
            for k in legacy_zonal_keys:
                if k in sanitized_fields:
                    sanitized_fields.pop(k) # Drop them, assuming data is also in rate_card JSON
            
            # Also 'rate_logic' is handled by Manager.create.
            
            # Map 'rate_card' -> 'legacy_rate_card_backup'
            if 'rate_card' in sanitized_fields:
                sanitized_fields['legacy_rate_card_backup'] = sanitized_fields.pop('rate_card')

            try:
                print(f"Restoring Courier: {fields.get('name')}")
                Courier.objects.create(**sanitized_fields)
                couriers_created += 1
            except TypeError as e:
                # If we missed some keys
                print(f"FAILED to restore {fields.get('name')} due to TypeError: {e}")
                # Try to identify which key
                # print(f"Keys provided: {list(sanitized_fields.keys())}")
                errors += 1
            except Exception as e:
                print(f"FAILED to restore {fields.get('name')}: {e}")
                errors += 1

                
    print("-" * 30)
    print(f"Restore Complete. Created: {couriers_created}, Errors: {errors}")

if __name__ == "__main__":
    restore_data()
