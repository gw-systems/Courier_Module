import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier
from courier.engine import calculate_cost

# Define Test Cases
scenarios = [
    {"carrier": "Shadowfax", "weight": 0.5},
    {"carrier": "Shadowfax", "weight": 5.0},
    {"carrier": "DTDC", "weight": 0.5},
    {"carrier": "DTDC", "weight": 5.0},
    {"carrier": "Delhivery Surface 5kg", "weight": 4.0}, # Test below limit
    {"carrier": "Delhivery Surface 5kg", "weight": 6.0}, # Test above limit (should fail or surcharge?)
    {"carrier": "Delhivery Surface 20kg", "weight": 15.0},
    {"carrier": "Delhivery Surface 20kg", "weight": 25.0}, # Test above limit
    {"carrier": "Delhivery Surface 10kg", "weight": 14.0}, # New Request
    {"carrier": "V-Trans 100kg", "weight": 50.0}, # Below min (should charge for 100)
    {"carrier": "V-Trans 100kg", "weight": 110.0}, # Normal
    {"carrier": "ACPL Surface", "weight": 25.0, "source": 421308, "dest": 370201}, # Bhiwandi -> Gandhidham (25kg -> Min 50)
    {"carrier": "ACPL Surface", "weight": 150.0, "source": 421308, "dest": 370201} # Bhiwandi -> Gandhidham (150kg)
]

# Standard Route (Pune -> Delhi, Zone A/Metros)
source = 411001
dest = 110001
val = 2000

print("-" * 60)
print(f"{'CARRIER':<20} | {'WEIGHT':<8} | {'STATUS':<10} | {'TOTAL':<10} | {'BREAKDOWN'}")
print("-" * 60)

for case in scenarios:
    name_part = case["carrier"]
    w = case["weight"]
    
    # Allow override destination for specific tests (e.g. ACPL needs Mumbai)
    current_dest = case.get("dest", dest)
    current_source = case.get("source", source)
    
    # Fuzzy match carrier
    c = Courier.objects.filter(name__icontains=name_part, is_active=True).first()
    
    if not c:
        print(f"{name_part:<20} | {w:<8} | {'MISSING':<10} | {'-':<10} | Carrier not found")
        continue

    print(f"Testing {c.name} (Dest: {current_dest})...") if "ACPL" in c.name else None
    if "ACPL" in c.name:
         print(f"DEBUG: ID={c.id}, RequiredSrc={c.rate_card.get('required_source_city')}")

    try:
        res = calculate_cost(
            weight=w,
            source_pincode=current_source,
            dest_pincode=current_dest,
            carrier_data=c.get_rate_dict(),
            is_cod=False,
            order_value=val
        )
        
        status = "OK" if res.get("servicable") else "FAIL"
        total = res.get("total_cost", 0)
        
        # Simplify breakdown for display
        bd = res.get("breakdown", {})
        bd_str = f"Base:{bd.get('base_transport_cost',0)}, Fuel:{bd.get('fuel_surcharge',0)}, GST:{bd.get('gst_amount',0)}"
        if res.get("error"):
            bd_str = res.get("error")
            
        print(f"{c.name:<20} | {w:<8} | {status:<10} | {total:<10} | {bd_str}")
        
    except Exception as e:
        print(f"{name_part:<20} | {w:<8} | {'ERROR':<10} | {'-':<10} | {str(e)}")

print("-" * 60)
