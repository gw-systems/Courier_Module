
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

def debug():
    c = Courier.objects.filter(name__icontains='ACPL').first()
    if c:
        print(f"Name: {c.name}")
        print(f"Min Freight: {c.rate_card.get('min_freight')}")
        rates = c.rate_card.get("routing_logic", {}).get("city_rates", {})
        print(f"Rate for Gandhidham: {rates.get('gandhidham')}")
    else:
        print("ACPL Not Found")

if __name__ == "__main__":
    debug()
