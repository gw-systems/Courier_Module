import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from courier.models import Order, SystemConfig
    from courier.zones import PINCODE_LOOKUP
    from courier.views.public import lookup_pincode
    print("Imports successful.")
except Exception as e:
    print(f"CRITICAL: Import failed: {e}")
    sys.exit(1)

# Check Pincodes
print(f"Pincode Lookup Size: {len(PINCODE_LOOKUP)}")
if len(PINCODE_LOOKUP) == 0:
    print("CRITICAL: Pincode lookup is empty!")

# Check Orders
try:
    count = Order.objects.count()
    print(f"Total Orders: {count}")
    for o in Order.objects.all()[:5]:
        print(f"Order: {o.order_number}, Status: {o.status}")
except Exception as e:
    print(f"CRITICAL: Failed to query orders: {e}")

# Check Config
try:
    conf = SystemConfig.get_solo()
    print(f"System Config: GST={conf.gst_rate}, Diesel={conf.diesel_price_current}")
except Exception as e:
    print(f"CRITICAL: Failed to load SystemConfig: {e}")
