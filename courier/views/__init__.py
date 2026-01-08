"""
Courier Views Package.
Re-exports all view functions and classes for URL routing.
"""

# Public API endpoints
from .public import (
    health_check,
    root_redirect,
    dashboard_view,
    rate_calculator_view,
    compare_rates,
    lookup_pincode,
)

# Order management
from .orders import OrderViewSet

# Admin endpoints
from .admin import (
    get_all_rates,
    update_rates,
    add_carrier,
    toggle_carrier_active,
    delete_carrier,
    update_carrier,
    admin_orders_list,
    admin_ftl_orders_list,
    admin_dashboard_stats,
)

# FTL endpoints
from .ftl import (
    get_ftl_routes,
    calculate_ftl_rate,
    FTLOrderViewSet,
)

# Utility functions (for direct access if needed)
from .base import (
    load_rates,
    load_ftl_rates,
    invalidate_rates_cache,
    generate_order_number,
    generate_ftl_order_number,
    generate_ftl_order_number,
    calculate_ftl_price,
)

# Invoice generation
from .invoices import generate_invoice_pdf

__all__ = [
    # Public
    'health_check',
    'root_redirect',
    'dashboard_view',
    'rate_calculator_view',
    'compare_rates',
    'lookup_pincode',
    # Orders
    'OrderViewSet',
    # Admin
    'get_all_rates',
    'update_rates',
    'add_carrier',
    'toggle_carrier_active',
    'delete_carrier',
    'update_carrier',
    'admin_orders_list',
    'admin_ftl_orders_list',
    'admin_dashboard_stats',
    # FTL
    'get_ftl_routes',
    'calculate_ftl_rate',
    'FTLOrderViewSet',
    # Utilities
    'load_rates',
    'load_ftl_rates',
    'invalidate_rates_cache',
    'generate_order_number',
    'generate_ftl_order_number',
    'generate_ftl_order_number',
    'calculate_ftl_price',
    # Invoices
    'generate_invoice_pdf',
]
