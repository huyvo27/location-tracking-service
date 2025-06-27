import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.utils.enums import UserRole
from tests.utils import (
    generate_phone_number,
    generate_strong_password,
    random_lower_string,
)

pytestmark = pytest.mark.asyncio

AUTH_ENDPOINT_PREFIX = "/api/v1/auth"
USERS_ENDPOINT_PREFIX = "/api/v1/users"


@pytest.fixture
def user_data() -> dict:
    username = random_lower_string(length=8)
    return {
        "username": username,
        "password": generate_strong_password(),
        "email": f"{username}@example.com",
        "full_name": username,
        "phone_number": generate_phone_number(),
    }


@pytest.fixture
def normal_user_data() -> dict:
    username = random_lower_string(length=8)
    return {
        "username": username,
        "password": generate_strong_password(),
        "email": f"{username}@example.com",
        "full_name": username,
        "phone_number": generate_phone_number(),
    }


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, normal_user_data) -> dict:
    resp = await async_client.post(
        AUTH_ENDPOINT_PREFIX + "/register", json=normal_user_data
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(async_client: AsyncClient, default_admin: dict) -> dict:
    admin_user_data = {
        "username": default_admin["username"],
        "password": default_admin["password"],
    }
    resp = await async_client.post(
        AUTH_ENDPOINT_PREFIX + "/login", json=admin_user_data
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_list_users(
    async_client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
):
    # Test as normal user (should get UserLimitedResponse)
    resp = await async_client.get(USERS_ENDPOINT_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        assert "full_name" in data["items"][0]
        assert "username" not in data["items"][0]

    # Test as admin (should get UserResponse)
    resp = await async_client.get(USERS_ENDPOINT_PREFIX, headers=admin_auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    if data["items"]:
        assert "role" in data["items"][0]
        assert "username" in data["items"][0]


async def test_create_user(
    async_client: AsyncClient,
    admin_auth_headers: dict,
    auth_headers: dict,
    user_data: dict,
):
    # Create user as admin
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert data["phone_number"] == user_data["phone_number"]

    # Try creating as non-admin (should fail)
    resp = await async_client.post(USERS_ENDPOINT_PREFIX, json=user_data, headers={})
    assert resp.status_code == 401
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=auth_headers
    )
    assert resp.status_code == 403


async def test_get_me(
    async_client: AsyncClient, auth_headers: dict, normal_user_data: dict
):
    resp = await async_client.get(USERS_ENDPOINT_PREFIX + "/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == normal_user_data["username"]
    assert data["email"] == normal_user_data["email"]
    assert data["full_name"] == normal_user_data["full_name"]
    assert data["phone_number"] == normal_user_data["phone_number"]

    # Try without authentication
    resp = await async_client.get(USERS_ENDPOINT_PREFIX + "/me", headers={})
    assert resp.status_code == 401


async def test_update_me(
    async_client: AsyncClient, auth_headers: dict, normal_user_data: dict
):
    update_data = {
        "full_name": random_lower_string(length=10),
        "phone_number": generate_phone_number(),
    }
    resp = await async_client.put(
        USERS_ENDPOINT_PREFIX + "/me", json=update_data, headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["full_name"] == update_data["full_name"]
    assert data["phone_number"] == update_data["phone_number"]
    assert data["username"] == normal_user_data["username"]

    # Try without authentication
    resp = await async_client.put(USERS_ENDPOINT_PREFIX + "/me", json=update_data)
    assert resp.status_code == 401


async def test_get_user_by_uuid(
    async_client: AsyncClient,
    auth_headers: dict,
    admin_auth_headers: dict,
    user_data: dict,
):
    # Create a user as admin
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    user_uuid = resp.json()["data"]["uuid"]

    # Get user as normal user (limited response)
    resp = await async_client.get(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["full_name"] == user_data["full_name"]
    assert "username" not in data

    # Get user as admin (full response)
    resp = await async_client.get(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == user_data["username"]
    assert "role" in data

    # Try without authentication
    resp = await async_client.get(f"{USERS_ENDPOINT_PREFIX}/{user_uuid}")
    assert resp.status_code == 401


async def test_update_user(
    async_client: AsyncClient,
    admin_auth_headers: dict,
    auth_headers: dict,
    user_data: dict,
):
    # Create a user as admin
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    user_uuid = resp.json()["data"]["uuid"]

    # Update user as admin
    update_data = {
        "full_name": random_lower_string(length=10),
        "phone_number": generate_phone_number(),
        "role": UserRole.USER.value,
    }
    resp = await async_client.put(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}",
        json=update_data,
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["full_name"] == update_data["full_name"]
    assert data["phone_number"] == update_data["phone_number"]
    assert data["role"] == update_data["role"]

    # Try updating as non-admin
    resp = await async_client.put(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", json=update_data, headers=auth_headers
    )
    assert resp.status_code == 403


async def test_delete_user(
    async_client: AsyncClient,
    admin_auth_headers: dict,
    auth_headers: dict,
    user_data: dict,
):
    # Create a user as admin
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    user_uuid = resp.json()["data"]["uuid"]

    # Delete user as admin
    resp = await async_client.delete(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", headers=admin_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None

    # Verify user is deleted
    resp = await async_client.get(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", headers=admin_auth_headers
    )
    assert resp.status_code == 404

    # Try deleting as non-admin
    resp = await async_client.post(
        USERS_ENDPOINT_PREFIX, json=user_data, headers=admin_auth_headers
    )
    user_uuid = resp.json()["data"]["uuid"]
    resp = await async_client.delete(
        f"{USERS_ENDPOINT_PREFIX}/{user_uuid}", headers=auth_headers
    )
    assert resp.status_code == 403
