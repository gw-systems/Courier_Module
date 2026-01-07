
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

def update_vtrans():
    try:
        c = Courier.objects.get(name='V-Trans 100kg')
        rc = c.rate_card
        
        # 1. GC Charge (Docket)
        if 'fixed_fees' not in rc: rc['fixed_fees'] = {}
        rc['fixed_fees']['docket_fee'] = 100.0
        
        # 2. Hamali (0.2 per kg)
        if 'variable_fees' not in rc: rc['variable_fees'] = {}
        rc['variable_fees']['hamali_per_kg'] = 0.2
        
        # 3. FOV (Owner's Risk - 0.2%)
        # Note: Removing old keys to avoid conflict
        if 'fov_insured_percent' in rc['variable_fees']:
            del rc['variable_fees']['fov_insured_percent']
            
        rc['variable_fees']['owners_risk'] = {
            "percent": 0.002, # 0.2%
            "min_amount": 0
        }
        
        # 4. Fuel Surcharge (10%)
        # IMPORTANT: Model 'save' method overwrites JSON from model field.
        # So we must update the model field.
        c.fuel_surcharge_percent = 0.10
        # No need to manually set rc['fuel_config'] as save() handles it.
        
        c.rate_card = rc
        c.save()
        print("Successfully updated V-Trans 100kg configuration.")
        print(json.dumps(c.rate_card, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_vtrans()
