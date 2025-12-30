"""
Tests for health check endpoint
"""
import pytest
from fastapi import status


class TestHealthEndpoint:
    """Tests for GET /health endpoint"""

    def test_health_endpoint_returns_200(self, client):
        """Test health endpoint returns successful response"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_health_endpoint_structure(self, client):
        """Test health endpoint returns expected structure"""
        response = client.get("/health")
        data = response.json()

        required_fields = [
            "status",
            "pincode_db_loaded",
            "pincode_count",
            "rate_cards_loaded",
            "rate_card_count"
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_health_status_is_healthy(self, client):
        """Test health status returns 'healthy'"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_pincode_db_loaded(self, client):
        """Test pincode database is loaded"""
        response = client.get("/health")
        data = response.json()

        assert data["pincode_db_loaded"] is True
        assert data["pincode_count"] > 0

    def test_rate_cards_loaded(self, client):
        """Test rate cards are loaded"""
        response = client.get("/health")
        data = response.json()

        # Should have rate cards loaded from file
        assert isinstance(data["rate_cards_loaded"], bool)
        assert isinstance(data["rate_card_count"], int)

    def test_health_check_types(self, client):
        """Test health response has correct data types"""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["status"], str)
        assert isinstance(data["pincode_db_loaded"], bool)
        assert isinstance(data["pincode_count"], int)
        assert isinstance(data["rate_cards_loaded"], bool)
        assert isinstance(data["rate_card_count"], int)

    def test_health_endpoint_no_auth_required(self, client):
        """Test health endpoint doesn't require authentication"""
        # Should work without any headers
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
