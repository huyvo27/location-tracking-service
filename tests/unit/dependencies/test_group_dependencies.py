from uuid import uuid4

import pytest

from app.dependencies.group import (
    membership_required,
    ownership_required,
    valid_group,
    valid_user,
)
from app.exceptions import (
    GroupNotFound,
    UserAlreadyMemberOfGroup,
    UserNotMemberOfGroup,
    UserNotOwnerOfGroup,
)

pytestmark = pytest.mark.asyncio


class DummyUser:
    def __init__(self, id, memberships=None):
        self.id = id
        self.memberships = memberships or []


class DummyGroup:
    def __init__(self, id, owner_id):
        self.id = id
        self.owner_id = owner_id


class DummyMembership:
    pass


async def test_valid_user_not_member():
    user = DummyUser(id=1, memberships=[])
    result = await valid_user(user=user)
    assert result is user


async def test_valid_user_already_member():
    user = DummyUser(id=1, memberships=[object()])
    with pytest.raises(UserAlreadyMemberOfGroup):
        await valid_user(user=user)


async def test_valid_group_found(mocker):
    dummy_group = DummyGroup(id=1, owner_id=2)
    mocker.patch("app.models.group.Group.find_by", return_value=dummy_group)
    group_uuid = uuid4()
    db = object()
    result = await valid_group(group_uuid=group_uuid, db=db)
    assert result is dummy_group


async def test_valid_group_not_found(mocker):
    mocker.patch("app.models.group.Group.find_by", return_value=None)
    group_uuid = uuid4()
    db = object()
    with pytest.raises(GroupNotFound):
        await valid_group(group_uuid=group_uuid, db=db)


async def test_membership_required_found(mocker):
    dummy_group = DummyGroup(id=1, owner_id=2)
    dummy_user = DummyUser(id=3)
    mocker.patch(
        "app.models.membership.Membership.find_by", return_value=DummyMembership()
    )
    db = object()
    result = await membership_required(group=dummy_group, user=dummy_user, db=db)
    assert isinstance(result, DummyMembership)


async def test_membership_required_not_found(mocker):
    dummy_group = DummyGroup(id=1, owner_id=2)
    dummy_user = DummyUser(id=3)
    mocker.patch("app.models.membership.Membership.find_by", return_value=None)
    db = object()
    with pytest.raises(UserNotMemberOfGroup):
        await membership_required(group=dummy_group, user=dummy_user, db=db)


async def test_ownership_required_owner():
    dummy_group = DummyGroup(id=1, owner_id=2)
    dummy_user = DummyUser(id=2)
    result = await ownership_required(group=dummy_group, user=dummy_user)
    assert result is dummy_group


async def test_ownership_required_not_owner():
    dummy_group = DummyGroup(id=1, owner_id=2)
    dummy_user = DummyUser(id=3)
    with pytest.raises(UserNotOwnerOfGroup):
        await ownership_required(group=dummy_group, user=dummy_user)
