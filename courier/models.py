from django.db import models
from django.utils import timezone
from decimal import Decimal


class Courier(models.Model):
    """
    Courier model to store rate cards and configuration.
    Replaces master_card.json.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Carrier Name")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    # Friendly Configuration Fields
    carrier_type = models.CharField(max_length=20, default="Courier", choices=[("Courier","Courier"),("PTL","PTL")])
    carrier_mode = models.CharField(max_length=20, default="Surface", choices=[("Surface","Surface"),("Air","Air")])
    rate_logic = models.CharField(
        max_length=20, 
        default="Zonal_Standard", 
        choices=[
            ("Zonal_Standard","Zonal (Standard A-F Zones)"),
            ("Zonal_Custom","Zonal (Custom Zone Matrix)"),
            ("City_To_City","City to City Routes")
        ],
        help_text="Select the routing logic type"
    )
    
    min_weight = models.FloatField(default=0.5, help_text="Min weight in kg")
    max_weight = models.FloatField(default=99999.0, help_text="Max weight in kg")
    volumetric_divisor = models.IntegerField(default=5000, help_text="e.g. 5000 or 4500")
    
    cod_charge_fixed = models.FloatField(default=0.0, verbose_name="COD Fixed Fee")
    cod_charge_percent = models.FloatField(default=0.0, verbose_name="COD % (ratio, e.g. 0.015)")
    fuel_surcharge_percent = models.FloatField(default=0.0, verbose_name="Fuel Surcharge % (ratio)")

    # Forward Rates (Zonal_Standard only)
    fwd_z_a = models.FloatField(default=0.0, verbose_name="Fwd Zone A", blank=True)
    fwd_z_b = models.FloatField(default=0.0, verbose_name="Fwd Zone B", blank=True)
    fwd_z_c = models.FloatField(default=0.0, verbose_name="Fwd Zone C", blank=True)
    fwd_z_d = models.FloatField(default=0.0, verbose_name="Fwd Zone D", blank=True)
    fwd_z_e = models.FloatField(default=0.0, verbose_name="Fwd Zone E", blank=True)
    fwd_z_f = models.FloatField(default=0.0, verbose_name="Fwd Zone F", blank=True)

    # Additional Rates (Zonal_Standard only)
    add_z_a = models.FloatField(default=0.0, verbose_name="Add Zone A", blank=True)
    add_z_b = models.FloatField(default=0.0, verbose_name="Add Zone B", blank=True)
    add_z_c = models.FloatField(default=0.0, verbose_name="Add Zone C", blank=True)
    add_z_d = models.FloatField(default=0.0, verbose_name="Add Zone D", blank=True)
    add_z_e = models.FloatField(default=0.0, verbose_name="Add Zone E", blank=True)
    add_z_f = models.FloatField(default=0.0, verbose_name="Add Zone F", blank=True)

    # The raw JSON - source of truth for engine, updated by fields below
    rate_card = models.JSONField(help_text="Full rate card logic (JSON)", blank=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'couriers'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Ensure rate_card is a dict
        if not self.rate_card or not isinstance(self.rate_card, dict):
            self.rate_card = {}
            
        def set_val(d, keys, val):
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = val

        # Sync Basic Info
        self.rate_card['carrier_name'] = self.name
        self.rate_card['type'] = self.carrier_type
        self.rate_card['mode'] = self.carrier_mode
        self.rate_card['active'] = self.is_active
        self.rate_card['min_weight'] = self.min_weight
        self.rate_card['max_weight'] = self.max_weight
        self.rate_card['volumetric_divisor'] = self.volumetric_divisor
        
        # Sync logic type to JSON format
        if self.rate_logic == 'City_To_City':
            self.rate_card['logic'] = 'city_to_city'
        else:
            self.rate_card['logic'] = 'Zonal'
        
        # Fees & Config
        set_val(self.rate_card, ['fixed_fees', 'cod_fixed'], float(self.cod_charge_fixed))
        set_val(self.rate_card, ['variable_fees', 'cod_percent'], float(self.cod_charge_percent))
        set_val(self.rate_card, ['fuel_config', 'flat_percent'], float(self.fuel_surcharge_percent))
        
        # Routing Logic based on type
        if self.rate_logic == 'Zonal_Standard':
            # Standard A-F Zones
            self.rate_card.setdefault('routing_logic', {})
            self.rate_card['routing_logic']['is_city_specific'] = False
            self.rate_card['routing_logic'].setdefault('zonal_rates', {})
            
            fwd = {
                'z_a': self.fwd_z_a, 'z_b': self.fwd_z_b, 'z_c': self.fwd_z_c,
                'z_d': self.fwd_z_d, 'z_e': self.fwd_z_e, 'z_f': self.fwd_z_f,
            }
            set_val(self.rate_card, ['routing_logic', 'zonal_rates', 'forward'], fwd)
            
            add = {
                'z_a': self.add_z_a, 'z_b': self.add_z_b, 'z_c': self.add_z_c,
                'z_d': self.add_z_d, 'z_e': self.add_z_e, 'z_f': self.add_z_f,
            }
            set_val(self.rate_card, ['routing_logic', 'zonal_rates', 'additional'], add)

        super().save(*args, **kwargs)
        
        # After saving, sync related models to JSON
        if self.pk:
            if self.rate_logic == 'City_To_City':
                self._sync_city_routes_to_json()
            elif self.rate_logic == 'Zonal_Custom':
                self._sync_custom_zones_to_json()
    
    def _sync_city_routes_to_json(self):
        """Sync CityRoute objects to rate_card JSON"""
        city_rates = {}
        for route in self.city_routes.all():
            city_rates[route.city_name.lower()] = route.rate_per_kg
        
        if not self.rate_card.get('routing_logic'):
            self.rate_card['routing_logic'] = {}
        self.rate_card['routing_logic']['is_city_specific'] = True
        self.rate_card['routing_logic']['city_rates'] = city_rates
        self.rate_card['routing_logic']['zonal_rates'] = []
        
        # Save without triggering infinite loop
        Courier.objects.filter(pk=self.pk).update(rate_card=self.rate_card)
    
    def _sync_custom_zones_to_json(self):
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
    rate_per_kg = models.FloatField(verbose_name="Rate (per kg)")
    
    class Meta:
        db_table = 'city_routes'
        unique_together = ['courier', 'city_name']
        ordering = ['city_name']
    
    def __str__(self):
        return f"{self.courier.name} - {self.city_name}"


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
    rate_per_kg = models.FloatField(verbose_name="Rate (per kg)")
    
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
    selected_carrier = models.CharField(max_length=100, blank=True, null=True)
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
            models.Index(fields=['selected_carrier']),
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
    source_address = models.TextField(default='Address not provided')
    source_pincode = models.IntegerField()
    destination_city = models.CharField(max_length=100)
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
