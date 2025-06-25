import pytest
from fastapi import HTTPException, status

from app.dependencies.auth import (
    get_current_user,
    get_token_data,
    login_required,
    permission_required,
)
from app.models.user import User
from app.schemas.token import TokenData

pytestmark = pytest.mark.asyncio


class DummyCreds:
    def __init__(self, credentials):
        self.credentials = credentials


async def test_get_token_data_valid(mocker):
    mocker.patch(
        "app.dependencies.auth.decode_access_token",
        return_value=TokenData(sub="user-uuid"),
    )
    creds = DummyCreds("validtoken")
    result = await get_token_data(http_authorization_credentials=creds)
    assert isinstance(result, TokenData)
    assert result.sub == "user-uuid"


async def test_get_token_data_invalid(mocker):
    def raise_exc(token):
        raise HTTPException(status_code=401)

    mocker.patch("app.dependencies.auth.decode_access_token", side_effect=raise_exc)
    creds = DummyCreds("invalidtoken")
    with pytest.raises(HTTPException) as exc:
        await get_token_data(http_authorization_credentials=creds)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_current_user_found(mocker):
    dummy_user = User()
    dummy_user.role = "user"
    mocker.patch("app.models.user.User.find_by", return_value=dummy_user)
    token_data = TokenData(sub="user-uuid")
    db = object()
    result = await get_current_user(token_data=token_data, db=db)
    assert result is dummy_user


async def test_get_current_user_not_found(mocker):
    mocker.patch("app.models.user.User.find_by", return_value=None)
    token_data = TokenData(sub="user-uuid")
    db = object()
    with pytest.raises(Exception):
        await get_current_user(token_data=token_data, db=db)


async def test_login_required():
    dummy_user = User()
    dummy_user.role = "user"
    result = await login_required(current_user=dummy_user)
    assert result is dummy_user


async def test_permission_required_allowed():
    dummy_user = User()
    dummy_user.role = "admin"
    dep = permission_required("admin")
    wrapper = dep.dependency
    result = await wrapper(user=dummy_user)
    assert result is dummy_user


async def test_permission_required_denied():
    dummy_user = User()
    dummy_user.role = "user"
    dep = permission_required("admin")
    wrapper = dep.dependency
    with pytest.raises(HTTPException) as exc:
        await wrapper(user=dummy_user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Permission Denied"
