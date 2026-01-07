"""
Pytest configuration and fixtures for Courier Module tests
Migrated from FastAPI to Django
"""

import pytest
import os
import json
import shutil
from django.conf import settings
from django.test import Client
from courier.models import Order, OrderStatus, PaymentMode, FTLOrder
from datetime import datetime
from django.utils import timezone


# Path to rate cards
RATE_CARD_PATH = os.path.join(settings.BASE_DIR, "courier", "data", "rate_cards.json")


@pytest.fixture
def client():
    """
    Django test client fixture
    """
    return Client()


@pytest.fixture
def admin_token():
    """
    Admin authentication token for protected routes.
    Returns the plaintext password (not the hash).
    The authentication system will hash it and compare with ADMIN_PASSWORD_HASH.
    """
    # For tests, we use the known password that matches the hash in .env
    # In production, users provide their actual password which gets hashed and compared
    return "AdminSecure@2025"


@pytest.fixture
def sample_rate_request():
    """
    Sample valid rate comparison request
    """
    return {
        "source_pincode": 400001,  # Mumbai
        "dest_pincode": 110001,  # Delhi
        "weight": 1.5,
        "is_cod": True,
        "order_value": 2000,
        "mode": "Both",
    }


@pytest.fixture
def sample_carrier_data():
    """
    Sample carrier configuration for testing calculations
    """
    return {
        "carrier_name": "Test Carrier",
        "mode": "Surface",
        "min_weight": 0.5,
        "forward_rates": {
            "z_a": 30.0,
            "z_b": 35.0,
            "z_c": 40.0,
            "z_d": 45.0,
            "z_f": 60.0,
        },
        "additional_rates": {
            "z_a": 25.0,
            "z_b": 28.0,
            "z_c": 32.0,
            "z_d": 36.0,
            "z_f": 45.0,
        },
        "cod_fixed": 30.0,
        "cod_percent": 0.015,
    }


@pytest.fixture
def mock_rate_cards(tmp_path):
    """
    Create a temporary rate cards JSON file for testing
    """
    rate_cards = [
        {
            "carrier_name": "Test Surface",
            "mode": "Surface",
            "active": True,
            "min_weight": 0.5,
            "forward_rates": {
                "z_a": 29.43,
                "z_b": 32.1,
                "z_c": 38.79,
                "z_d": 44.14,
                "z_f": 56.18,
            },
            "additional_rates": {
                "z_a": 25.41,
                "z_b": 28.09,
                "z_c": 33.44,
                "z_d": 36.11,
                "z_f": 40.13,
            },
            "cod_fixed": 27.69,
            "cod_percent": 0.0188,
        }
    ]

    file_path = tmp_path / "rate_cards.json"
    with open(file_path, "w") as f:
        json.dump(rate_cards, f)

    return str(file_path)


@pytest.fixture(scope="function", autouse=True)
def restore_rate_cards():
    """
    Backup and restore rate_cards.json before and after each test
    This ensures test isolation for add/update carrier tests
    """
    backup_path = RATE_CARD_PATH + ".test_backup"

    # Backup before test
    if os.path.exists(RATE_CARD_PATH):
        shutil.copy(RATE_CARD_PATH, backup_path)

    yield

    # Restore after test
    if os.path.exists(backup_path):
        shutil.copy(backup_path, RATE_CARD_PATH)
        os.remove(backup_path)


@pytest.fixture
@pytest.mark.django_db
def sample_order(db):
    """
    Create a sample order in the database for testing
    """
    order = Order.objects.create(
        order_number=f"ORD-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        sender_pincode=400001,
        sender_name="Test Sender",
        sender_phone="9876543210",
        recipient_pincode=110001,
        recipient_name="Test Recipient",
        recipient_contact="9876543211",
        recipient_address="Test Address",
        weight=1.5,
        length=30.0,
        width=20.0,
        height=10.0,
        payment_mode=PaymentMode.PREPAID,
        status=OrderStatus.DRAFT,
    )

    yield order

    # Cleanup
    order.delete()


@pytest.fixture
@pytest.mark.django_db
def sample_booked_order(db):
    """
    Create a booked order for testing analytics
    """
    order = Order.objects.create(
        order_number=f"ORD-BOOKED-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        sender_pincode=400001,
        sender_name="Test Sender",
        sender_phone="9876543210",
        recipient_pincode=110001,
        recipient_name="Test Recipient",
        recipient_contact="9876543211",
        recipient_address="Test Address",
        weight=2.0,
        length=30.0,
        width=20.0,
        height=10.0,
        payment_mode=PaymentMode.COD,
        status=OrderStatus.BOOKED,
        mode="Surface",
        zone_applied="Zone C",
        total_cost=150.00,
    )

    yield order

    # Cleanup
    order.delete()


@pytest.fixture
def sample_order_data():
    """
    Sample order data for creating new orders
    """
    return {
        "sender_pincode": 400001,
        "sender_name": "John Doe",
        "sender_phone": "9876543210",
        "recipient_pincode": 110001,
        "recipient_name": "Jane Smith",
        "recipient_contact": "9876543211",
        "recipient_address": "123 Test Street, Test Area",
        "weight": 1.5,
        "length": 30.0,
        "width": 20.0,
        "height": 10.0,
        "payment_mode": "prepaid",
        "order_value": 1000.0,
    }


@pytest.fixture
def valid_carrier_data():
    """Fixture providing valid carrier data for testing"""
    return {
        "carrier_name": "Test Express",
        "mode": "Surface",
        "min_weight": 0.5,
        "active": True,
        "forward_rates": {
            "z_a": 35.0,
            "z_b": 40.0,
            "z_c": 45.0,
            "z_d": 50.0,
            "z_f": 55.0,
        },
        "additional_rates": {
            "z_a": 5.0,
            "z_b": 6.0,
            "z_c": 7.0,
            "z_d": 8.0,
            "z_f": 9.0,
        },
        "cod_fixed": 25.0,
        "cod_percent": 0.015,
    }


@pytest.fixture
@pytest.mark.django_db
def sample_ftl_order(db):
    """
    Create a sample FTL order in DRAFT status for testing
    """
    order = FTLOrder.objects.create(
        order_number=f"FTL-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name="Test Customer",
        email="test@example.com",
        phone="9876543210",
        source_city="Bangalore",
        source_address="123 Test Street, Bangalore, Karnataka",
        source_pincode=560001,
        destination_city="Bhiwandi",
        destination_pincode=421302,
        container_type="20FT",
        base_price=25000.00,
        escalation_amount=3750.00,  # 15% of base
        price_with_escalation=28750.00,  # base + escalation
        gst_amount=5175.00,  # 18% of price_with_escalation
        total_price=33925.00,  # price_with_escalation + gst
        status=OrderStatus.DRAFT,
    )

    yield order

    # Cleanup
    order.delete()


@pytest.fixture
@pytest.mark.django_db
def sample_booked_ftl_order(db):
    """
    Create a sample FTL order in BOOKED status for testing
    """
    order = FTLOrder.objects.create(
        order_number=f"FTL-BOOKED-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        name="Booked Customer",
        email="booked@example.com",
        phone="9123456789",
        source_city="Bangalore",
        source_address="456 Booked Avenue, Bangalore, Karnataka",
        source_pincode=560001,
        destination_city="Noida",
        destination_pincode=201301,
        container_type="20FT",
        base_price=30000.00,
        escalation_amount=4500.00,  # 15% of base
        price_with_escalation=34500.00,  # base + escalation
        gst_amount=6210.00,  # 18% of price_with_escalation
        total_price=40710.00,  # price_with_escalation + gst
        status=OrderStatus.BOOKED,
        booked_at=timezone.now(),
    )

    yield order

    # Cleanup
    order.delete()
