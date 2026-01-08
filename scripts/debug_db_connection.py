import os
import sys
import django
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from courier.models import Order, Courier

def debug_db():
    print(f"DEBUG: BASE_DIR is {BASE_DIR}")
    print(f"DEBUG: Databases Config: {settings.DATABASES}")
    
    db_path = settings.DATABASES['default'].get('NAME')
    print(f"DEBUG: Expected DB Path: {db_path}")
    
    if os.path.exists(db_path):
        print("DEBUG: DB file exists on disk.")
        print(f"DEBUG: DB file size: {os.path.getsize(db_path)} bytes")
    else:
        print("DEBUG: DB FILE NOT FOUND AT PATH!")

    print("-" * 30)
    
    try:
        courier_count = Courier.objects.count()
        print(f"Couriers in DB: {courier_count}")
        for c in Courier.objects.all()[:5]:
            print(f" - {c.name} (Active: {c.is_active})")
    except Exception as e:
        print(f"ERROR querying Couriers: {e}")

    try:
        order_count = Order.objects.count()
        print(f"Orders in DB: {order_count}")
        if order_count > 0:
            print("Last 5 Orders:")
            for o in Order.objects.order_by('-created_at')[:5]:
                print(f" - {o.order_number} | {o.recipient_name} | Status: {o.status}")
        else:
            print("WARNING: No orders found.")
    except Exception as e:
        print(f"ERROR querying Orders: {e}")

if __name__ == "__main__":
    debug_db()
