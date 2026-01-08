"""
Quick verification of migration 0021.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

# BlueDart
try:
    bd = Courier.objects.get(name="Blue Dart")
    print(f"BlueDart CSV: {bd.serviceable_pincode_csv}")
except:
    print("BlueDart: NOT FOUND")

# ACPL
try:
    acpl = Courier.objects.filter(name__icontains='ACPL').first()
    if acpl:
        print(f"ACPL hub_city: {acpl.hub_city}")
        print(f"ACPL min_weight: {acpl.min_weight}")
        print(f"ACPL required_source: {acpl.required_source_city}")
    else:
        print("ACPL: NOT FOUND")
except Exception as e:
    print(f"ACPL ERROR: {e}")

# V-Trans
try:
    vt = Courier.objects.get(name="V-Trans 100kg")
    print(f"V-Trans rate_logic: {vt.rate_logic}")
    print(f"V-Trans custom_zones: {vt.custom_zones.count()}")
except:
    print("V-Trans: NOT FOUND")
