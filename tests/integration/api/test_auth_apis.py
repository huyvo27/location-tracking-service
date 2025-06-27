import pytest
from httpx import AsyncClient

from tests.utils import (
    generate_phone_number,
    generate_strong_password,
    random_lower_string,
)

pytestmark = pytest.mark.asyncio

ENDPOINT_PREFIX = "/api/v1/auth"


@pytest.fixture
def user_data() -> dict:
    userame = random_lower_string(length=8)
    return {
        "username": userame,
        "password": generate_strong_password(),
        "email": f"{userame}@gmail.com",
        "full_name": userame,
        "phone_number": generate_phone_number(),
    }


async def test_register_and_login_flow(async_client: AsyncClient, user_data: dict):
    # Register
    resp = await async_client.post(ENDPOINT_PREFIX + "/register", json=user_data)
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    assert token
    # Login
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    resp = await async_client.post(ENDPOINT_PREFIX + "/login", json=login_data)
    assert resp.status_code == 200
    login_token = resp.json()["data"]["access_token"]
    assert login_token

    # Logout
    resp = await async_client.post(ENDPOINT_PREFIX + "/logout")
    assert resp.status_code == 200
    assert resp.json()["data"] is None


async def test_login_fail(async_client: AsyncClient, user_data: dict):
    wrong_login_data = {
        "username": user_data["username"],
        "password": user_data["password"],
    }
    resp = await async_client.post(ENDPOINT_PREFIX + "/login", json=wrong_login_data)
    assert resp.status_code == 401 or resp.status_code == 400


async def test_register_duplicate(async_client: AsyncClient, user_data: dict):
    # Register a user
    resp = await async_client.post(ENDPOINT_PREFIX + "/register", json=user_data)
    assert resp.status_code == 200

    # Register again with the same username/email
    resp = await async_client.post(ENDPOINT_PREFIX + "/register", json=user_data)
    assert resp.status_code == 400 or resp.status_code == 409
