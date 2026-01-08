import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier, CustomZone, CustomZoneRate

def check_custom_zones():
    print(f"Checking DB: {django.conf.settings.DATABASES['default']['NAME']}")
    
    # Check counts
    cz_count = CustomZone.objects.count()
    czr_count = CustomZoneRate.objects.count()
    
    print(f"Custom Zones: {cz_count}")
    print(f"Custom Zone Rates: {czr_count}")
    
    if cz_count > 0:
        print("Sample Zones:")
        for z in CustomZone.objects.all()[:5]:
            print(f" - {z.zone_code}: {z.location_name} (Courier: {z.courier.name})")

    if czr_count > 0:
        print("Sample Rates:")
        for r in CustomZoneRate.objects.all()[:5]:
            print(f" - {r.from_zone} -> {r.to_zone}: {r.rate_per_kg}")

    # Check V-Trans
    try:
        vt = Courier.objects.get(name__icontains="V-Trans")
        print(f"V-Trans: {vt.name}")
        print(f" - Logic: {vt.rate_logic}")
        print(f" - Custom Zones Linked: {vt.custom_zones.count()}")
        print(f" - Custom Rates Linked: {vt.custom_zone_rates.count()}")
    except Courier.DoesNotExist:
        print("V-Trans not found")

if __name__ == "__main__":
    check_custom_zones()
