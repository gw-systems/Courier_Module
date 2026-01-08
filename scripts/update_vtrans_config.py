import os
import sys
import django
import json
from pathlib import Path
from decimal import Decimal

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

def update_vtrans():
    try:
        # 1. Fetch Carrier
        # Using icontains to be safe, but exact match 'V-Trans 100kg' is preferred if known
        c = Courier.objects.get(name='V-Trans 100kg')
        print(f"Updating configuration for: {c.name}")
        
        # 2. Update Standard Model Fields (Source of Truth for these values)
        # Fixed Fees
        c.docket_fee = Decimal('100.00')
        c.eway_bill_fee = Decimal('0.00') # Explicitly 0 as per requirement
        c.cod_charge_fixed = Decimal('35.00') # Existing value, ensuring it stays
        c.appointment_delivery_fee = Decimal('0.00')
        
        # Variable Fees
        c.hamali_per_kg = Decimal('0.20')
        c.cod_charge_percent = Decimal('1.75') # Existing
        
        # Disable standard FOV in favor of Owner's Risk
        c.fov_insured_percent = Decimal('0.00')
        
        # Fuel (10%)
        # Note: Model stores this in linked FuelConfiguration object
        c.fuel_surcharge_percent = Decimal('0.10')
        c.fuel_is_dynamic = False
        
        # 3. Update Legacy Backup (to inject 'owners_risk' which isn't in model yet)
        backup = c.legacy_rate_card_backup or {}
        
        if 'variable_fees' not in backup:
            backup['variable_fees'] = {}
            
        # Inject Owner's Risk
        # 0.2% = 0.002
        backup['variable_fees']['owners_risk'] = {
            "percent": 0.002, 
            "min_amount": 0
        }
        
        # Remove conflicting keys from backup if they exist, to ensure Model takes precedence
        # (Though our merge logic overlays backup ON TOP of model for un-handled keys, 
        #  so we want to make sure we don't accidentally override model values with old backup garbage)
        keys_to_clean = ['docket_fee', 'hamali_per_kg', 'fuel_config']
        # Actually variable fees are inside a dict, so clean sub-keys
        if 'docket_fee' in backup.get('fixed_fees', {}):
             del backup['fixed_fees']['docket_fee']
             
        if 'fov_insured_percent' in backup.get('variable_fees', {}):
            del backup['variable_fees']['fov_insured_percent']
            
        c.legacy_rate_card_backup = backup
        c.save()
        
        print("Successfully updated V-Trans 100kg configuration.")
        
        # 4. Verify Output
        # Re-fetch to ensure clean state
        c.refresh_from_db()
        rc = c.get_rate_dict()
        
        print("\n--- Verified Rate Card Output ---")
        print(json.dumps(rc, indent=2, default=str))
        
        # Assertions
        assert rc['fixed_fees']['docket_fee'] == 100.0, f"Docket fee mismatch: {rc['fixed_fees']['docket_fee']}"
        assert rc['variable_fees']['hamali_per_kg'] == 0.2, f"Hamali mismatch: {rc['variable_fees']['hamali_per_kg']}"
        assert rc['fuel_config']['flat_percent'] == 0.1, f"Fuel mismatch: {rc['fuel_config']['flat_percent']}"
        assert rc['variable_fees'].get('owners_risk'), "Owner's Risk missing"
        assert rc['variable_fees']['owners_risk']['percent'] == 0.002, "Owner's Risk percent mismatch"
        
        print("\nAll verifications passed!")
        
    except Courier.DoesNotExist:
        print("Error: V-Trans 100kg carrier not found!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_vtrans()
