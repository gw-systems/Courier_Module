from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Order, OrderStatus, PaymentMode, FTLOrder, Courier, CityRoute, CustomZone, CustomZoneRate


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


@admin.register(Courier)
class CourierAdmin(admin.ModelAdmin):
    list_display = ['name', 'carrier_type', 'carrier_mode', 'rate_logic', 'is_active', 'updated_at']
    list_filter = ['is_active', 'carrier_type', 'carrier_mode', 'rate_logic']
    search_fields = ['name']
    
    def get_inlines(self, request, obj=None):
        """Show different inlines based on routing logic"""
        if obj and obj.rate_logic == 'City_To_City':
            return [CityRouteInline]
        elif obj and obj.rate_logic == 'Zonal_Custom':
            return [CustomZoneInline, CustomZoneRateInline]
        return []
    
    def get_fieldsets(self, request, obj=None):
        """Show different fieldsets based on routing logic"""
        basic_fieldsets = [
            ('Basic Configuration', {
                'fields': (
                    ('name', 'is_active'),
                    ('carrier_type', 'carrier_mode', 'rate_logic')
                ),
                'description': '<b>Step 1:</b> Select the routing logic type and configure basic settings.'
            }),
            ('Weight & Dimensions', {
                'fields': (
                    ('min_weight', 'max_weight'),
                    'volumetric_divisor',
                )
            }),
            ('Surcharges & Fees', {
                'fields': (
                    ('cod_charge_fixed', 'cod_charge_percent'),
                    'fuel_surcharge_percent'
                )
            }),
        ]
        
        # Add routing-specific fieldsets
        if obj and obj.rate_logic == 'Zonal_Standard':
            basic_fieldsets.extend([
                ('Forward Rates (Per Zone)', {
                    'fields': (
                        ('fwd_z_a', 'fwd_z_b', 'fwd_z_c'),
                        ('fwd_z_d', 'fwd_z_e', 'fwd_z_f')
                    ),
                    'description': '<b>Step 2:</b> Base delivery rates for each standard zone (A-F).'
                }),
                ('Additional Rates (Per Zone)', {
                    'fields': (
                        ('add_z_a', 'add_z_b', 'add_z_c'),
                        ('add_z_d', 'add_z_e', 'add_z_f')
                    ),
                    'description': 'Rates for every additional weight slab (e.g. per 0.5kg or 1kg).'
                }),
            ])
        elif obj and obj.rate_logic == 'City_To_City':
            basic_fieldsets.append(
                ('City Routes Configuration', {
                    'fields': (),
                    'description': '<b>Step 2:</b> Scroll down to add city routes using the form below. Add each destination city and its rate.'
                })
            )
        elif obj and obj.rate_logic == 'Zonal_Custom':
            basic_fieldsets.append(
                ('Custom Zone Configuration', {
                    'fields': (),
                    'description': '<b>Step 2:</b> Scroll down to define zone mappings and zone matrix rates using the forms below.'
                })
            )
        
        # Advanced section (always present)
        basic_fieldsets.append(
            ('Advanced Configuration', {
                'classes': ('collapse',),
                'fields': ('rate_card',),
                'description': '<b>WARNING:</b> This JSON is automatically generated from the fields/tables above. Manual edits may be overwritten.'
            })
        )
        

        return basic_fieldsets

    def save_related(self, request, form, formsets, change):
        """
        Override to ensure JSON sync happens AFTER inlines are saved.
        Standard save_model happens BEFORE inlines, so new inlines aren't in the DB yet.
        """
        super().save_related(request, form, formsets, change)
        
        # Re-sync JSON if applicable
        obj = form.instance
        if obj.pk:
            if obj.rate_logic == 'City_To_City':
                obj._sync_city_routes_to_json()
            elif obj.rate_logic == 'Zonal_Custom':
                obj._sync_custom_zones_to_json()



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Django Admin configuration for Order model"""

    list_display = [
        'order_number', 'recipient_name', 'recipient_contact',
        'status_badge', 'selected_carrier', 'mode', 'total_cost_display', 'created_at'
    ]

    list_filter = [
        'status', 'payment_mode', 'selected_carrier',
        'mode', 'created_at', 'booked_at'
    ]

    search_fields = [
        'order_number', 'recipient_name', 'recipient_contact',
        'recipient_email', 'awb_number', 'sender_name'
    ]

    readonly_fields = [
        'order_number', 'volumetric_weight', 'applicable_weight',
        'created_at', 'updated_at', 'booked_at', 'cost_breakdown'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'notes')
        }),
        ('Recipient Details', {
            'fields': (
                'recipient_name', 'recipient_contact', 'recipient_email',
                'recipient_address', 'recipient_pincode', 'recipient_city',
                'recipient_state', 'recipient_phone'
            )
        }),
        ('Sender Details', {
            'fields': (
                'sender_name', 'sender_pincode', 'sender_address', 'sender_phone'
            )
        }),
        ('Package Details', {
            'fields': (
                'weight', 'length', 'width', 'height',
                'volumetric_weight', 'applicable_weight'
            )
        }),
        ('Item Details', {
            'fields': (
                'item_type', 'sku', 'quantity', 'item_amount'
            )
        }),
        ('Payment', {
            'fields': ('payment_mode', 'order_value')
        }),
        ('Shipping Details', {
            'fields': (
                'selected_carrier', 'mode', 'zone_applied',
                'total_cost', 'cost_breakdown', 'awb_number'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'booked_at'),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    actions = ['mark_as_booked', 'mark_as_cancelled']

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'draft': '#6c757d',
            'booked': '#007bff',
            'manifested': '#17a2b8',
            'picked_up': '#ffc107',
            'out_for_delivery': '#fd7e14',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
            'pickup_exception': '#e83e8c',
            'ndr': '#6f42c1',
            'rto': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def total_cost_display(self, obj):
        """Display cost with currency formatting"""
        if obj.total_cost:
            formatted = '₹{:,.2f}'.format(float(obj.total_cost))
            return format_html('{}', formatted)
        return '-'
    total_cost_display.short_description = 'Total Cost'
    total_cost_display.admin_order_field = 'total_cost'

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of DRAFT orders
        if obj and obj.status != OrderStatus.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    @admin.action(description='Mark selected orders as BOOKED')
    def mark_as_booked(self, request, queryset):
        updated = queryset.filter(status=OrderStatus.DRAFT).update(status=OrderStatus.BOOKED)
        self.message_user(request, f'{updated} order(s) marked as booked.')

    @admin.action(description='Mark selected orders as PICKED UP')
    def mark_as_picked_up(self, request, queryset):
        updated = queryset.filter(status__in=[OrderStatus.BOOKED, OrderStatus.MANIFESTED]).update(status=OrderStatus.PICKED_UP)
        self.message_user(request, f'{updated} order(s) marked as picked up.')

    @admin.action(description='Mark selected orders as IN TRANSIT')
    def mark_as_in_transit(self, request, queryset):
        # Note: IN TRANSIT is often same as PICKED_UP in this system, or implies movement
        # Assuming we treat 'out_for_delivery' or custom status? 
        # The choices has: PICKED_UP (Picked Up / In Transit).
        # So "In Transit" effectively means PICKED_UP here if there's no strict distinction.
        # But wait, user asked for "in transit". The text choice says "Picked Up / In Transit".
        # Let's map it to PICKED_UP for now or allow updating from other states.
        updated = queryset.exclude(status__in=[OrderStatus.DRAFT, OrderStatus.CANCELLED, OrderStatus.DELIVERED]).update(status=OrderStatus.PICKED_UP)
        self.message_user(request, f'{updated} order(s) marked as in transit.')

    @admin.action(description='Mark selected orders as DELIVERED')
    def mark_as_delivered(self, request, queryset):
        updated = queryset.exclude(status__in=[OrderStatus.DRAFT, OrderStatus.CANCELLED]).update(status=OrderStatus.DELIVERED)
        self.message_user(request, f'{updated} order(s) marked as delivered.')

    @admin.action(description='Mark selected orders as CANCELLED')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.exclude(
            status__in=[OrderStatus.DELIVERED, OrderStatus.PICKED_UP]
        ).update(status=OrderStatus.CANCELLED)
        self.message_user(request, f'{updated} order(s) marked as cancelled.')


@admin.register(FTLOrder)
class FTLOrderAdmin(admin.ModelAdmin):
    """Django Admin configuration for FTL Order model"""

    list_display = [
        'order_number', 'name', 'phone', 'source_city', 'destination_city',
        'container_type', 'status_badge', 'total_price_display', 'created_at'
    ]

    list_filter = [
        'status', 'container_type', 'source_city', 'destination_city',
        'created_at', 'booked_at'
    ]

    search_fields = [
        'order_number', 'name', 'phone', 'email', 'source_city', 'destination_city'
    ]

    readonly_fields = [
        'order_number', 'base_price', 'escalation_amount',
        'price_with_escalation', 'gst_amount', 'total_price',
        'created_at', 'updated_at', 'booked_at'
    ]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'notes')
        }),
        ('Customer Details', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Route Details', {
            'fields': (
                ('source_city', 'source_pincode'),
                'source_address',
                ('destination_city', 'destination_pincode')
            )
        }),
        ('Container & Pricing', {
            'fields': (
                'container_type',
                ('base_price', 'escalation_amount'),
                ('price_with_escalation', 'gst_amount'),
                'total_price'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'booked_at'),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50
    actions = [
        'mark_as_booked', 'mark_as_picked_up', 'mark_as_delivered', 'mark_as_cancelled'
    ]

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'draft': '#6c757d',
            'booked': '#007bff',
            'manifested': '#17a2b8',
            'picked_up': '#ffc107',
            'out_for_delivery': '#fd7e14',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 8px; border-radius:3px; font-size:11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def total_price_display(self, obj):
        """Display price with currency formatting"""
        if obj.total_price:
            formatted = '₹{:,.2f}'.format(float(obj.total_price))
            return format_html('{}', formatted)
        return '-'
    total_price_display.short_description = 'Total Price'
    total_price_display.admin_order_field = 'total_price'

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of DRAFT or CANCELLED orders
        if obj and obj.status not in [OrderStatus.DRAFT, OrderStatus.CANCELLED]:
            return False
        return super().has_delete_permission(request, obj)

    @admin.action(description='Mark selected orders as BOOKED')
    def mark_as_booked(self, request, queryset):
        updated = queryset.filter(status=OrderStatus.DRAFT).update(status=OrderStatus.BOOKED)
        self.message_user(request, f'{updated} FTL order(s) marked as booked.')

    @admin.action(description='Mark selected orders as IN TRANSIT')
    def mark_as_picked_up(self, request, queryset):
        updated = queryset.filter(status=OrderStatus.BOOKED).update(status=OrderStatus.PICKED_UP)
        self.message_user(request, f'{updated} FTL order(s) marked as in transit.')

    @admin.action(description='Mark selected orders as DELIVERED')
    def mark_as_delivered(self, request, queryset):
        updated = queryset.exclude(status__in=[OrderStatus.DRAFT, OrderStatus.CANCELLED]).update(status=OrderStatus.DELIVERED)
        self.message_user(request, f'{updated} FTL order(s) marked as delivered.')

    @admin.action(description='Mark selected orders as CANCELLED')
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.filter(status=OrderStatus.DRAFT).update(status=OrderStatus.CANCELLED)
        self.message_user(request, f'{updated} FTL order(s) marked as cancelled.')


# Customize admin site header
admin.site.site_header = 'LogiRate Admin'
admin.site.site_title = 'LogiRate Admin Portal'
admin.site.index_title = 'Order & Carrier Management'
