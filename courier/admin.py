from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Order, OrderStatus, PaymentMode, FTLOrder, Courier, CourierZoneRate, CityRoute, CustomZone, CustomZoneRate, DeliverySlab, SystemConfig
from .models_refactored import FeeStructure, ServiceConstraints, FuelConfiguration, RoutingLogic

class FeeStructureInline(admin.StackedInline):
    model = FeeStructure
    verbose_name = "Fee Structure Configuration"
    can_delete = False

class ServiceConstraintsInline(admin.StackedInline):
    model = ServiceConstraints
    verbose_name = "Service Constraints"
    can_delete = False

class FuelConfigurationInline(admin.StackedInline):
    model = FuelConfiguration
    verbose_name = "Fuel Surcharge Configuration"
    can_delete = False

class RoutingLogicInline(admin.StackedInline):
    model = RoutingLogic
    verbose_name = "Routing Logic Config"
    can_delete = False

class CourierZoneRateInline(admin.TabularInline):
    model = CourierZoneRate
    extra = 0
    fields = ['zone_code', 'rate_type', 'rate']
    verbose_name = "Standard Zone Rate"
    verbose_name_plural = "Standard Zone Rates (Zones A-F)"
    ordering = ['zone_code', 'rate_type']


class CityRouteInline(admin.TabularInline):
    model = CityRoute
    extra = 1
    fields = ['city_name', 'rate_per_kg']
    verbose_name = "City Route"
    verbose_name_plural = "City Routes (add all destination cities and their rates)"


class CustomZoneInline(admin.TabularInline):
    model = CustomZone
    extra = 1
    fields = ['location_name', 'zone_code']
    verbose_name = "Zone Mapping"
    verbose_name_plural = "Zone Mappings (map locations to zone codes)"


class CustomZoneRateInline(admin.TabularInline):
    model = CustomZoneRate
    extra = 1
    fields = ['from_zone', 'to_zone', 'rate_per_kg']
    verbose_name = "Zone Rate"
    verbose_name_plural = "Zone Matrix (rates between zone pairs)"


class DeliverySlabInline(admin.TabularInline):
    model = DeliverySlab
    extra = 1
    fields = ['min_weight', 'max_weight', 'rate']
    verbose_name = "Delivery Slab"
    verbose_name_plural = "Delivery Slabs (City-to-City Weight Brackets)"


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    # Only show main fields, hide legacy big list
    list_display = ['name', 'is_active', 'updated_at']
    list_filter = ['is_active']
    search_fields = ['name']
    
    inlines = [
        FeeStructureInline,
        ServiceConstraintsInline,
        FuelConfigurationInline,
        RoutingLogicInline,
        # Conditional inlines are tricky if not dynamic, but we can just add them all 
        # or keep the get_inlines logic from before but appended
    ]

    def get_inlines(self, request, obj=None):
        """Show different inlines based on routing logic"""
        default_inlines = [
            FeeStructureInline,
            ServiceConstraintsInline,
            FuelConfigurationInline,
            RoutingLogicInline
        ]
        
        # We need to check obj.routing_config.logic_type if moved, or obj.rate_logic fallback using property
        # For now assume legacy column usage for logic checking
        if obj and obj.rate_logic == 'City_To_City':
            return default_inlines + [CityRouteInline, DeliverySlabInline]
        elif obj and obj.rate_logic == 'Zonal_Custom':
            return default_inlines + [CustomZoneInline, CustomZoneRateInline]
        elif obj and obj.rate_logic == 'Zonal_Standard':
            return default_inlines + [CourierZoneRateInline]
        return default_inlines
    
    # We remove the fieldsets that referenced legacy fields because they will error if fields are deleted
    # Instead rely on Inlines
