"""
URL configuration for LogiRate API (Courier Module).
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from courier import views

urlpatterns = [
    # Django admin
    path("django-admin/", admin.site.urls),

    # Dashboard (Django template)
    path("", views.rate_calculator_view, name='rate-calculator'),
    path("dashboard/", views.dashboard_view, name='dashboard-explicit'),

    # API endpoints
    path("api/", include(('courier.urls', 'courier'), namespace='courier')),

    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name='schema'),
    path("docs/", SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path("redoc/", SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
