import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from courier.models import Courier
updated = Courier.objects.filter(serviceable_pincode_csv="BlueDart_Servicable Pincodes.csv").update(serviceable_pincode_csv="BlueDart_Serviceable Pincodes.csv")
print(f"Updated {updated} carriers.")
