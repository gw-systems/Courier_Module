from django.test import TestCase
from courier.models import Courier
from decimal import Decimal

class RefactorIntegrityTest(TestCase):
    def test_facade_and_manager(self):
        # 1. Create Courier using Legacy kwargs
        # This exercises CourierManager.create -> populates FeeStructure etc.
        c = Courier.objects.create(
            name="Test Facade Courier",
            docket_fee=Decimal("100.00"),
            min_weight=3.5,
            rate_logic="City_To_City",
            cod_charge_fixed=Decimal("50.00")
        )
        
        # 2. Verify Legacy Columns are GONE (Implicit, accessing them would be via property now)
        # But we want to verify the property READS from the new table.
        
        # Verify Reverse Relations exist
        self.assertTrue(hasattr(c, 'fees_config'))
        self.assertTrue(hasattr(c, 'constraints_config'))
        self.assertTrue(hasattr(c, 'routing_config'))
        
        # 3. Verify Data Correctness via Properties
        self.assertEqual(c.docket_fee, Decimal("100.00")) # Property getter
        self.assertEqual(c.min_weight, 3.5)
        self.assertEqual(c.cod_charge_fixed, Decimal("50.00"))
        
        # 4. Verify Data Correctness via Direct Access (Internal)
        self.assertEqual(c.fees_config.docket_fee, Decimal("100.00"))
        self.assertEqual(c.constraints_config.min_weight, 3.5)
        self.assertEqual(c.routing_config.logic_type, "City_To_City")

        # 5. Verify Engine Dictionary (The most important part)
        data = c.get_rate_dict()
        self.assertEqual(data["fixed_fees"]["docket_fee"], 100.0)
        self.assertEqual(data["min_weight"], 3.5)
        self.assertEqual(data["logic"], "city_to_city") # Mapping check
        
        # 6. Verify Update via Property
        c.docket_fee = Decimal("200.00")
        # Note: Property setter creates/saves.
        
        c.refresh_from_db() # Reload to ensure saved
        self.assertEqual(c.fees_config.docket_fee, Decimal("200.00"))
        self.assertEqual(c.get_rate_dict()["fixed_fees"]["docket_fee"], 200.0)
        
        print("\n✅ Facade Integrity Test Passed: Manager and Properties working seamlessly.")
