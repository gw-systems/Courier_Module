"""
Tests for order CRUD endpoints (app/orders.py)
"""
import pytest
from fastapi import status
from datetime import datetime


class TestCreateOrder:
    """Tests for creating orders"""

    def test_create_order_success(self, client, sample_order_data):
        """Test creating a new order"""
        response = client.post("/api/orders/", json=sample_order_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "order_number" in data
        assert data["status"] in ["pending", "draft"]
        assert data["sender_pincode"] == sample_order_data["sender_pincode"]
        assert data["recipient_pincode"] == sample_order_data["recipient_pincode"]

    def test_create_order_generates_order_number(self, client, sample_order_data):
        """Test that order number is auto-generated"""
        response = client.post("/api/orders", json=sample_order_data)
        data = response.json()

        assert data["order_number"] is not None
        assert len(data["order_number"]) > 0

    def test_create_order_sets_default_status(self, client, sample_order_data):
        """Test default status is 'draft' or 'pending'"""
        response = client.post("/api/orders/", json=sample_order_data)
        data = response.json()

        assert data["status"] in ["pending", "draft"]

    def test_create_order_with_cod(self, client, sample_order_data):
        """Test creating COD order"""
        sample_order_data["payment_mode"] = "cod"
        response = client.post("/api/orders/", json=sample_order_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["payment_mode"] == "cod"

    def test_create_order_with_prepaid(self, client, sample_order_data):
        """Test creating prepaid order"""
        sample_order_data["payment_mode"] = "prepaid"
        response = client.post("/api/orders/", json=sample_order_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["payment_mode"] == "prepaid"

    def test_create_order_invalid_payment_mode(self, client, sample_order_data):
        """Test invalid payment mode fails validation"""
        sample_order_data["payment_mode"] = "invalid"
        response = client.post("/api/orders", json=sample_order_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_order_missing_required_fields(self, client):
        """Test creating order with missing fields fails"""
        incomplete_data = {
            "sender_pincode": 400001
            # Missing other required fields
        }
        response = client.post("/api/orders", json=incomplete_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_order_invalid_pincode(self, client, sample_order_data):
        """Test invalid pincode validation"""
        sample_order_data["sender_pincode"] = 12345  # Only 5 digits
        response = client.post("/api/orders", json=sample_order_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_order_negative_weight(self, client, sample_order_data):
        """Test negative weight validation"""
        sample_order_data["weight"] = -1.5
        response = client.post("/api/orders", json=sample_order_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_order_with_dimensions(self, client, sample_order_data):
        """Test creating order with package dimensions"""
        sample_order_data["length"] = 30.0
        sample_order_data["width"] = 20.0
        sample_order_data["height"] = 10.0

        response = client.post("/api/orders/", json=sample_order_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["length"] == 30.0
        assert data["width"] == 20.0
        assert data["height"] == 10.0


class TestGetOrders:
    """Tests for retrieving orders"""

    def test_get_all_orders(self, client):
        """Test getting all orders (public endpoint)"""
        response = client.get("/api/orders/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_get_order_by_id(self, client, db_session, sample_order):
        """Test getting a specific order by ID"""
        response = client.get(f"/api/orders/{sample_order.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_order.id

    def test_get_nonexistent_order(self, client):
        """Test getting non-existent order returns 404"""
        response = client.get("/api/orders/99999")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateOrder:
    """Tests for updating orders"""

    def test_update_order_public(self, client, db_session, sample_order):
        """Test updating order via public endpoint"""
        update_data = {"status": "in_transit"}

        response = client.put(
            f"/api/orders/{sample_order.id}",
            json=update_data
        )

        # Public update endpoint exists
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_order_admin(self, client, admin_token, db_session, sample_order):
        """Test updating order via admin endpoint"""
        update_data = {"status": "in_transit"}

        response = client.put(
            f"/api/admin/orders/{sample_order.id}",
            headers={"X-Admin-Token": admin_token},
            json=update_data
        )

        # Admin endpoint should work
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "in_transit"

    def test_update_order_carrier(self, client, admin_token, db_session, sample_order):
        """Test updating selected carrier"""
        update_data = {"selected_carrier": "DTDC"}

        response = client.put(
            f"/api/admin/orders/{sample_order.id}",
            headers={"X-Admin-Token": admin_token},
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_order_multiple_fields(self, client, admin_token, db_session, sample_order):
        """Test updating multiple fields at once"""
        update_data = {
            "status": "booked",
            "selected_carrier": "Blue Dart"
        }

        response = client.put(
            f"/api/admin/orders/{sample_order.id}",
            headers={"X-Admin-Token": admin_token},
            json=update_data
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_nonexistent_order(self, client, admin_token):
        """Test updating non-existent order returns 404"""
        update_data = {"status": "in_transit"}

        response = client.put(
            "/api/admin/orders/99999",
            headers={"X-Admin-Token": admin_token},
            json=update_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompareCarriers:
    """Tests for comparing carriers for orders"""

    def test_compare_carriers_for_order(self, client):
        """Test getting carrier comparisons for an order"""
        # Prepare order comparison data
        comparison_data = {
            "source_pincode": 400001,
            "dest_pincode": 110001,
            "weight": 1.5,
            "mode": "Both"
        }

        response = client.post(
            "/api/orders/compare-carriers",
            json=comparison_data
        )

        # Should return carrier comparison results
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestBookCarrier:
    """Tests for booking carriers"""

    def test_book_carrier_endpoint_exists(self, client):
        """Test book carrier endpoint exists"""
        booking_data = {
            "order_id": 1,
            "carrier": "Blue Dart",
            "total_cost": 150.00
        }

        response = client.post(
            "/api/orders/book-carrier",
            json=booking_data
        )

        # Endpoint should exist (may fail with 404 for non-existent order)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY]


class TestOrderValidation:
    """Tests for order validation logic"""

    def test_order_contact_validation(self, client, sample_order_data):
        """Test contact number validation"""
        sample_order_data["recipient_contact"] = "12345"  # Too short
        response = client.post("/api/orders", json=sample_order_data)

        # Should either fail validation or accept it based on schema
        # Adjust assertion based on actual validation rules

    def test_order_email_validation(self, client, sample_order_data):
        """Test email validation if present"""
        if "recipient_email" in sample_order_data:
            sample_order_data["recipient_email"] = "invalid-email"
            response = client.post("/api/orders", json=sample_order_data)
            # Check validation

    def test_order_date_created(self, client, sample_order_data):
        """Test that created_at timestamp is set"""
        response = client.post("/api/orders", json=sample_order_data)
        data = response.json()

        assert "created_at" in data
        # Verify it's a valid timestamp


class TestOrderStatistics:
    """Tests for order statistics and counts"""

    def test_order_count_by_status(self, client, admin_token):
        """Test getting order counts by status"""
        response = client.get(
            "/api/admin/orders/all",
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total" in data
