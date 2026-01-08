import os
import sys
import django
import glob

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
print(f"DB Path from settings: {settings.DATABASES['default']['NAME']}")

# List .db files
print("DB files in root:")
for f in glob.glob("*.db") + glob.glob("*.sqlite3"):
    print(f" - {f} ({os.path.getsize(f)} bytes)")

try:
    from courier.models import Order
    count = Order.objects.count()
    print(f"Total Orders in DB: {count}")
    
    if count > 0:
        print("First 3 orders:")
        for o in Order.objects.all()[:3]:
            print(f" - {o.order_number}: {o.status}")
    else:
        print("Checking if table exists by creating a dummy? No, safe read only.")
        
except Exception as e:
    print(f"Error querying orders: {e}")
