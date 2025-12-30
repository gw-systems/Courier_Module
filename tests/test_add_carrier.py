"""
Tests for the Add Carrier endpoint
"""
import pytest
from httpx import AsyncClient
import json
import os
from app.main import app, RATE_CARD_PATH


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
            "z_f": 55.0
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


@pytest.mark.asyncio
async def test_add_carrier_success(admin_token, valid_carrier_data):
    """Test successful addition of a new carrier"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "added successfully" in data["message"]
        assert data["carrier"]["carrier_name"] == "Test Express"

        # Verify carrier was added to file
        with open(RATE_CARD_PATH, "r") as f:
            rates = json.load(f)

        carrier_names = [c["carrier_name"] for c in rates]
        assert "Test Express" in carrier_names


@pytest.mark.asyncio
async def test_add_carrier_duplicate_name(admin_token, valid_carrier_data):
    """Test rejection of duplicate carrier name"""
    # First add the carrier
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        # Try to add again with same name
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_carrier_duplicate_name_case_insensitive(admin_token, valid_carrier_data):
    """Test duplicate detection is case-insensitive"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Add first carrier
        await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        # Try to add with different case
        valid_carrier_data["carrier_name"] = "TEST EXPRESS"
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_add_carrier_no_auth(valid_carrier_data):
    """Test that endpoint requires authentication"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_carrier_invalid_auth(valid_carrier_data):
    """Test that endpoint rejects invalid token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": "wrong-token"}
        )

        assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_carrier_missing_required_field(admin_token, valid_carrier_data):
    """Test validation when required field is missing"""
    del valid_carrier_data["carrier_name"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_empty_name(admin_token, valid_carrier_data):
    """Test validation rejects empty carrier name"""
    valid_carrier_data["carrier_name"] = ""

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_whitespace_only_name(admin_token, valid_carrier_data):
    """Test validation rejects whitespace-only carrier name"""
    valid_carrier_data["carrier_name"] = "   "

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_invalid_mode(admin_token, valid_carrier_data):
    """Test validation rejects invalid mode"""
    valid_carrier_data["mode"] = "Express"  # Only Surface/Air allowed

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_negative_min_weight(admin_token, valid_carrier_data):
    """Test validation rejects negative min_weight"""
    valid_carrier_data["min_weight"] = -0.5

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_zero_min_weight(admin_token, valid_carrier_data):
    """Test validation rejects zero min_weight"""
    valid_carrier_data["min_weight"] = 0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_negative_forward_rate(admin_token, valid_carrier_data):
    """Test validation rejects negative forward rates"""
    valid_carrier_data["forward_rates"]["z_a"] = -10.0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_zero_forward_rate(admin_token, valid_carrier_data):
    """Test validation rejects zero forward rates"""
    valid_carrier_data["forward_rates"]["z_b"] = 0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_negative_additional_rate(admin_token, valid_carrier_data):
    """Test validation rejects negative additional rates"""
    valid_carrier_data["additional_rates"]["z_c"] = -5.0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_zero_additional_rate(admin_token, valid_carrier_data):
    """Test validation rejects zero additional rates"""
    valid_carrier_data["additional_rates"]["z_d"] = 0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_negative_cod_fixed(admin_token, valid_carrier_data):
    """Test validation rejects negative COD fixed fee"""
    valid_carrier_data["cod_fixed"] = -10.0

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_negative_cod_percent(admin_token, valid_carrier_data):
    """Test validation rejects negative COD percentage"""
    valid_carrier_data["cod_percent"] = -0.01

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_cod_percent_above_one(admin_token, valid_carrier_data):
    """Test validation rejects COD percentage > 1"""
    valid_carrier_data["cod_percent"] = 1.5

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_active_defaults_true(admin_token, valid_carrier_data):
    """Test that active field defaults to True when not provided"""
    del valid_carrier_data["active"]
    valid_carrier_data["carrier_name"] = "Default Active Carrier"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 200
        assert response.json()["carrier"]["active"] is True


@pytest.mark.asyncio
async def test_add_carrier_active_false(admin_token, valid_carrier_data):
    """Test that active field can be set to False"""
    valid_carrier_data["active"] = False
    valid_carrier_data["carrier_name"] = "Inactive Carrier"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 200
        assert response.json()["carrier"]["active"] is False


@pytest.mark.asyncio
async def test_add_carrier_backup_created(admin_token, valid_carrier_data):
    """Test that backup file is created before adding carrier"""
    backup_path = RATE_CARD_PATH + ".bak"
    valid_carrier_data["carrier_name"] = "Backup Test Carrier"

    # Remove backup if exists
    if os.path.exists(backup_path):
        os.remove(backup_path)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 200
        assert os.path.exists(backup_path), "Backup file should be created"


@pytest.mark.asyncio
async def test_add_carrier_air_mode(admin_token, valid_carrier_data):
    """Test adding carrier with Air mode"""
    valid_carrier_data["mode"] = "Air"
    valid_carrier_data["carrier_name"] = "Air Express"

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 200
        assert response.json()["carrier"]["mode"] == "Air"


@pytest.mark.asyncio
async def test_add_carrier_missing_forward_rate_zone(admin_token, valid_carrier_data):
    """Test validation when a forward rate zone is missing"""
    del valid_carrier_data["forward_rates"]["z_f"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_carrier_missing_additional_rate_zone(admin_token, valid_carrier_data):
    """Test validation when an additional rate zone is missing"""
    del valid_carrier_data["additional_rates"]["z_a"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/rates/add",
            json=valid_carrier_data,
            headers={"X-Admin-Token": admin_token}
        )

        assert response.status_code == 422
