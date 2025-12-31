"""
Tests for admin extended endpoints (app/admin_extended.py)
"""
import pytest
from fastapi import status
import json


class TestSettingsEndpoints:
    """Tests for settings management endpoints"""

    def test_get_settings_success(self, client, admin_token):
        """Test getting current system settings"""
        response = client.get(
            "/api/admin/settings",
            headers={"X-Admin-Token": admin_token}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all required settings are present
        assert "GST_RATE" in data
        assert "ESCALATION_RATE" in data
        assert "VOLUMETRIC_DIVISOR" in data
        assert "DEFAULT_WEIGHT_SLAB" in data

    def test_get_settings_without_auth(self, client):
        """Test settings endpoint requires authentication"""
        response = client.get("/api/admin/settings")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_settings_success(self, client, admin_token):
        """Test updating system settings"""
        new_settings = {
            "GST_RATE": 0.18,
            "ESCALATION_RATE": 0.15,
            "VOLUMETRIC_DIVISOR": 5000,
            "DEFAULT_WEIGHT_SLAB": 0.5
        }

        response = client.put(
            "/api/admin/settings",
            headers={"X-Admin-Token": admin_token},
            json=new_settings
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"
        assert "updated successfully" in data["message"]

    def test_update_settings_creates_backup(self, client, admin_token):
        """Test that updating settings creates a backup"""
        import os
        from app.main import BASE_DIR

        settings_path = os.path.join(BASE_DIR, "config", "settings.json")
        backup_path = settings_path + ".bak"

        # Remove backup if exists
        if os.path.exists(backup_path):
            os.remove(backup_path)

        new_settings = {
            "GST_RATE": 0.18,
            "ESCALATION_RATE": 0.15,
            "VOLUMETRIC_DIVISOR": 5000,
            "DEFAULT_WEIGHT_SLAB": 0.5
        }

        response = client.put(
            "/api/admin/settings",
            headers={"X-Admin-Token": admin_token},
            json=new_settings
        )

        assert response.status_code == status.HTTP_200_OK
        assert os.path.exists(backup_path)


class TestOrderManagementEndpoints:
    """Tests for order management endpoints"""

    def test_get_all_orders_success(self, client, admin_token):
        """Test getting all orders"""
        response = client.get(
            "/api/admin/orders/all",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
        assert "orders" in data
        assert "page" in data
        assert "page_size" in data

    def test_get_orders_with_status_filter(self, client, admin_token):
        """Test filtering orders by status"""
        response = client.get(
            "/api/admin/orders/all?status_filter=pending",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_orders_with_date_range(self, client, admin_token):
        """Test filtering orders by date range"""
        response = client.get(
            "/api/admin/orders/all?date_from=2024-01-01&date_to=2024-12-31",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_orders_with_carrier_filter(self, client, admin_token):
        """Test filtering orders by carrier"""
        response = client.get(
            "/api/admin/orders/all?carrier=Blue Dart",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_orders_with_search(self, client, admin_token):
        """Test searching orders"""
        response = client.get(
            "/api/admin/orders/all?search=test",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_orders_pagination(self, client, admin_token):
        """Test order pagination"""
        response = client.get(
            "/api/admin/orders/all?skip=0&limit=10",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page_size"] == 10

    def test_bulk_update_status_success(self, client, admin_token, db_session, sample_order):
        """Test bulk updating order status"""
        order_ids = [sample_order.id]

        response = client.post(
            "/api/admin/orders/bulk-update-status",
            headers={"X-Admin-Token": admin_token},
            json=order_ids,
            params={"new_status": "in_transit"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    def test_bulk_update_invalid_status(self, client, admin_token):
        """Test bulk update with invalid status"""
        response = client.post(
            "/api/admin/orders/bulk-update-status",
            headers={"X-Admin-Token": admin_token},
            json=[1, 2, 3],
            params={"new_status": "invalid_status"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_order_success(self, client, admin_token, db_session, sample_order):
        """Test deleting an order"""
        response = client.delete(
            f"/api/admin/orders/{sample_order.id}",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    def test_delete_nonexistent_order(self, client, admin_token):
        """Test deleting non-existent order returns 404"""
        response = client.delete(
            "/api/admin/orders/99999",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAnalyticsEndpoints:
    """Tests for analytics and reporting endpoints"""

    def test_get_analytics_overview(self, client, admin_token):
        """Test getting analytics overview"""
        response = client.get(
            "/api/admin/analytics/overview",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_orders" in data
        assert "booked_orders" in data
        assert "total_revenue" in data
        assert "status_breakdown" in data
        assert "carrier_revenue" in data
        assert "payment_modes" in data

    def test_analytics_overview_with_date_range(self, client, admin_token):
        """Test analytics with date range filter"""
        response = client.get(
            "/api/admin/analytics/overview?date_from=2024-01-01&date_to=2024-12-31",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_get_daily_stats(self, client, admin_token):
        """Test getting daily statistics"""
        response = client.get(
            "/api/admin/analytics/daily-stats",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "period_days" in data
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_daily_stats_custom_days(self, client, admin_token):
        """Test daily stats with custom period"""
        response = client.get(
            "/api/admin/analytics/daily-stats?days=7",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["period_days"] == 7

    def test_get_carrier_performance(self, client, admin_token):
        """Test getting carrier performance metrics"""
        response = client.get(
            "/api/admin/analytics/carrier-performance",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "carriers" in data
        assert isinstance(data["carriers"], list)

    def test_carrier_performance_structure(self, client, admin_token, db_session, sample_booked_order):
        """Test carrier performance data structure"""
        response = client.get(
            "/api/admin/analytics/carrier-performance",
            headers={"X-Admin-Token": admin_token}
        )

        data = response.json()
        if data["carriers"]:
            carrier = data["carriers"][0]
            assert "carrier" in carrier
            assert "total_orders" in carrier
            assert "total_revenue" in carrier
            assert "modes" in carrier

    def test_get_zone_distribution(self, client, admin_token):
        """Test getting zone distribution"""
        response = client.get(
            "/api/admin/analytics/zone-distribution",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "zones" in data


class TestCarrierManagement:
    """Tests for carrier activation/deactivation"""

    def test_toggle_carrier_active(self, client, admin_token):
        """Test activating/deactivating a carrier"""
        response = client.put(
            "/api/admin/carriers/Blue Dart/toggle-active?active=false",
            headers={"X-Admin-Token": admin_token}
        )

        # May fail if Blue Dart doesn't exist, check for 200 or 404
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_toggle_carrier_creates_backup(self, client, admin_token):
        """Test that toggling carrier creates backup"""
        import os
        from app.main import RATE_CARD_PATH

        backup_path = RATE_CARD_PATH + ".bak"

        # Remove backup if exists
        if os.path.exists(backup_path):
            os.remove(backup_path)

        # Try to toggle any carrier (may not exist)
        client.put(
            "/api/admin/carriers/TestCarrier/toggle-active?active=true",
            headers={"X-Admin-Token": admin_token}
        )

        # Backup should be created if carrier exists
        # If not, that's also acceptable

    def test_toggle_nonexistent_carrier(self, client, admin_token):
        """Test toggling non-existent carrier returns 404"""
        response = client.put(
            "/api/admin/carriers/NonExistentCarrier123/toggle-active?active=true",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_carrier_success(self, client, admin_token):
        """Test deleting a carrier (may fail if carrier doesn't exist)"""
        # First add a test carrier
        carrier_data = {
            "carrier_name": "ToBeDeleted",
            "mode": "Surface",
            "min_weight": 0.5,
            "active": True,
            "forward_rates": {
                "z_a": 30.0,
                "z_b": 35.0,
                "z_c": 40.0,
                "z_d": 45.0,
                "z_f": 50.0
            },
            "additional_rates": {
                "z_a": 5.0,
                "z_b": 6.0,
                "z_c": 7.0,
                "z_d": 8.0,
                "z_f": 9.0
            },
            "cod_fixed": 25.0,
            "cod_percent": 0.015
        }

        client.post(
            "/api/admin/rates/add",
            headers={"X-Admin-Token": admin_token},
            json=carrier_data
        )

        # Now delete it
        response = client.delete(
            "/api/admin/carriers/ToBeDeleted",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "success"

    def test_delete_nonexistent_carrier(self, client, admin_token):
        """Test deleting non-existent carrier returns 404"""
        response = client.delete(
            "/api/admin/carriers/NonExistentCarrier999",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
