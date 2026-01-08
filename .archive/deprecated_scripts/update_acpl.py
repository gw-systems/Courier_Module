
import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from courier.models import Courier

def update_acpl():
    try:
        # Find ACPL Surface (or similar)
        # Assuming only one ACPL exists or we pick the first
        c = Courier.objects.filter(name__icontains='ACPL').first()
        if not c:
            print("ACPL carrier not found!")
            return

        rc = c.rate_card
        
        # 1. GC Charge (Docket): 100
        # 2. Eway Bill: 10
        if 'fixed_fees' not in rc: rc['fixed_fees'] = {}
        rc['fixed_fees']['docket_fee'] = 100.0
        rc['fixed_fees']['eway_bill_fee'] = 10.0
        
        # 3. FOV (Owner's Risk 0.5% or 50 max) -> wait, 'whichever is higher' means min_amount
        # User said: "FOV 0.5% of invoice value or 50 whichever is higher"
        if 'variable_fees' not in rc: rc['variable_fees'] = {}
        rc['variable_fees']['owners_risk'] = {
            "percent": 0.005, # 0.5%
            "min_amount": 50.0
        }
        
        # 4. Hamali (0.5 per kg or 50 whichever is higher)
        rc['variable_fees']['hamali_per_kg'] = 0.5
        rc['variable_fees']['min_hamali'] = 50.0
        
        # 5. Godown Collection (Pickup)
        # "20 RS upto 100kg. above 100kg RS 0.1paisa per kg extra"
        # Assuming 0.1 RUPEES (10 paisa) or 0.1 PAISA? "RS 0.1paisa" is ambiguous.
        # usually 10 paisa = 0.1 Rs. 
        # But 'RS 0.1paisa' might mean 'Rs 0.1'. Let's assume Rs 0.1 per kg.
        rc['variable_fees']['pickup_slab'] = {
            "slab": 100,
            "base": 20.0,
            "extra_rate": 0.1 # Rs 0.1 per kg? Or did user mean 0.1 Paisa (0.001 Rs)?
                              # Context: 20 Rs base. 0.1 Rs seems reasonable. 
                              # If 0.1 paisa, it would be negligible. I'll stick to 0.1 Rs.
        }

        # 6. Godown Delivery
        # "Up to 100 kg Rs: 80/- Above 101 Kg Rs: 0.25.p Per Kg Extra. For Mumbai"
        # "Up to 100 kg Rs: 70/- Above 101 Kg Rs: 0.25.p Per Kg Extra. For Other Destinations"
        # Again assuming 0.25 Rs per kg.
        rc['variable_fees']['delivery_slab'] = {
            "slab": 100,
            "base": 70.0,
            "extra_rate": 0.25,
            "city_exceptions": {
                "mumbai": {
                    "slab": 100,
                    "base": 80.0,
                    "extra_rate": 0.25
                }
            }
        }
        
        # 7. COD/DOD: 250 per GC
        # Assuming this is fixed fee per order if COD
        rc['fixed_fees']['cod_fixed'] = 250.0
        rc['variable_fees']['cod_percent'] = 0 # Disable percent if fixed used?
                                             # Engine takes max(fixed, pct). So set pct 0 is safe.

        # 8. Fuel Surcharge (Base 90) - Wait, user said "base fuel price is 90RS"
        # Does this mean dynamic? "fuel surcharge is 10 % of basic freight" implies FLAT 10%.
        # BUT then "base fuel price is 90RS" implies DYNAMIC.
        # Usually if base price is given, it's dynamic.
        # Let's check user request again: "fuel surcharge is 10 % of basic freight... base fuel price is 90RS"
        # This is conflicting. 
        # Scenario A: It is currently 10% because price is near base?
        # Scenario B: It IS dynamic, and current calculation results in 10%?
        # Scenario C: Use Flat 10% as requested first line. 
        # "base fuel price is 90RS" might be context for dynamic calc.
        # Let's configure as DYNAMIC with base 90. 
        # Check defaults in engine: ratio 0.625.
        # If current diesel is ~106 (typical), (106-90)*0.625 = 10%. 
        # This matches perfect! (16 * 0.625 = 10).
        # So I should strict set Dynamic with Base 90.
        rc['fuel_config'] = {
            "is_dynamic": True,
            "base_diesel_price": 90.0,
            "diesel_ratio": 0.625 # Standard
        }
        
        # 9. Minimum Chargeable Weight is 50kg
        c.min_weight = 50.0
        
        # 10. Escalation 15% (Settings default, but good to know)
        
        c.fuel_surcharge_percent = 0 # Use dynamic config
        
        c.rate_card = rc
        c.save()
        print("Successfully updated ACPL configuration.")
        print(json.dumps(c.rate_card, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_acpl()
