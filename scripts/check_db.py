import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from courier.models import Courier
for c in Courier.objects.filter(serviceable_pincode_csv__isnull=False):
    print(f"DB: {c.name}: '{c.serviceable_pincode_csv}'")
