import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from courier.models import Courier
from courier.engine import calculate_cost

# Get ACPL courier
acpl = Courier.objects.filter(name__icontains='ACPL').first()

print(f"ACPL Courier: {acpl.name}")
print(f"Active: {acpl.is_active}")
print(f"Min Weight: {acpl.min_weight}")
print(f"Required Source City: {acpl.required_source_city}")

# Get config
config = acpl.get_rate_dict()
print(f"\nRouting Logic Type: {config.get('routing_logic', {}).get('type')}")
print(f"Hub City: {config.get('routing_logic', {}).get('hub_city')}")

# Test Gandhidham -> Bhiwandi
print("\n" + "="*60)
print("Testing: Gandhidham (370201) -> Bhiwandi (421308), 100kg")
print("="*60)

result = calculate_cost(100, 370201, 421308, config)

print(f"Serviceable: {result.get('servicable')}")
print(f"Zone: {result.get('zone')}")
print(f"Error: {result.get('error')}")
if result.get('servicable'):
    print(f"Total Cost: ₹{result.get('total_cost')}")
    
# Test Bhiwandi -> Gandhidham (regression)
print("\n" + "="*60)
print("Testing: Bhiwandi (421308) -> Gandhidham (370201), 100kg")
print("="*60)

result2 = calculate_cost(100, 421308, 370201, config)

print(f"Serviceable: {result2.get('servicable')}")
print(f"Zone: {result2.get('zone')}")
print(f"Error: {result2.get('error')}")
if result2.get('servicable'):
    print(f"Total Cost: ₹{result2.get('total_cost')}")
