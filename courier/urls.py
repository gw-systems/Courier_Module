"""
URL configuration for courier app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'courier'

# Create router for ViewSets
router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'ftl-orders', views.FTLOrderViewSet, basename='ftl-order')

urlpatterns = [
    # Public endpoints
    path('health', views.health_check, name='health'),
    path('compare-rates', views.compare_rates, name='compare-rates'),
    path('pincode/<int:pincode>/', views.lookup_pincode, name='lookup-pincode'),
    
    # FTL endpoints
    path('ftl/routes', views.get_ftl_routes, name='get-ftl-routes'),
    path('ftl/calculate-rate', views.calculate_ftl_rate, name='calculate-ftl-rate'),

    # Order management (includes ViewSet routes)
    # IMPORTANT: Router must come BEFORE manual paths with <pk> to prevent action names being captured
    path('', include(router.urls)),
    path('orders/<str:pk>/invoice/', views.generate_invoice_pdf, name='generate-invoice'),

    # Admin endpoints
    path('admin/rates', views.get_all_rates, name='admin-get-rates'),
    path('admin/rates/update', views.update_rates, name='admin-update-rates'),
    path('admin/rates/add', views.add_carrier, name='admin-add-carrier'),
    path('admin/carriers/<str:carrier_name>/toggle-active', views.toggle_carrier_active, name='admin-toggle-carrier'),
    path('admin/carriers/<str:carrier_name>', views.delete_carrier, name='admin-delete-carrier'),
    path('admin/carriers/<str:carrier_name>/update', views.update_carrier, name='admin-update-carrier'),
    path('admin/orders', views.admin_orders_list, name='admin-orders-list'),
    path('admin/ftl-orders', views.admin_ftl_orders_list, name='admin-ftl-orders-list'),
    path('admin/dashboard', views.admin_dashboard_stats, name='admin-dashboard-stats'),
]
