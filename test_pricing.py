"""
Test script to validate the new pricing engine calculations.
Tests all 3 routing models with proper escalation and GST.
"""
import os
import django
import sys

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courier.engine import calculate_cost
from courier.views.base import load_rates

def print_breakdown(result):
    """Pretty print the cost breakdown"""
    print(f"\n{'='*60}")
    print(f"Carrier: {result['carrier']}")
    print(f"Zone: {result['zone']}")
    print(f"Serviceable: {result.get('servicable', False)}")
    
    if not result.get('servicable'):
        print(f"Error: {result.get('error')}")
        return
    
    breakdown = result.get('breakdown', {})
    
    print(f"\n--- BASE FREIGHT ---")
    print(f"Base Freight: ₹{breakdown.get('base_freight', 0)}")
    
    print(f"\n--- CARRIER SURCHARGES ---")
    print(f"Docket Fee: ₹{breakdown.get('docket_fee', 0)}")
    print(f"Fuel Surcharge: ₹{breakdown.get('fuel_surcharge', 0)}")
    print(f"Hamali Charge: ₹{breakdown.get('hamali_charge', 0)}")
    print(f"FOV Charge: ₹{breakdown.get('fov_charge', 0)}")
    print(f"COD Fee: ₹{breakdown.get('cod_fee', 0)}")
    
    print(f"\n--- SUBTOTAL & MARGINS ---")
    print(f"Subtotal: ₹{breakdown.get('subtotal', 0)}")
    print(f"Escalation ({breakdown.get('escalation_rate', '15%')}): ₹{breakdown.get('escalation_amount', 0)}")
    print(f"After Escalation: ₹{breakdown.get('amount_after_escalation', 0)}")
    
    print(f"\n--- TAX ---")
    print(f"GST ({breakdown.get('gst_rate', '18%')}): ₹{breakdown.get('gst_amount', 0)}")
    
    print(f"\n--- FINAL ---")
    print(f"TOTAL COST: ₹{result['total_cost']}")
    print(f"{'='*60}\n")

def run_tests():
    """Run test cases for all routing models"""
    rates = load_rates()
    
    print("\n" + "="*60)
    print("PRICING ENGINE VALIDATION TESTS")
    print("="*60)
    
    # Test 1: Standard Zonal (Shadowfax)
    print("\n\n🧪 TEST 1: Standard Zonal - Shadowfax Surface")
    print("Route: Pune (411001) → Delhi (110001)")
    print("Weight: 2.5 kg, Mode: Prepaid")
    
    shadowfax = next((r for r in rates if r['carrier_name'] == 'Shadowfax Surface 0.5kg'), None)
    if shadowfax:
        result = calculate_cost(
            weight=2.5,
            source_pincode=411001,
            dest_pincode=110001,
            carrier_data=shadowfax,
            is_cod=False,
            order_value=0
        )
        print_breakdown(result)
    else:
        print("❌ Shadowfax not found")
    
    # Test 2: City-to-City (ACPL)
    print("\n\n🧪 TEST 2: City-to-City - ACPL Surface")
    print("Route: Pune (411001) → Nagpur (440001)")
    print("Weight: 100 kg, Mode: Prepaid")
    
    acpl = next((r for r in rates if r['carrier_name'] == 'ACPL Surface 50kg'), None)
    if acpl:
        result = calculate_cost(
            weight=100,
            source_pincode=411001,
            dest_pincode=440001,
            carrier_data=acpl,
            is_cod=False,
            order_value=0
        )
        print_breakdown(result)
    else:
        print("❌ ACPL not found")
    
    # Test 3: COD Order
    print("\n\n🧪 TEST 3: COD Order - Delhivery Surface")
    print("Route: Mumbai (400001) → Bangalore (560001)")
    print("Weight: 1 kg, Mode: COD, Order Value: ₹5,000")
    
    delhivery = next((r for r in rates if r['carrier_name'] == 'Delhivery Surface 0.5kg'), None)
    if delhivery:
        result = calculate_cost(
            weight=1.0,
            source_pincode=400001,
            dest_pincode=560001,
            carrier_data=delhivery,
            is_cod=True,
            order_value=5000
        )
        print_breakdown(result)
    else:
        print("❌ Delhivery not found")
    
    # Test 4: Custom Zonal (V-Trans) - if available
    print("\n\n🧪 TEST 4: Custom Zonal Matrix - V-Trans")
    print("Route: Pune (411001) → Kolkata (700001)")
    print("Weight: 150 kg, Mode: Prepaid")
    
    vtrans = next((r for r in rates if r['carrier_name'] == 'V-Trans 100kg'), None)
    if vtrans:
        result = calculate_cost(
            weight=150,
            source_pincode=411001,
            dest_pincode=700001,
            carrier_data=vtrans,
            is_cod=False,
            order_value=0
        )
        print_breakdown(result)
    else:
        print("❌ V-Trans not found")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)

if __name__ == '__main__':
    run_tests()
