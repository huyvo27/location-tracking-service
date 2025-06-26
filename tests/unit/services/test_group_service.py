import uuid

import pytest
import pytest_asyncio

from app.core.security import hash_password, verify_password
from app.exceptions import (
    GroupNameAlreadyExists,
    InvalidGroupKey,
    UserNotFound,
    UserNotMemberOfGroup,
)
from app.models.group import Group
from app.models.membership import Membership
from app.models.user import User
from app.schemas.group import (
    GroupCreateRequest,
    GroupJoinRequest,
    GroupListRequest,
    GroupUpdateRequest,
    MyGroupListRequest,
)
from app.services.group import GroupService
from app.utils.enums import UserRole

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def group_service(db_session):
    return GroupService(db=db_session)


@pytest.fixture
def group_create_data():
    return GroupCreateRequest(
        name="TestGroup",
        description="A test group",
        key="secretkey",
    )


@pytest.fixture
def group_join_data():
    return GroupJoinRequest(key="secretkey")


@pytest.fixture
def group_update_data():
    return GroupUpdateRequest(
        description="Updated description", capacity=20, key="newsecretkey"
    )


@pytest.fixture
def group_list_params():
    return GroupListRequest(page=1, page_size=2, search="Test")


@pytest.fixture
def my_group_list_params():
    return MyGroupListRequest(page=1, page_size=2, search="Test", only_owned=False)


async def get_or_create_user(db_session, data):
    user = await User.find_by(db=db_session, username=data["username"])
    if user:
        return user
    return await User.create(
        db=db_session,
        username=data["username"],
        phone_number=data["phone_number"],
        full_name=data["full_name"],
        email=data["email"],
        hashed_password=hash_password(data["password"]),
        is_active=data["is_active"],
        role=data["role"].value,
    )


@pytest_asyncio.fixture
async def leader_user(db_session):
    data = {
        "username": "leader",
        "password": "p@ssw0rD",
        "email": "leader@example.com",
        "full_name": "Leader",
        "phone_number": "0395345456",
        "is_active": True,
        "role": UserRole.USER,
    }

    return await get_or_create_user(db_session, data)


@pytest_asyncio.fixture
async def member_user(db_session):
    data = {
        "username": "member",
        "password": "p@ssw0rD",
        "email": "member@example.com",
        "full_name": "Member",
        "phone_number": "0395345457",
        "is_active": True,
        "role": UserRole.USER,
    }

    return await get_or_create_user(db_session, data)


@pytest_asyncio.fixture
async def non_member_user(db_session):
    data = {
        "username": "nonmember",
        "password": "p@ssw0rD",
        "email": "nonmember@example.com",
        "full_name": "Non-Member",
        "phone_number": "0395345458",
        "is_active": True,
        "role": UserRole.USER,
    }

    return await get_or_create_user(db_session, data)


@pytest_asyncio.fixture(scope="module", autouse=True)
async def cleanup(async_session):
    yield
    async with async_session() as session:
        users = await User.all(db=session)
        groups = await Group.all(db=session)
        for user in users:
            await user.delete(db=session)
        for group in groups:
            await group.delete(db=session)


@pytest_asyncio.fixture
async def created_group(group_service, group_create_data, leader_user, db_session):
    group = await Group.find_by(db=db_session, name=group_create_data.name)
    return (
        group
        if group
        else await group_service.create_group(group_create_data, leader_user)
    )


@pytest_asyncio.fixture
async def membership(
    group_service, created_group, member_user, group_join_data, db_session
):
    ms = await Membership.find_by(
        db=db_session, group_id=created_group.id, user_id=member_user.id
    )
    return (
        ms
        if ms
        else await group_service.join_group(created_group, member_user, group_join_data)
    )


async def test_create_group_success(group_service, group_create_data, leader_user):
    group = await group_service.create_group(group_create_data, leader_user)
    assert group.name == group_create_data.name
    assert verify_password(group_create_data.key, group.hashed_key)


async def test_create_group_already_exists(
    group_service, group_create_data, member_user
):
    with pytest.raises(GroupNameAlreadyExists):
        await group_service.create_group(group_create_data, member_user)


async def test_join_group_success(
    group_service, created_group, member_user, group_join_data
):
    membership = await group_service.join_group(
        created_group, member_user, group_join_data
    )
    assert membership.user_id == member_user.id
    assert membership.group_id == created_group.id


async def test_join_group_invalid_key(group_service, created_group, non_member_user):
    bad_join_data = GroupJoinRequest(key="wrongkey")
    with pytest.raises(InvalidGroupKey):
        await group_service.join_group(created_group, non_member_user, bad_join_data)


async def test_list_groups(group_service, group_list_params):
    result = await group_service.list(group_list_params)
    assert isinstance(result, list)


async def test_get_my_groups_owned(group_service, leader_user, my_group_list_params):
    my_group_list_params.only_owned = True
    result = await group_service.get_my_groups(leader_user, my_group_list_params)
    assert isinstance(result, list)


async def test_get_my_groups_member(group_service, member_user, my_group_list_params):
    my_group_list_params.only_owned = False
    result = await group_service.get_my_groups(member_user, my_group_list_params)
    assert isinstance(result, list)


async def test_kick_member_success(
    group_service, created_group, db_session, member_user
):
    await group_service.kick_member(created_group, member_user.uuid)
    membership = await Membership.find_by(
        db=db_session, user_id=member_user.id, group_id=created_group.id
    )
    assert membership is None


async def test_kick_member_user_not_found(group_service, created_group):
    with pytest.raises(UserNotFound):
        await group_service.kick_member(created_group, uuid.uuid4())


async def test_kick_member_not_member(group_service, created_group, non_member_user):
    with pytest.raises(UserNotMemberOfGroup):
        await group_service.kick_member(created_group, non_member_user.uuid)


async def test_update_group(group_service, created_group, group_update_data):
    updated = await group_service.update_group(created_group, group_update_data)
    assert updated.description == group_update_data.description
    assert updated.capacity == group_update_data.capacity
    assert verify_password(group_update_data.key, updated.hashed_key)
