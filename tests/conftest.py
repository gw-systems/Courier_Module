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
