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

from courier.models import Courier, CityRoute

def restore_city_rates():
    json_path = BASE_DIR / "data" / "sqlite_data.json"
    print(f"Reading backup from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    created_count = 0
    
    for entry in data:
        if entry['model'] == 'courier.courier':
            fields = entry['fields']
            name = fields.get('name')
            
            # Check if this carrier uses City_To_City logic
            # OR if it just has city_rates in the JSON
            rate_card = fields.get('rate_card', {})
            routing_logic = rate_card.get('routing_logic', {})
            city_rates = routing_logic.get('city_rates')
            
            if city_rates and isinstance(city_rates, dict):
                print(f"Restoring City Routes for: {name}")
                try:
                    courier = Courier.objects.get(name=name)
                except Courier.DoesNotExist:
                    print(f" - Courier {name} not found in DB. Skipping.")
                    continue
                
                # Clear existing to prevent duplicates
                # courier.city_routes.all().delete() 
                # Actually, let's keep it safe. If count is 0, we proceed.
                if courier.city_routes.count() > 0:
                    print(f" - Routes determine to exist ({courier.city_routes.count()}). Skipping overwrite.")
                    continue
                
                for city, rate in city_rates.items():
                    if rate is not None:
                        CityRoute.objects.create(
                            courier=courier,
                            city_name=city,
                            rate_per_kg=Decimal(str(rate))
                        )
                        created_count += 1
                
                print(f" - Restored {len(city_rates)} cities.")
            
    print("-" * 30)
    print(f"City Rates Restoration Complete. Created: {created_count}")

if __name__ == "__main__":
    restore_city_rates()
