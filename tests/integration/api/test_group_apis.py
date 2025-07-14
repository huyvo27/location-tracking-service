from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, verify_password
from tests.utils import (
    generate_phone_number,
    generate_strong_password,
    random_lower_string,
)

AUTH_ENDPOINT_PREFIX = "/api/v1/auth"
GROUPS_ENDPOINT_PREFIX = "/api/v1/groups"

pytestmark = pytest.mark.asyncio


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


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, user_data) -> dict:
    resp = await async_client.post(AUTH_ENDPOINT_PREFIX + "/register", json=user_data)
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def owner_user_data() -> dict:
    username = random_lower_string(length=8)
    return {
        "username": username,
        "password": generate_strong_password(),
        "email": f"{username}@example.com",
        "full_name": username,
        "phone_number": generate_phone_number(),
    }


@pytest_asyncio.fixture
async def owner_auth_headers(async_client: AsyncClient, owner_user_data) -> dict:
    resp = await async_client.post(
        AUTH_ENDPOINT_PREFIX + "/register", json=owner_user_data
    )
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def group_data() -> dict:
    return {
        "name": random_lower_string(length=10),
        "key": generate_strong_password(8),
        "description": "Group description",
    }


@pytest.fixture
def location_data() -> dict:
    return {
        "latitude": 10.1234,
        "longitude": 106.5678,
        "timestamp": datetime.now(timezone.utc).timestamp(),
        "nickname": random_lower_string(),
    }


@pytest_asyncio.fixture
async def existing_group(
    async_client: AsyncClient,
    pg_db: AsyncSession,
    owner_auth_headers: dict,
    group_data: dict,
) -> AsyncGenerator[SimpleNamespace, Any]:
    resp = await async_client.post(
        GROUPS_ENDPOINT_PREFIX, json=group_data, headers=owner_auth_headers
    )
    assert resp.status_code == 200
    group_uuid = resp.json()["data"]["uuid"]

    yield SimpleNamespace(
        uuid=group_uuid, key=group_data["key"], name=group_data["name"]
    )

    # Cleanup
    from app.models.group import Group

    group = await Group.find_by(uuid=group_uuid)
    if group:
        pg_db.expunge_all()
        await group.delete(db=pg_db)


async def test_list_groups(
    async_client: AsyncClient, auth_headers: dict, existing_group: SimpleNamespace
):
    # List groups
    resp = await async_client.get(GROUPS_ENDPOINT_PREFIX, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        assert data["items"][0]["name"] == existing_group.name
        assert data["items"][0]["uuid"] == existing_group.uuid

    # Try without authentication
    resp = await async_client.get(GROUPS_ENDPOINT_PREFIX)
    assert resp.status_code == 401


async def test_get_my_groups(
    async_client: AsyncClient,
    owner_auth_headers: dict,
    existing_group: SimpleNamespace,
):
    # List user's groups
    resp = await async_client.get(
        GROUPS_ENDPOINT_PREFIX + "?joined=true", headers=owner_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    assert isinstance(data["items"], list)
    assert any(item["uuid"] == existing_group.uuid for item in data["items"])

    # Try without authentication
    resp = await async_client.get(GROUPS_ENDPOINT_PREFIX + "?joined=true")
    assert resp.status_code == 401


async def test_get_group_detail(
    async_client: AsyncClient,
    owner_auth_headers: dict,
    existing_group: SimpleNamespace,
    auth_headers: dict,
):
    # Get group details
    resp = await async_client.get(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}", headers=owner_auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["uuid"] == existing_group.uuid
    assert data["name"] == existing_group.name
    assert "members" in data

    # Try without membership
    resp = await async_client.get(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}", headers=auth_headers
    )
    assert resp.status_code == 403

    # Try without authentication
    resp = await async_client.get(f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}")
    assert resp.status_code == 401


async def test_create_group(
    async_client: AsyncClient,
    owner_auth_headers: dict,
    auth_headers: dict,
    group_data: dict,
    existing_group: SimpleNamespace,
):
    # Group are created
    assert group_data["name"] == existing_group.name

    # Verify in database
    from app.dependencies.db import get_redis
    from app.models.group import Group
    from app.services.group_cache import GroupCacheService

    group = await Group.find_by(name=group_data["name"])
    group_uuid = str(group.uuid)
    gc = GroupCacheService(
        redis=await get_redis(group_uuid=group_uuid), db=None, group_uuid=group_uuid
    )
    # Get users info
    token_data = decode_access_token(owner_auth_headers["Authorization"].split()[1])
    user_uuid = token_data.sub

    assert group is not None
    assert group_uuid == existing_group.uuid
    assert await gc.is_exists()
    assert await gc.is_member(user_uuid)

    # Try creating duplicate group name
    resp = await async_client.post(
        GROUPS_ENDPOINT_PREFIX, json=group_data, headers=auth_headers
    )
    assert resp.status_code == 409

    # Try without authentication
    resp = await async_client.post(GROUPS_ENDPOINT_PREFIX, json=group_data)
    assert resp.status_code == 401


async def test_join_group(
    async_client: AsyncClient, auth_headers: dict, existing_group: SimpleNamespace
):
    # Join group
    join_data = {"key": existing_group.key}
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    data = resp.json()["data"]

    # Get user info
    token_data = decode_access_token(auth_headers["Authorization"].split()[1])
    user_uuid = token_data.sub
    # init group_cache_service
    from app.dependencies.db import get_redis
    from app.services.group_cache import GroupCacheService

    gc = GroupCacheService(
        redis=await get_redis(group_uuid=existing_group.uuid),
        db=None,
        group_uuid=existing_group.uuid,
    )

    assert resp.status_code == 200
    assert data["group_uuid"] == existing_group.uuid
    assert data["user_uuid"] == user_uuid
    assert await gc.is_exists()
    assert await gc.is_member(user_uuid)

    # Try joining again (should fail)
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    assert resp.status_code == 400

    # Try without authentication
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members", json=join_data
    )
    assert resp.status_code == 401


async def test_delete_group(
    async_client: AsyncClient,
    pg_db: AsyncSession,
    owner_auth_headers: dict,
    auth_headers: dict,
    existing_group: SimpleNamespace,
):
    # Try without authentication
    resp = await async_client.delete(f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}")
    assert resp.status_code == 401

    # Try deleting as non-owner
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}", headers=auth_headers
    )
    assert resp.status_code == 403

    # init group_cache_service
    from app.dependencies.db import get_redis
    from app.services.group_cache import GroupCacheService

    gc = GroupCacheService(
        redis=await get_redis(group_uuid=existing_group.uuid),
        db=None,
        group_uuid=existing_group.uuid,
    )

    # Delete group as owner
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}", headers=owner_auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None
    assert not await gc.is_exists()

    # Verify group is deleted
    from app.models.group import Group

    group = await Group.find_by(db=pg_db, uuid=existing_group.uuid)
    assert group is None


async def test_leave_group(
    async_client: AsyncClient, auth_headers: dict, existing_group: SimpleNamespace
):
    # Join group
    join_data = {"key": existing_group.key}
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Leave group
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/me",
        headers=auth_headers,
    )

    # init group_cache_service
    from app.dependencies.db import get_redis
    from app.services.group_cache import GroupCacheService

    gc = GroupCacheService(
        redis=await get_redis(group_uuid=existing_group.uuid),
        db=None,
        group_uuid=existing_group.uuid,
    )
    # Get user info
    token_data = decode_access_token(auth_headers["Authorization"].split()[1])
    user_uuid = token_data.sub

    assert resp.status_code == 200
    assert await gc.is_exists()
    assert not await gc.is_member(user_uuid)

    # Try leaving again (should fail)
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/me",
        headers=auth_headers,
    )
    assert resp.status_code == 403

    # Try without authentication
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/me"
    )
    assert resp.status_code == 401


async def test_kick_member(
    async_client: AsyncClient,
    owner_auth_headers: dict,
    auth_headers: dict,
    existing_group: SimpleNamespace,
):
    # Join group
    join_data = {"key": existing_group.key}
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Get users info
    token_data = decode_access_token(owner_auth_headers["Authorization"].split()[1])
    owner_uuid = token_data.sub
    token_data = decode_access_token(auth_headers["Authorization"].split()[1])
    user_uuid = token_data.sub

    # Try without authentication
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/{user_uuid}"
    )
    assert resp.status_code == 401

    # Try kicking as non-owner
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/{owner_uuid}",
        headers=auth_headers,
    )
    assert resp.status_code == 403

    # Kick user as owner
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/{user_uuid}",
        headers=owner_auth_headers,
    )
    # init group_cache_service
    from app.dependencies.db import get_redis
    from app.services.group_cache import GroupCacheService

    gc = GroupCacheService(
        redis=await get_redis(group_uuid=existing_group.uuid),
        db=None,
        group_uuid=existing_group.uuid,
    )

    assert resp.status_code == 200
    assert resp.json()["data"] is None
    assert await gc.is_exists()
    assert not await gc.is_member(user_uuid)

    #  Kick user as owner again
    resp = await async_client.delete(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/{user_uuid}",
        headers=owner_auth_headers,
    )
    assert resp.status_code == 404


async def test_update_group(
    async_client: AsyncClient,
    pg_db: AsyncSession,
    owner_auth_headers: dict,
    auth_headers: dict,
    existing_group: SimpleNamespace,
):
    # Update group as owner
    update_data = {
        "key": generate_strong_password(),
        "description": "Updated group description",
    }
    resp = await async_client.put(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}",
        json=update_data,
        headers=owner_auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["description"] == update_data["description"]

    # Verify in database
    from app.models.group import Group

    group = await Group.find_by(db=pg_db, uuid=existing_group.uuid)
    assert verify_password(update_data["key"], group.hashed_key)

    # Try updating as non-owner
    resp = await async_client.put(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}",
        json=update_data,
        headers=auth_headers,
    )
    assert resp.status_code == 403

    # Try without authentication
    resp = await async_client.put(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}", json=update_data
    )
    assert resp.status_code == 401


async def test_update_location(
    async_client: AsyncClient,
    auth_headers: dict,
    existing_group: SimpleNamespace,
    location_data: dict,
):
    join_data = {"key": existing_group.key}
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    resp = await async_client.put(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/me/location",
        json=location_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None


async def test_get_group_locations(
    async_client: AsyncClient,
    auth_headers: dict,
    owner_auth_headers: dict,
    existing_group: SimpleNamespace,
    location_data: dict,
):
    # First join the group
    join_data = {"key": existing_group.key}
    resp = await async_client.post(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members",
        json=join_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Update location first
    token_data = decode_access_token(auth_headers["Authorization"].split()[1])
    user_uuid = token_data.sub

    await async_client.put(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/me/location",
        json=location_data,
        headers=auth_headers,
    )

    # Get group locations
    resp = await async_client.get(
        f"{GROUPS_ENDPOINT_PREFIX}/{existing_group.uuid}/members/locations",
        headers=owner_auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data, dict)
    items = data["items"]
    assert isinstance(items, list)
    assert any(loc["user_uuid"] == user_uuid for loc in items)
    assert any(loc["nickname"] == location_data["nickname"] for loc in items)
    assert any(loc["latitude"] == location_data["latitude"] for loc in items)
    assert any(loc["longitude"] == location_data["longitude"] for loc in items)
    assert any(loc["timestamp"] == location_data["timestamp"] for loc in items)
