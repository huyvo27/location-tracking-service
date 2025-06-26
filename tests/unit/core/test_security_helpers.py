from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core import security
from app.schemas.token import TokenData
from tests.config import settings
from tests.ultils import generate_strong_password


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch):
    monkeypatch.setattr("app.core.security.settings", settings)


@pytest.fixture
def password():
    return generate_strong_password()


@pytest.fixture
def hashed_password(password):
    return security.hash_password(password)


@pytest.fixture
def data():
    return {"sub": str(uuid.uuid4())}


def test_hash_and_verify_password(password, hashed_password):
    assert hashed_password != password
    assert security.verify_password(password, hashed_password)
    assert not security.verify_password("wrongpassword", hashed_password)


def test_create_access_token_and_decode(data):
    token = security.create_access_token(data)
    decoded = security.decode_access_token(token)
    assert isinstance(decoded, TokenData)
    assert decoded.sub == data["sub"]


def test_create_access_token_with_custom_expiry(data):
    expires = timedelta(seconds=10)
    token = security.create_access_token(data, expires_delta=expires)
    payload = jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.SECURITY_ALGORITHM]
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
    assert (exp - iat).total_seconds() == 10


def test_decode_access_token_expired(data):
    # Create token with expiry in the past
    expires = timedelta(seconds=-1)
    token = security.create_access_token(data, expires_delta=expires)
    with pytest.raises(HTTPException) as exc:
        security.decode_access_token(token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail


def test_decode_access_token_invalid():
    # Tamper with token
    token = "invalid.token.value"
    with pytest.raises(HTTPException) as exc:
        security.decode_access_token(token)
    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail
