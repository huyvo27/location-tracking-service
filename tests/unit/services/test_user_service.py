import random
import uuid

import pytest
import pytest_asyncio

from app.core.security import hash_password, verify_password
from app.exceptions import InvalidLogin, UsernameEmailAlreadyExists, UserNotFound
from app.models.user import User
from app.schemas.user import (
    UserCreateRequest,
    UserListRequest,
    UserUpdateMeRequest,
    UserUpdateRequest,
)
from app.services.user import UserService
from app.utils.enums import UserRole

from tests.ultils import generate_strong_password, random_lower_string, generate_phone_number

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def user_service(db_session):
    return UserService(db=db_session)


@pytest.fixture
def create_data():
    name = random_lower_string(8)
    return UserCreateRequest(
        username=name,
        password=generate_strong_password(),
        email=f"{name}@example.com",
        full_name=name,
        phone_number=generate_phone_number(),
        is_active=True,
        role=UserRole.USER,
    )


@pytest.fixture
def update_me_data():
    name = random_lower_string(8)
    return UserUpdateMeRequest(
        password=generate_strong_password(),
        email=f"{name}@example.com",
        full_name=name,
        phone_number=generate_phone_number(),
    )


@pytest.fixture
def update_data():
    name = random_lower_string(8)
    return UserUpdateRequest(
        password=generate_strong_password(),
        email=f"{name}@example.com",
        full_name=name,
        phone_number=generate_phone_number(),
        is_active=True,
        role=UserRole.USER,
    )


@pytest_asyncio.fixture
async def existing_user(db_session, create_data):
    user = await User.create(
        db=db_session,
        username=create_data.username,
        phone_number=create_data.phone_number,
        full_name=create_data.full_name,
        email=create_data.email,
        hashed_password=hash_password(create_data.password),
        is_active=create_data.is_active,
        role=create_data.role.value,
    )
    yield user
    await user.delete(db=db_session)


async def test_create_user_success_and_already_exists(user_service, create_data, db_session):
    # Create user
    user = await user_service.create_user(create_data)
    assert user.username == create_data.username
    assert verify_password(create_data.password, user.hashed_password)

    # Create existing user
    with pytest.raises(UsernameEmailAlreadyExists):
        await user_service.create_user(create_data)

    await user.delete(db=db_session)

@pytest.mark.usefixtures("existing_user")
async def test_authenticate_success(user_service, create_data):
    # Authenticate
    user = await user_service.authenticate(
        username=create_data.username, password=create_data.password
    )
    assert user.full_name == create_data.full_name


async def test_authenticate_fail(user_service):
    with pytest.raises(InvalidLogin):
        await user_service.authenticate(username="fake_user", password="fake_password")


async def test_update_me(user_service, update_me_data, existing_user):
    old_hashed_password = existing_user.hashed_password
    updated_user = await user_service.update_me(
        update_me_data, current_user=existing_user
    )

    assert updated_user.hashed_password != old_hashed_password
    assert verify_password(update_me_data.password, updated_user.hashed_password)


async def test_update(user_service, update_data, existing_user):
    old_hashed_password = existing_user.hashed_password
    updated_user = await user_service.update(
        data=update_data, user_uuid=existing_user.uuid
    )

    assert updated_user.hashed_password != old_hashed_password
    assert verify_password(update_data.password, updated_user.hashed_password)


async def test_get_found(user_service, existing_user):
    user = await user_service.get(existing_user.uuid)
    assert user == existing_user


async def test_get_not_found(user_service):
    with pytest.raises(UserNotFound):
        await user_service.get(uuid.uuid4())


async def test_list(db_session, user_service):
    users = []
    number_of_user = random.randint(1, 9)
    for _ in range(number_of_user):
        name = random_lower_string(8)
        user = await User.create(
            db=db_session,
            username=name,
            full_name=name,
            email=f"{name}@gmail.com",
            hashed_password=hash_password(generate_strong_password())
        )
        users.append(user)

    params = UserListRequest(page=1, page_size=20)
    result = await user_service.list(params)
    assert len(result) == number_of_user
    assert result == users

    for user in users:
        await user.delete(db=db_session)


async def test_delete_success(user_service, existing_user, db_session):
    uuid = existing_user.uuid
    result = await user_service.delete(uuid)
    deleted_user = await User.find_by(db=db_session, uuid=uuid)

    assert result is True
    assert not deleted_user


async def test_delete_not_found(user_service):
    result = await user_service.delete(uuid.uuid4())
    assert result is False
