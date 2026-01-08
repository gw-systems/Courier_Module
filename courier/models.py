from django.db import models
from django.utils import timezone
from django.utils import timezone
from decimal import Decimal
from .models_refactored import FeeStructure, ServiceConstraints, FuelConfiguration, RoutingLogic


class CourierManager(models.Manager):
    def create(self, **kwargs):
        # Separate legacy fields from main fields
        fees_fields = {
            'docket_fee': 'docket_fee', 
            'eway_bill_fee': 'eway_bill_fee', 
            'appointment_delivery_fee': 'appointment_delivery_fee', 
            'cod_charge_fixed': 'cod_fixed', 
            'cod_charge_percent': 'cod_percent', 
            'hamali_per_kg': 'hamali_per_kg', 
            'min_hamali': 'min_hamali', 
            'fov_min': 'fov_min', 
            'fov_insured_percent': 'fov_insured_percent', 
            'fov_uninsured_percent': 'fov_uninsured_percent', 
            'damage_claim_percent': 'damage_claim_percent'
        }
        constraints_fields = ['min_weight', 'max_weight', 'volumetric_divisor', 'required_source_city']
        fuel_fields = {'fuel_is_dynamic': 'is_dynamic', 'fuel_base_price': 'base_price', 'fuel_ratio': 'ratio', 'fuel_surcharge_percent': 'surcharge_percent'}
        routing_fields = {'rate_logic': 'logic_type', 'serviceable_pincode_csv': 'serviceable_pincode_csv', 'hub_city': 'hub_city', 'hub_pincode_prefixes': 'hub_pincode_prefixes'}
        
        fees_data = {model_k: kwargs.pop(legacy_k) for legacy_k, model_k in fees_fields.items() if legacy_k in kwargs}
        constraints_data = {k: kwargs.pop(k) for k in constraints_fields if k in kwargs}
        fuel_data = {model_k: kwargs.pop(legacy_k) for legacy_k, model_k in fuel_fields.items() if legacy_k in kwargs}
        routing_data = {model_k: kwargs.pop(legacy_k) for legacy_k, model_k in routing_fields.items() if legacy_k in kwargs}
        
        # Create Courier
        obj = super().create(**kwargs)
        
        # Create related components
        if fees_data or True: # always create to ensure structure exists? No, only if data. Or strict defaults.
            # Using defaults from model definition if not provided
            FeeStructure.objects.create(courier_link=obj, **fees_data)
        
        if constraints_data or True:
            ServiceConstraints.objects.create(courier_link=obj, **constraints_data)
            
        if fuel_data or True:
            FuelConfiguration.objects.create(courier_link=obj, **fuel_data)
            
        if routing_data or True:
            RoutingLogic.objects.create(courier_link=obj, **routing_data)
            
        return obj


class Courier(models.Model):
    """
    Courier model to store rate cards and configuration.
    Replaces master_card.json.
    """
    objects = CourierManager()
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Carrier Name")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    # Friendly Configuration Fields
    carrier_type = models.CharField(max_length=20, default="Courier", choices=[("Courier","Courier"),("PTL","PTL")])
    carrier_mode = models.CharField(max_length=20, default="Surface", choices=[("Surface","Surface"),("Air","Air")])
    
    # --- LEGACY PROPERTIES (FACADE) ---

    def _get_fees(self):
        if not hasattr(self, 'fees_config'):
             # If accessed before save/create, this fails. 
             # But for existing objects it should work.
             return None
        return self.fees_config

    # docket_fee
    @property
    def docket_fee(self):
        return self.fees_config.docket_fee if self._get_fees() else Decimal('0.00')
    @docket_fee.setter
    def docket_fee(self, value):
        if self._get_fees(): self.fees_config.docket_fee = value; self.fees_config.save()

    # eway_bill_fee
    @property
    def eway_bill_fee(self):
        return self.fees_config.eway_bill_fee if self._get_fees() else Decimal('0.00')
    @eway_bill_fee.setter
    def eway_bill_fee(self, value):
        if self._get_fees(): self.fees_config.eway_bill_fee = value; self.fees_config.save()
    
    # ... (Implementing key properties for completeness)
    
    # min_weight
    @property
    def min_weight(self):
        return self.constraints_config.min_weight if hasattr(self, 'constraints_config') else 0.5
    @min_weight.setter
    def min_weight(self, value):
        if hasattr(self, 'constraints_config'): self.constraints_config.min_weight = value; self.constraints_config.save()

    # max_weight
    @property
    def max_weight(self):
        return self.constraints_config.max_weight if hasattr(self, 'constraints_config') else 99999.0
    @max_weight.setter
    def max_weight(self, value):
        if hasattr(self, 'constraints_config'): self.constraints_config.max_weight = value; self.constraints_config.save()

    # rate_logic (Mapped to logic_type)
    @property
    def rate_logic(self):
        return self.routing_config.logic_type if hasattr(self, 'routing_config') else "Zonal_Standard"
    @rate_logic.setter
    def rate_logic(self, value):
        if hasattr(self, 'routing_config'): self.routing_config.logic_type = value; self.routing_config.save()

    # --- Fuel Properties ---
    @property
    def fuel_is_dynamic(self):
        return self.fuel_config_obj.is_dynamic if hasattr(self, 'fuel_config_obj') else False
    @fuel_is_dynamic.setter
    def fuel_is_dynamic(self, value):
        if hasattr(self, 'fuel_config_obj'): self.fuel_config_obj.is_dynamic = value; self.fuel_config_obj.save()

    @property
    def fuel_base_price(self):
        return self.fuel_config_obj.base_price if hasattr(self, 'fuel_config_obj') else Decimal('0.00')
    @fuel_base_price.setter
    def fuel_base_price(self, value):
        if hasattr(self, 'fuel_config_obj'): self.fuel_config_obj.base_price = value; self.fuel_config_obj.save()

    @property
    def fuel_ratio(self):
        return self.fuel_config_obj.ratio if hasattr(self, 'fuel_config_obj') else Decimal('0.0000')
    @fuel_ratio.setter
    def fuel_ratio(self, value):
        if hasattr(self, 'fuel_config_obj'): self.fuel_config_obj.ratio = value; self.fuel_config_obj.save()

    @property
    def fuel_surcharge_percent(self):
        return self.fuel_config_obj.surcharge_percent if hasattr(self, 'fuel_config_obj') else Decimal('0.0000')
    @fuel_surcharge_percent.setter
    def fuel_surcharge_percent(self, value):
        if hasattr(self, 'fuel_config_obj'): self.fuel_config_obj.surcharge_percent = value; self.fuel_config_obj.save()

    # --- Other Fees Properties (Partial List for brevity, assuming standard usage covers them) ---
    @property
    def cod_charge_fixed(self): return self.fees_config.cod_fixed if self._get_fees() else Decimal('0.00')
    @cod_charge_fixed.setter
    def cod_charge_fixed(self, v): 
        if self._get_fees(): self.fees_config.cod_fixed = v; self.fees_config.save()

    @property
    def cod_charge_percent(self): return self.fees_config.cod_percent if self._get_fees() else Decimal('0.0000')
    @cod_charge_percent.setter
    def cod_charge_percent(self, v): 
        if self._get_fees(): self.fees_config.cod_percent = v; self.fees_config.save()
    
    @property
    def hamali_per_kg(self): return self.fees_config.hamali_per_kg if self._get_fees() else Decimal('0.00')
    @hamali_per_kg.setter
    def hamali_per_kg(self, v): 
        if self._get_fees(): self.fees_config.hamali_per_kg = v; self.fees_config.save()

    @property
    def min_hamali(self): return self.fees_config.min_hamali if self._get_fees() else Decimal('0.00')
    @min_hamali.setter
    def min_hamali(self, v): 
        if self._get_fees(): self.fees_config.min_hamali = v; self.fees_config.save()
        
    @property
    def appointment_delivery_fee(self): return self.fees_config.appointment_delivery_fee if self._get_fees() else Decimal('0.00')
    @appointment_delivery_fee.setter
    def appointment_delivery_fee(self, v): 
        if self._get_fees(): self.fees_config.appointment_delivery_fee = v; self.fees_config.save()

    @property
    def fov_min(self): return self.fees_config.fov_min if self._get_fees() else Decimal('0.00')
    @fov_min.setter
    def fov_min(self, v): 
        if self._get_fees(): self.fees_config.fov_min = v; self.fees_config.save()

    @property
    def fov_insured_percent(self): return self.fees_config.fov_insured_percent if self._get_fees() else Decimal('0.0000')
    @fov_insured_percent.setter
    def fov_insured_percent(self, v): 
        if self._get_fees(): self.fees_config.fov_insured_percent = v; self.fees_config.save()

    @property
    def fov_uninsured_percent(self): return self.fees_config.fov_uninsured_percent if self._get_fees() else Decimal('0.0000')
    @fov_uninsured_percent.setter
    def fov_uninsured_percent(self, v): 
        if self._get_fees(): self.fees_config.fov_uninsured_percent = v; self.fees_config.save()

    @property
    def damage_claim_percent(self): return self.fees_config.damage_claim_percent if self._get_fees() else Decimal('0.0000')
    @damage_claim_percent.setter
    def damage_claim_percent(self, v): 
        if self._get_fees(): self.fees_config.damage_claim_percent = v; self.fees_config.save()

    # --- Routing Config Properties ---
    @property
    def serviceable_pincode_csv(self): return self.routing_config.serviceable_pincode_csv if hasattr(self, 'routing_config') else None
    @serviceable_pincode_csv.setter
    def serviceable_pincode_csv(self, v): 
        if hasattr(self, 'routing_config'): self.routing_config.serviceable_pincode_csv = v; self.routing_config.save()

    @property
    def hub_city(self): return self.routing_config.hub_city if hasattr(self, 'routing_config') else None
    @hub_city.setter
    def hub_city(self, v): 
        if hasattr(self, 'routing_config'): self.routing_config.hub_city = v; self.routing_config.save()

    @property
    def hub_pincode_prefixes(self): return self.routing_config.hub_pincode_prefixes if hasattr(self, 'routing_config') else None
    @hub_pincode_prefixes.setter
    def hub_pincode_prefixes(self, v): 
        if hasattr(self, 'routing_config'): self.routing_config.hub_pincode_prefixes = v; self.routing_config.save()
        
    @property
    def required_source_city(self): return self.constraints_config.required_source_city if hasattr(self, 'constraints_config') else None
    @required_source_city.setter
    def required_source_city(self, v):
        if hasattr(self, 'constraints_config'): self.constraints_config.required_source_city = v; self.constraints_config.save()

    @property
    def volumetric_divisor(self): return self.constraints_config.volumetric_divisor if hasattr(self, 'constraints_config') else 5000
    @volumetric_divisor.setter
    def volumetric_divisor(self, v):
        if hasattr(self, 'constraints_config'): self.constraints_config.volumetric_divisor = v; self.constraints_config.save()




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
        fees = getattr(self, 'fees_config', None)
        if fees:
            data["fixed_fees"]["docket_fee"] = fees.docket_fee
            data["fixed_fees"]["eway_bill_fee"] = fees.eway_bill_fee
            data["fixed_fees"]["cod_fixed"] = fees.cod_fixed
            data["fixed_fees"]["appointment_delivery"] = fees.appointment_delivery_fee
            
            data["variable_fees"]["cod_percent"] = fees.cod_percent
            data["variable_fees"]["hamali_per_kg"] = fees.hamali_per_kg
            data["variable_fees"]["min_hamali"] = fees.min_hamali
            data["variable_fees"]["fov_insured_percent"] = fees.fov_insured_percent
            data["variable_fees"]["fov_uninsured_percent"] = fees.fov_uninsured_percent
            data["variable_fees"]["fov_min"] = fees.fov_min
            data["variable_fees"]["damage_claim_percent"] = fees.damage_claim_percent

        constraints = getattr(self, 'constraints_config', None)
        if constraints:
            data["min_weight"] = constraints.min_weight
            data["max_weight"] = constraints.max_weight
            data["volumetric_divisor"] = constraints.volumetric_divisor
            data["required_source_city"] = constraints.required_source_city

        fuel = getattr(self, 'fuel_config_obj', None)
        if fuel:
            data["fuel_config"]["is_dynamic"] = fuel.is_dynamic
            data["fuel_config"]["base_diesel_price"] = fuel.base_price
            data["fuel_config"]["diesel_ratio"] = fuel.ratio
            data["fuel_config"]["flat_percent"] = fuel.surcharge_percent

        routing = getattr(self, 'routing_config', None)
        if routing:
             legacy_logic_map = {
                 "City_To_City": "city_to_city",
                 "Zonal_Standard": "Zonal",
                 "Zonal_Custom": "Zonal",
                 "Region_CSV": "pincode_region_csv"
             }
             data['logic'] = legacy_logic_map.get(routing.logic_type, 'Zonal')
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

        # --- LEGACY BACKUP MERGE (Global) ---
        # Merge legacy backup data (EDL config, variable fees, etc.) for ALL logic types
        # This allows injecting custom fields like 'owners_risk' that aren't in the normalized DB yet.
        if self.legacy_rate_card_backup:
            for key in ['edl_config', 'edl_matrix', 'variable_fees', 'fixed_fees']:
                if key in self.legacy_rate_card_backup:
                    if key == 'variable_fees':
                        # Merge with existing variable_fees
                        if 'variable_fees' not in data: data['variable_fees'] = {}
                        data['variable_fees'].update(self.legacy_rate_card_backup[key])
                    elif key == 'fixed_fees':
                        # Merge with existing fixed_fees
                        if 'fixed_fees' not in data: data['fixed_fees'] = {}
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
