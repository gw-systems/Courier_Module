"""
Pytest configuration and fixtures for LogiRate API tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app, RATE_CARD_PATH
import os
import json
import shutil


@pytest.fixture
def client():
    """
    FastAPI test client fixture
    """
    return TestClient(app)


@pytest.fixture
def admin_token():
    """
    Admin authentication token for protected routes
    """
    return os.getenv("ADMIN_PASSWORD")


@pytest.fixture
def sample_rate_request():
    """
    Sample valid rate comparison request
    """
    return {
        "source_pincode": 400001,  # Mumbai
        "dest_pincode": 110001,    # Delhi
        "weight": 1.5,
        "is_cod": True,
        "order_value": 2000,
        "mode": "Both"
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
            "z_f": 60.0
        },
        "additional_rates": {
            "z_a": 25.0,
            "z_b": 28.0,
            "z_c": 32.0,
            "z_d": 36.0,
            "z_f": 45.0
        },
        "cod_fixed": 30.0,
        "cod_percent": 0.015
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
            "forward_rates": {"z_a": 29.43, "z_b": 32.1, "z_c": 38.79, "z_d": 44.14, "z_f": 56.18},
            "additional_rates": {"z_a": 25.41, "z_b": 28.09, "z_c": 33.44, "z_d": 36.11, "z_f": 40.13},
            "cod_fixed": 27.69,
            "cod_percent": 0.0188
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
def db_session():
    """
    Database session fixture for testing
    """
    from app.database import SessionLocal, init_db

    # Initialize database
    init_db()

    # Create session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_order(db_session):
    """
    Create a sample order in the database for testing
    """
    from app.database import Order, OrderStatus, PaymentMode
    from datetime import datetime

    order = Order(
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
        status=OrderStatus.PENDING,
        created_at=datetime.utcnow()
    )

    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    yield order

    # Cleanup
    db_session.delete(order)
    db_session.commit()


@pytest.fixture
def sample_booked_order(db_session):
    """
    Create a booked order for testing analytics
    """
    from app.database import Order, OrderStatus, PaymentMode
    from datetime import datetime

    order = Order(
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
        selected_carrier="Blue Dart",
        mode="Surface",
        zone_applied="Zone C",
        total_cost=150.00,
        created_at=datetime.utcnow()
    )

    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    yield order

    # Cleanup
    db_session.delete(order)
    db_session.commit()


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
        "order_value": 1000.0
    }
