import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.engine import calculate_cost
from courier.models import Courier

def test_calc():
    couriers = Courier.objects.filter(is_active=True)
    print(f"Total active couriers: {couriers.count()}")
    
    for c in couriers:
        try:
            data = c.get_rate_dict()
            # Test cases: Pincodes that should work for most
            source = 421302 if "ACPL" in c.name else 400001
            dest = 400001 if source == 421302 else 400708
            
            res = calculate_cost(
                weight=10.0,
                source_pincode=source,
                dest_pincode=dest,
                carrier_data=data
            )
            print(f"[{'PASS' if res.get('servicable') else 'FAIL'}] {c.name:25} Logic: {c.rate_logic:15} Total: {res.get('total_cost', 0):8} Error: {res.get('error')}")
            
        except Exception as e:
            print(f"[ERROR] {c.name:25} {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_calc()
