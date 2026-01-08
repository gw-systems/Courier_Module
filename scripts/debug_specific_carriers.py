import os
import sys
import django
from pathlib import Path
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier, CityRoute, CourierZoneRate

def debug_carriers():
    print("=== ACPL Debug ===")
    try:
        acpl = Courier.objects.get(name__icontains="ACPL")
        print(f"Name: {acpl.name}")
        print(f"Logic: {acpl.rate_logic}")
        print(f"Active: {acpl.is_active}")
        
        # Check City Routes
        routes = acpl.city_routes.all()
        print(f"City Routes count: {routes.count()}")
        
        # Check Ghaziabad
        gzb_route = acpl.city_routes.filter(city_name__icontains="ghaziabad")
        if gzb_route.exists():
            for r in gzb_route:
                print(f" - Route found: {r.city_name} -> {r.rate_per_kg}")
        else:
            print(" - No route found for Ghaziabad")
            
    except Courier.DoesNotExist:
        print("ACPL not found.")

    print("\n=== V-Trans Debug ===")
    try:
        vtrans = Courier.objects.get(name__icontains="V-Trans")
        print(f"Name: {vtrans.name}")
        print(f"Logic: {vtrans.rate_logic}")
        print(f"Active: {vtrans.is_active}")
        
        # Check Zonal Rates
        z_rates = vtrans.zone_rates.all()
        print(f"Zone Rules: {z_rates.count()}")
        if z_rates.count() > 0:
            print(f"Sample Rate: {z_rates.first()}")
            
        # Check Custom Zone Rates if generic is empty
        c_rates = vtrans.custom_zone_rates.all()
        print(f"Custom Zone Rates: {c_rates.count()}")
        
    except Courier.DoesNotExist:
        print("V-Trans not found.")

if __name__ == "__main__":
    debug_carriers()
