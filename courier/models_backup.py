from django.db import models
from django.utils import timezone
from django.utils import timezone
from decimal import Decimal
from .models_refactored import FeeStructure, ServiceConstraints, FuelConfiguration, RoutingLogic


class Courier(models.Model):
    """
    Courier model to store rate cards and configuration.
    Replaces master_card.json.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Carrier Name")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    # New Normalized Relations (Facade)
    fees = models.OneToOneField(FeeStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name='courier')
    constraints = models.OneToOneField(ServiceConstraints, on_delete=models.SET_NULL, null=True, blank=True, related_name='courier')
    fuel_config = models.OneToOneField(FuelConfiguration, on_delete=models.SET_NULL, null=True, blank=True, related_name='courier')
    routing = models.OneToOneField(RoutingLogic, on_delete=models.SET_NULL, null=True, blank=True, related_name='courier')
    
    # Friendly Configuration Fields
    carrier_type = models.CharField(max_length=20, default="Courier", choices=[("Courier","Courier"),("PTL","PTL")])
    carrier_mode = models.CharField(max_length=20, default="Surface", choices=[("Surface","Surface"),("Air","Air")])
    rate_logic = models.CharField(
        max_length=20, 
        default="Zonal_Standard", 
        choices=[
            ("Zonal_Standard","Zonal (Standard A-F Zones)"),
            ("Zonal_Custom","Zonal (Custom Zone Matrix)"),
            ("City_To_City","City to City Routes"),
            ("Region_CSV","Regional (CSV Based)")
        ],
        help_text="Select the routing logic type"
    )
    
    min_weight = models.FloatField(default=0.5, help_text="Min weight in kg")
    max_weight = models.FloatField(default=99999.0, help_text="Max weight in kg")
    volumetric_divisor = models.IntegerField(default=5000, help_text="e.g. 5000 or 4500")
    
    # Advanced / Source Config
    required_source_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Required Source City", help_text="Restrict service to this city only")
    serviceable_pincode_csv = models.CharField(max_length=255, blank=True, null=True, verbose_name="Serviceable CSV", help_text="Filename for CSV-based logic (e.g. BlueDart_...csv)")
    hub_city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hub City", help_text="Hub city for City-to-City logic")
    hub_pincode_prefixes = models.JSONField(blank=True, null=True, verbose_name="Hub Pincode Prefixes", help_text="List of pincode prefixes for hub city validation (e.g. ['4213'] for Bhiwandi)")
    
    cod_charge_fixed = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="COD Fixed Fee")
    cod_charge_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="COD % (ratio, e.g. 0.015)")

    # Fuel Surcharge Configuration
    fuel_surcharge_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="Fuel Surcharge % (ratio)")
    fuel_is_dynamic = models.BooleanField(default=False, verbose_name="Dynamic Fuel Surcharge")
    fuel_base_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Base Diesel Price")
    fuel_ratio = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="Diesel Ratio")
    
    # Fixed Fees
    docket_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Docket Fee")
    eway_bill_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="E-Way Bill Fee")
    appointment_delivery_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Appointment Delivery Fee")

    # Variable Fees
    hamali_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Hamali (per kg)")
    min_hamali = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Min Hamali")
    fov_min = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Min FOV")
    fov_insured_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="FOV Insured %")
    fov_uninsured_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="FOV Uninsured %")
    damage_claim_percent = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0.0000'), verbose_name="Damage Claim %")



    # The raw JSON - source of truth for engine, updated by fields below
    legacy_rate_card_backup = models.JSONField(help_text="Backup of legacy JSON logic", blank=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'couriers'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Removed sync logic - data source of truth is now the DB tables
        super().save(*args, **kwargs)
    
    def get_rate_dict(self):
        """
        Reconstructs the dictionary expected by the engine from DB columns and CourierZoneRate.
        """
        # Fetch Zone Rates efficiently
        zone_rates = self.zone_rates.all()
        fwd_rates = {}
        add_rates = {}
        
        for zr in zone_rates:
            if zr.rate_type == CourierZoneRate.RateType.FORWARD:
                fwd_rates[zr.zone_code] = zr.rate
            else:
                add_rates[zr.zone_code] = zr.rate

        data = {
            "carrier_name": self.name,
            "type": self.carrier_type,
            "mode": self.carrier_mode,
            "active": self.is_active,
            "min_weight": self.min_weight,
            "max_weight": self.max_weight,
            "volumetric_divisor": self.volumetric_divisor,
            "logic": "Zonal", # Default
            "required_source_city": self.required_source_city or self.legacy_rate_card_backup.get("required_source_city"), 
            "hub_pincode_prefixes": self.hub_pincode_prefixes,
            "fuel_config": {
                "is_dynamic": self.fuel_is_dynamic,
                "base_diesel_price": self.fuel_base_price,
                "diesel_ratio": self.fuel_ratio,
                "flat_percent": self.fuel_surcharge_percent
            },
            "fixed_fees": {
                "docket_fee": self.docket_fee,
                "eway_bill_fee": self.eway_bill_fee,
                "cod_fixed": self.cod_charge_fixed,
                "appointment_delivery": self.appointment_delivery_fee
            },
            "variable_fees": {
                "cod_percent": self.cod_charge_percent,
                "hamali_per_kg": self.hamali_per_kg,
                "min_hamali": self.min_hamali,
                "fov_insured_percent": self.fov_insured_percent,
                "fov_uninsured_percent": self.fov_uninsured_percent,
                "fov_min": self.fov_min,
                "damage_claim_percent": self.damage_claim_percent
            },
            "routing_logic": {
                "is_city_specific": False,
                "zonal_rates": {
                    "forward": fwd_rates,
                    "additional": add_rates
                },
                "city_rates": None,
                "zone_mapping": None,
                "door_delivery_slabs": []
            } 
        }

        # --- FACADE FACELIFT START ---
        # Prioritize normalized tables over legacy columns
        if self.fees:
            data["fixed_fees"]["docket_fee"] = self.fees.docket_fee
            data["fixed_fees"]["eway_bill_fee"] = self.fees.eway_bill_fee
            data["fixed_fees"]["cod_fixed"] = self.fees.cod_fixed
            data["fixed_fees"]["appointment_delivery"] = self.fees.appointment_delivery_fee
            
            data["variable_fees"]["cod_percent"] = self.fees.cod_percent
            data["variable_fees"]["hamali_per_kg"] = self.fees.hamali_per_kg
            data["variable_fees"]["min_hamali"] = self.fees.min_hamali
            data["variable_fees"]["fov_insured_percent"] = self.fees.fov_insured_percent
            data["variable_fees"]["fov_uninsured_percent"] = self.fees.fov_uninsured_percent
            data["variable_fees"]["fov_min"] = self.fees.fov_min
            data["variable_fees"]["damage_claim_percent"] = self.fees.damage_claim_percent

        if self.constraints:
            data["min_weight"] = self.constraints.min_weight
            data["max_weight"] = self.constraints.max_weight
            data["volumetric_divisor"] = self.constraints.volumetric_divisor
            data["required_source_city"] = self.constraints.required_source_city

        if self.fuel_config:
            data["fuel_config"]["is_dynamic"] = self.fuel_config.is_dynamic
            data["fuel_config"]["base_diesel_price"] = self.fuel_config.base_price
            data["fuel_config"]["diesel_ratio"] = self.fuel_config.ratio
            data["fuel_config"]["flat_percent"] = self.fuel_config.surcharge_percent

        if self.routing:
             # Override logic type logic if routing table says so
             # But routing logic also depends on relations (zone_rates, etc) which are not fully moved yet
             # So we trust the legacy self.rate_logic for the IF blocks below, 
             # UNLESS we explicitly update self.rate_logic property.
             
             pass
        # --- FACADE FACELIFT END ---

        # Logic Mapping
        if self.rate_logic == 'City_To_City':
            data['logic'] = 'city_to_city'
            data['routing_logic']['is_city_specific'] = True
            
            # Legacy fields for zones.py logic
            if self.serviceable_pincode_csv:
                data['routing_logic']['pincode_csv'] = self.serviceable_pincode_csv
            if self.hub_city:
                data['routing_logic']['hub_city'] = self.hub_city
            
            # Populate City Rates
            city_rates = {}
            for r in self.city_routes.all():
                city_rates[r.city_name.lower()] = r.rate_per_kg
            data['routing_logic']['city_rates'] = city_rates
            
            # Populate Slabs
            slabs = []
            for s in self.delivery_slabs.all():
                slabs.append({
                    "min": s.min_weight,
                    "max": s.max_weight,
                    "rate": s.rate
                })
            data['routing_logic']['door_delivery_slabs'] = slabs
            
        elif self.rate_logic == 'Zonal_Standard':
            data['logic'] = 'Zonal'
            # Already populated via fwd_rates / add_rates above

        elif self.rate_logic == 'Zonal_Custom':
            data['logic'] = 'Zonal'
            # Zones
            zm = {}
            for z in self.custom_zones.all():
                zm[z.location_name] = z.zone_code
            data['zone_mapping'] = zm 
            
            # Rates
            zr = {}
            for r in self.custom_zone_rates.all():
                if r.from_zone not in zr: zr[r.from_zone] = {}
                zr[r.from_zone][r.to_zone] = r.rate_per_kg
            data['routing_logic']['zonal_rates'] = zr

        elif self.rate_logic == 'Region_CSV':
            data['logic'] = 'pincode_region_csv'
            # Set the type field for zones.py logic detection
            data['routing_logic']['type'] = 'pincode_region_csv'
            # Set csv_file with fallback to BlueDart default
            csv_file = self.serviceable_pincode_csv or "BlueDart_Serviceable Pincodes.csv"
            data['routing_logic']['csv_file'] = csv_file
            # Set forward_rates from CourierZoneRate table
            data['forward_rates'] = fwd_rates
            # Merge legacy backup data (EDL config, variable fees, etc.)
            if self.legacy_rate_card_backup:
                for key in ['edl_config', 'edl_matrix', 'variable_fees', 'fixed_fees']:
                    if key in self.legacy_rate_card_backup:
                        if key == 'variable_fees':
                            # Merge with existing variable_fees
                            data['variable_fees'].update(self.legacy_rate_card_backup[key])
                        elif key == 'fixed_fees':
                            # Merge with existing fixed_fees
                            data['fixed_fees'].update(self.legacy_rate_card_backup[key])
                        else:
                            data[key] = self.legacy_rate_card_backup[key]

        def cast_decimal(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, dict):
                return {k: cast_decimal(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [cast_decimal(v) for v in obj]
            return obj

        return cast_decimal(data)

    def _sync_custom_zones_to_json(self):
        # Deprecated
        pass
        """Sync CustomZone and CustomZoneRate objects to rate_card JSON"""
        zone_mapping = {}
        for zone in self.custom_zones.all():
            zone_mapping[zone.location_name] = zone.zone_code
        
        zonal_rates = {}
        for rate in self.custom_zone_rates.all():
            if rate.from_zone not in zonal_rates:
                zonal_rates[rate.from_zone] = {}
            zonal_rates[rate.from_zone][rate.to_zone] = rate.rate_per_kg
        
        if not self.rate_card.get('routing_logic'):
            self.rate_card['routing_logic'] = {}
        self.rate_card['routing_logic']['is_city_specific'] = False
        self.rate_card['zone_mapping'] = zone_mapping
        self.rate_card['routing_logic']['zonal_rates'] = zonal_rates
        
        # Save without triggering infinite loop
        Courier.objects.filter(pk=self.pk).update(rate_card=self.rate_card)


class CityRoute(models.Model):
    """City-to-City routing rates"""
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='city_routes')
    city_name = models.CharField(max_length=100, verbose_name="City/Destination")
    rate_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Rate (per kg)")
    
    class Meta:
        db_table = 'city_routes'
        unique_together = ['courier', 'city_name']
        ordering = ['city_name']
    
    def __str__(self):
        return f"{self.courier.name} - {self.city_name}"


class DeliverySlab(models.Model):
    """Delivery slabs for City-to-City logic"""
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='delivery_slabs')
    min_weight = models.FloatField(verbose_name="Min Weight")
    max_weight = models.FloatField(verbose_name="Max Weight", null=True, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Flat Rate")
    
    class Meta:
        db_table = 'delivery_slabs'
        ordering = ['min_weight']
    
    def __str__(self):
        return f"{self.courier.name}: {self.min_weight}-{self.max_weight} = {self.rate}"


class CustomZone(models.Model):
    """Custom zone mapping (location to zone code)"""
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='custom_zones')
    location_name = models.CharField(max_length=100, help_text="State/City/Region name")
    zone_code = models.CharField(max_length=20, help_text="Zone code (e.g. CTL, E1, MH1)")
    
    class Meta:
        db_table = 'custom_zones'
        unique_together = ['courier', 'location_name']
        ordering = ['zone_code', 'location_name']
    
    def __str__(self):
        return f"{self.location_name} → {self.zone_code}"


class CustomZoneRate(models.Model):
    """Custom zone matrix rates (from zone to zone)"""
    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='custom_zone_rates')
    from_zone = models.CharField(max_length=20, verbose_name="From Zone")
    to_zone = models.CharField(max_length=20, verbose_name="To Zone")
    rate_per_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Rate (per kg)")
    
    class Meta:
        db_table = 'custom_zone_rates'
        unique_together = ['courier', 'from_zone', 'to_zone']
        ordering = ['from_zone', 'to_zone']
    
    def __str__(self):
        return f"{self.from_zone} → {self.to_zone}: ₹{self.rate_per_kg}"


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    BOOKED = "booked", "Booked / Ready to Ship"
    MANIFESTED = "manifested", "Manifested"
    PICKED_UP = "picked_up", "Picked Up / In Transit"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for Delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled / Unbooked"
    PICKUP_EXCEPTION = "pickup_exception", "Pickup Exception"
    NDR = "ndr", "NDR (Non-Delivery Report)"
    RTO = "rto", "RTO (Return to Origin)"


class PaymentMode(models.TextChoices):
    COD = "cod", "Cash on Delivery"
    PREPAID = "prepaid", "Prepaid"


class Order(models.Model):
    """
    Order model for logistics management.
    Converted from SQLAlchemy to Django ORM.
    """
    # Auto-generated fields
    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)

    # Recipient Details
    recipient_name = models.CharField(max_length=255)
    recipient_contact = models.CharField(max_length=15)  # Mandatory contact number
    recipient_address = models.TextField()
    recipient_pincode = models.IntegerField()
    recipient_city = models.CharField(max_length=100, blank=True, null=True)  # Auto-filled
    recipient_state = models.CharField(max_length=100, blank=True, null=True)  # Auto-filled
    recipient_phone = models.CharField(max_length=15, blank=True, null=True)
    recipient_email = models.EmailField(blank=True, null=True)

    # Sender Details
    sender_pincode = models.IntegerField()
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    sender_address = models.TextField(blank=True, null=True)
    sender_phone = models.CharField(max_length=15, blank=True, null=True)

    # Box Details
    weight = models.FloatField()  # Actual weight in kg
    length = models.FloatField()  # Length in cm (mandatory)
    width = models.FloatField()   # Width in cm (mandatory)
    height = models.FloatField()  # Height in cm (mandatory)
    volumetric_weight = models.FloatField(blank=True, null=True)  # Calculated: (L x W x H) / 5000
    applicable_weight = models.FloatField(blank=True, null=True)  # max(actual_weight, volumetric_weight)

    # Payment
    payment_mode = models.CharField(
        max_length=10,
        choices=PaymentMode.choices,
        default=PaymentMode.PREPAID
    )
    order_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text="Order value for COD"
    )

    # Items Info
    item_type = models.CharField(max_length=100, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    item_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'),
        help_text="Item amount"
    )

    # Order Status & Tracking
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT
    )

    # Shipment Details (filled after carrier selection)
    carrier = models.ForeignKey('Courier', on_delete=models.PROTECT, null=True, blank=True, related_name='orders')
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text="Total shipping cost"
    )
    cost_breakdown = models.JSONField(blank=True, null=True)  # Stores the full breakdown
    awb_number = models.CharField(max_length=100, blank=True, null=True)  # Air Waybill number
    zone_applied = models.CharField(max_length=100, blank=True, null=True)
    mode = models.CharField(max_length=20, blank=True, null=True)  # Surface/Air

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    booked_at = models.DateTimeField(blank=True, null=True)

    # Additional metadata
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.recipient_name}"

    def save(self, *args, **kwargs):
        # Calculate volumetric weight if dimensions are provided
        if self.length and self.width and self.height:
            self.volumetric_weight = (self.length * self.width * self.height) / 5000
            self.applicable_weight = max(self.weight, self.volumetric_weight)
        else:
            self.applicable_weight = self.weight

        super().save(*args, **kwargs)


class FTLOrder(models.Model):
    """
    Full Truck Load (FTL) Order model.
    Different from regular courier orders - uses container-based pricing.
    """
    # Auto-generated fields
    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(max_length=50, unique=True, db_index=True)

    # Contact Details
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)

    # Location Details
    source_city = models.CharField(max_length=100)
    source_address = models.TextField(blank=True, null=True)
    source_pincode = models.IntegerField()
    destination_city = models.CharField(max_length=100)
    destination_address = models.TextField(blank=True, null=True)
    destination_pincode = models.IntegerField()

    # Container Details
    container_type = models.CharField(
        max_length=20,
        choices=[
            ("20FT", "20FT"),
            ("32 FT SXL 7MT", "32 FT SXL 7MT"),
            ("32 FT SXL 9MT", "32 FT SXL 9MT"),
        ]
    )

    # Pricing Details
    base_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Base price before escalation"
    )
    escalation_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="15% of base price"
    )
    price_with_escalation = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Base + escalation"
    )
    gst_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="18% GST on price_with_escalation"
    )
    total_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Final total price"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    booked_at = models.DateTimeField(blank=True, null=True)

    # Additional metadata
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ftl_orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.name}"


class SystemConfig(models.Model):
    """
    Singleton-like model to store global system configuration.
    Replaces settings.json and hardcoded values.
    """
    # Fuel Config
    diesel_price_current = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('90.00'),
        verbose_name="Current Diesel Price", help_text="Used for dynamic fuel surcharge calculation"
    )
    base_diesel_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('90.00'),
        verbose_name="Base Diesel Price", help_text="Benchmark price for fuel surcharge"
    )
    fuel_surcharge_ratio = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('0.625'),
        verbose_name="Fuel Surcharge Ratio", help_text="Ratio for fuel surcharge calculation"
    )

    # Financial Config
    gst_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.18'),
        verbose_name="GST Rate", help_text="18% = 0.18"
    )
    escalation_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.15'),
        verbose_name="Escalation Rate", help_text="Margin/Escalation 15% = 0.15"
    )

    # File/Path Config
    default_servicable_csv = models.CharField(
        max_length=255, default="BlueDart_Servicable Pincodes.csv",
        verbose_name="Default Serviceable CSV", help_text="Filename in config directory"
    )

    class Meta:
        db_table = 'system_config'
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"

    def __str__(self):
        return "Global System Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if not self.pk and SystemConfig.objects.exists():
            # If trying to create a new one, update the existing one instead?
            # Or just block it. For now, let's just save as is or update the first one.
            # A cleaner way for simple singleton is just strict check, but let's be lenient.
            return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    @classmethod

    def get_solo(cls):
        """Get the configuration object, creating if it doesn't exist."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class CourierZoneRate(models.Model):
    """
    Normalized model to store Forward and Additional rates per zone.
    Replaces fwd_z_a, add_z_b, etc. columns on Courier model.
    """
    class RateType(models.TextChoices):
        FORWARD = "forward", "Forward Rate"
        ADDITIONAL = "additional", "Additional Rate"

    courier = models.ForeignKey(Courier, on_delete=models.CASCADE, related_name='zone_rates')
    zone_code = models.CharField(max_length=20, help_text="Zone Code (e.g. z_a, z_b, north, south)")
    rate_type = models.CharField(max_length=20, choices=RateType.choices, default=RateType.FORWARD)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Rate (₹)")
    
    class Meta:
        db_table = 'courier_zone_rates'
        unique_together = ['courier', 'zone_code', 'rate_type']
        ordering = ['zone_code', 'rate_type']

    def __str__(self):
        return f"{self.courier.name} - {self.zone_code} ({self.rate_type}): ₹{self.rate}"
