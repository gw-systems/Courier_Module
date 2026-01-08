import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier, CourierZoneRate

def fix_vtrans():
    try:
        courier = Courier.objects.get(name__icontains="V-Trans")
        print(f"Fixing rates for: {courier.name}")
        
        # Define default rates for PTL (Surface)
        # Assuming simple progressive zonal rates
        defaults = {
            "z_a": 4.00, # Metro
            "z_b": 4.50, # Region
            "z_c": 5.50, # Intercity
            "z_d": 6.50, # ROI
            "z_e": 8.00, # NE
            "z_f": 10.00 # Special
        }
        
        # Clear existing zero rates
        courier.zone_rates.all().delete()
        
        count = 0
        for zone, rate in defaults.items():
            # Forward
            CourierZoneRate.objects.create(
                courier=courier,
                zone_code=zone,
                rate_type=CourierZoneRate.RateType.FORWARD,
                rate=Decimal(str(rate))
            )
            # Additional (slightly cheaper)
            CourierZoneRate.objects.create(
                courier=courier,
                zone_code=zone,
                rate_type=CourierZoneRate.RateType.ADDITIONAL,
                rate=Decimal(str(rate - 0.50))
            )
            count += 2
            
        print(f"Created {count} rates for V-Trans.")
        
    except Courier.DoesNotExist:
        print("V-Trans carrier not found.")

if __name__ == "__main__":
    fix_vtrans()
