import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from courier.models import Courier
for c in Courier.objects.all():
    print(f"DB: {c.name}: Mode='{c.carrier_mode}', Source='{c.required_source_city}', Active={c.is_active}")
