from datetime import datetime
from uuid import uuid4

import pytest

from app.schemas.user import (
    UserCreateRequest,
    UserLimitedResponse,
    UserListRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateMeRequest,
)
from app.utils.enums import UserRole


def test_user_update_me_request_valid():
    req = UserUpdateMeRequest(
        full_name="John Doe",
        email="john@example.com",
        phone_number="+84912345678",
        password="StrongP@ssw0rd",
    )
    assert req.full_name == "John Doe"
    assert req.email == "john@example.com"


@pytest.mark.parametrize(
    "password",
    ["short", "nocaps123!", "NOLOWERCASE123!", "NoSpecial123", "NoNumber!@#"],
)
def test_user_update_me_request_invalid_password(password):
    with pytest.raises(ValueError):
        UserUpdateMeRequest(
            full_name="Jane",
            email="jane@example.com",
            phone_number="0912345678",
            password=password,
        )


def test_user_register_request_username_constraints():
    # Valid username
    req = UserRegisterRequest(
        full_name="Jane",
        email="jane@example.com",
        phone_number="0912345678",
        password="StrongP@ssw0rd",
        username="user_123",
    )
    assert req.username == "user_123"

    # Invalid username
    with pytest.raises(ValueError):
        UserRegisterRequest(
            full_name="Jane",
            email="jane@example.com",
            phone_number="0912345678",
            password="StrongP@ssw0rd",
            username="invalid username!",
        )


def test_user_create_request_defaults():
    req = UserCreateRequest(
        full_name="Jane",
        email="jane@example.com",
        phone_number="0912345678",
        password="StrongP@ssw0rd",
        username="user123",
    )
    assert req.role == UserRole.USER
    assert req.is_active is True


def test_user_response_fields():
    resp = UserResponse(
        uuid=uuid4(),
        username="user123",
        full_name="Jane",
        email="jane@example.com",
        phone_number="0912345678",
        role=UserRole.USER,
        is_active=True,
        last_login=datetime.utcnow(),
    )
    assert resp.username == "user123"
    assert resp.is_active


def test_user_limited_response_fields():
    resp = UserLimitedResponse(uuid=uuid4(), full_name="Jane", is_active=True)
    assert resp.is_active


def test_user_list_request_search():
    req = UserListRequest(page=1, page_size=10, search="john")
    assert req.search == "john"
