import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Order, Courier, CourierZoneRate

def check_integrity():
    print(f"Checking DB at: {django.conf.settings.DATABASES['default']['NAME']}")
    
    print(f"Total Orders: {Order.objects.count()}")
    print(f"Total Couriers: {Courier.objects.count()}")
    print(f"Total Zone Rates: {CourierZoneRate.objects.count()}")
    
    cities = Courier.objects.filter(city_routes__isnull=False).distinct().count()
    print(f"Couriers with City Routes: {cities}")
    
    # Check a sample courier for rates
    c = Courier.objects.first()
    if c:
        print(f"Sample Courier: {c.name}")
        print(f" - Zone Rates: {c.zone_rates.count()}")
        print(f" - City Routes: {c.city_routes.count()}")
        
        # Check raw dict
        try:
            d = c.get_rate_dict()
            fwd = d.get('routing_logic', {}).get('zonal_rates', {}).get('forward', {})
            print(f" - API Dict Forward Rates keys: {list(fwd.keys()) if fwd else 'None'}")
        except Exception as e:
            print(f" - Error getting rate dict: {e}")

if __name__ == "__main__":
    check_integrity()
