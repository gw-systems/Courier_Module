import os
import sys
import json
import django
from pathlib import Path
from decimal import Decimal

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier, CourierZoneRate

def restore_rates():
    json_path = BASE_DIR / "data" / "sqlite_data.json"
    print(f"Reading backup from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    rates_created = 0
    
    # Map legacy keys to Zone Codes
    # Keys like 'fwd_z_a' -> zone_code='z_a', rate_type='forward'
    # Keys like 'add_z_a' -> zone_code='z_a', rate_type='additional'
    
    zone_suffix_map = {
        'z_a': 'z_a', 'z_b': 'z_b', 'z_c': 'z_c', 
        'z_d': 'z_d', 'z_e': 'z_e', 'z_f': 'z_f'
    }
    
    for entry in data:
        if entry['model'] == 'courier.courier':
            fields = entry['fields']
            name = fields.get('name')
            
            try:
                courier = Courier.objects.get(name=name)
            except Courier.DoesNotExist:
                print(f"Skipping {name} - Courier not found in DB")
                continue

            # Check if rates already exist to avoid duplicates
            if courier.zone_rates.exists():
                 # Maybe delete old ones? Or skip?
                 # Let's delete old ones to be safe and ensure fresh state
                 courier.zone_rates.all().delete()
            
            # Identify legacy fields
            for key, value in fields.items():
                if value is None: continue
                
                rate_type = None
                zone_code = None
                
                if key.startswith('fwd_'):
                    rate_type = CourierZoneRate.RateType.FORWARD
                    suffix = key[4:] # remove 'fwd_'
                    if suffix in zone_suffix_map:
                        zone_code = zone_suffix_map[suffix]
                        
                elif key.startswith('add_'):
                    rate_type = CourierZoneRate.RateType.ADDITIONAL
                    suffix = key[4:] # remove 'add_'
                    if suffix in zone_suffix_map:
                        zone_code = zone_suffix_map[suffix]
                
                if rate_type and zone_code:
                    # Create Rate
                    CourierZoneRate.objects.create(
                        courier=courier,
                        zone_code=zone_code,
                        rate_type=rate_type,
                        rate=Decimal(str(value))
                    )
                    rates_created += 1
                    
    print("-" * 30)
    print(f"Rates Restoration Complete. Created: {rates_created} rates.")

if __name__ == "__main__":
    restore_rates()
