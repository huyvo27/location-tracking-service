import uuid

import pytest
import pytest_asyncio

from app.core.security import verify_password
from app.exceptions import InvalidLogin, UsernameEmailAlreadyExists, UserNotFound
from app.models.user import User
from app.schemas.user import (
    UserCreateRequest,
    UserListRequest,
    UserRegisterRequest,
    UserUpdateMeRequest,
    UserUpdateRequest,
)
from app.services.user import UserService
from app.utils.enums import UserRole

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def user_service(db_session):
    return UserService(db=db_session)


@pytest.fixture
def creation_data():
    return UserCreateRequest(
        username="user",
        password="p@ssw0rD",
        email="user@example.com",
        full_name="User",
        phone_number="0395345456",
        is_active=True,
        role=UserRole.USER,
    )


@pytest.fixture
def registration_data():
    return UserRegisterRequest(
        username="user02",
        password="p@ssw0rD",
        email="user02@example.com",
        full_name="User 02",
        phone_number="0395345457",
    )


@pytest.fixture
def update_me_data():
    return UserUpdateMeRequest(
        password="str0ngP@ssw0rD",
        email="user03@example.com",
        full_name="User03",
        phone_number="0123456789",
    )


@pytest.fixture
def update_data():
    return UserUpdateRequest(
        password="str0ngP@ssw0rDUser04",
        email="user04@example.com",
        full_name="User04",
        phone_number="0454459789",
        is_active=True,
        role=UserRole.USER,
    )


@pytest_asyncio.fixture
async def current_user(db_session):
    users = await User.all(db=db_session)
    return users[0]


@pytest_asyncio.fixture(scope="module", autouse=True)
async def cleanup(async_session):
    yield
    async with async_session() as session:
        users = await User.all(db=session)
        for user in users:
            await user.delete(db=session)


async def test_create_user_success(user_service, creation_data):
    user = await user_service.create_user(creation_data)
    assert user.username == creation_data.username
    assert verify_password(creation_data.password, user.hashed_password)


async def test_create_user_already_exists(user_service, creation_data):
    with pytest.raises(UsernameEmailAlreadyExists):
        await user_service.create_user(creation_data)


async def test_register_user_calls_create_user(user_service, registration_data):
    user = await user_service.create_user(registration_data)
    assert user.username == registration_data.username
    assert verify_password(registration_data.password, user.hashed_password)


async def test_authenticate_success(user_service, registration_data):
    data = registration_data
    user = await user_service.authenticate(
        username=data.username, password=data.password
    )
    assert user.full_name == data.full_name


async def test_authenticate_fail(user_service):
    with pytest.raises(InvalidLogin):
        await user_service.authenticate(username="fake_user", password="fake_password")


async def test_update_me(user_service, update_me_data, current_user):
    old_hashed_password = current_user.hashed_password
    updated_user = await user_service.update_me(
        update_me_data, current_user=current_user
    )

    assert updated_user.hashed_password != old_hashed_password
    assert verify_password(update_me_data.password, updated_user.hashed_password)


async def test_update(user_service, update_data, current_user):
    old_hashed_password = current_user.hashed_password
    updated_user = await user_service.update(
        data=update_data, user_uuid=current_user.uuid
    )

    assert updated_user.hashed_password != old_hashed_password
    assert verify_password(update_data.password, updated_user.hashed_password)


async def test_get_found(user_service, current_user):
    user = await user_service.get(current_user.uuid)
    assert user == current_user


async def test_get_not_found(user_service):
    with pytest.raises(UserNotFound):
        await user_service.get(uuid.uuid4())


async def test_list(user_service):
    params = UserListRequest(page=1, page_size=2, search="user")
    result = await user_service.list(params)
    assert len(result) == 2


async def test_delete_success(user_service, current_user, db_session):
    uuid = current_user.uuid
    result = await user_service.delete(uuid)
    deleted_user = await User.find_by(db=db_session, uuid=uuid)

    assert result is True
    assert not deleted_user


async def test_delete_not_found(user_service):
    result = await user_service.delete(uuid.uuid4())
    assert result is False
