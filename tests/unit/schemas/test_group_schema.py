from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.schemas.group import (
    GroupCreateRequest,
    GroupDetailResponse,
    GroupJoinRequest,
    GroupUpdateLocationRequest,
    GroupUpdateRequest,
    KickMemberRequest,
    MemberResponse,
    MembershipResponse,
    SimpleGroupResponse,
)


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


def test_group_create_request_valid():
    req = GroupCreateRequest(
        name="group_123",
        key="supersecretkey",
        description="A test group",
        capacity=20,
    )
    assert req.name == "group_123"
    assert req.capacity == 20


@pytest.mark.parametrize("name", ["short", "invalid name!", "a" * 61])
def test_group_create_request_invalid_name(name):
    with pytest.raises(ValueError):
        GroupCreateRequest(
            name=name,
            key="supersecretkey",
        )


@pytest.mark.parametrize("key", ["short", ""])
def test_group_create_request_invalid_key(key):
    with pytest.raises(ValueError):
        GroupCreateRequest(
            name="group_123",
            key=key,
        )


def test_group_join_request_valid():
    req = GroupJoinRequest(key="supersecretkey")
    assert req.key == "supersecretkey"


def test_group_update_location_request_valid(now):
    req = GroupUpdateLocationRequest(
        longitude=100.0,
        latitude=10.0,
        timestamp=int(now.timestamp()),
    )
    assert req.longitude == 100.0
    assert req.latitude == 10.0
    assert req.timestamp == int(now.timestamp())


def test_kick_member_request():
    uuid = uuid4()
    req = KickMemberRequest(member_uuid=uuid)
    assert req.member_uuid == uuid


def test_group_update_request_defaults():
    req = GroupUpdateRequest()
    assert req.capacity == 10


def test_simple_group_response():
    uuid = uuid4()
    resp = SimpleGroupResponse(name="group", uuid=uuid, description="desc")
    assert resp.name == "group"
    assert resp.uuid == uuid


def test_member_response_serialize(now):
    uuid = uuid4()
    member = MemberResponse(user_uuid=uuid, user_full_name="Alice", joined_at=now)
    data = member.serialize()
    assert data["uuid"] == str(uuid)
    assert data["name"] == "Alice"
    assert data["joined_at"] == now.isoformat()


def test_group_detail_response_serialize(now):
    uuid = uuid4()
    owner_uuid = uuid4()
    member = MemberResponse(user_uuid=uuid4(), user_full_name="Bob", joined_at=now)
    group = GroupDetailResponse(
        name="group",
        uuid=uuid,
        description="desc",
        owner_uuid=owner_uuid,
        member_count=1,
        capacity=10,
        created_at=now,
        updated_at=now,
        memberships=[member],
    )
    data = group.serialize()
    assert data["name"] == "group"
    assert data["uuid"] == str(uuid)
    assert data["owner"] == str(owner_uuid)
    assert data["members"][0]["name"] == "Bob"


def test_membership_response(now):
    user_uuid = uuid4()
    group_uuid = uuid4()
    resp = MembershipResponse(user_uuid=user_uuid, group_uuid=group_uuid, joined_at=now)
    assert resp.user_uuid == user_uuid
    assert resp.group_uuid == group_uuid
    assert resp.joined_at == now
