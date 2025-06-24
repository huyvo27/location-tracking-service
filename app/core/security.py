from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.schemas.token import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with an expiration time.
    If expires_delta is not provided, it defaults to the configured access token expiration time.
    Args:
        data (dict): Data to encode in the token.
        expires_delta (Optional[timedelta]): Optional expiration time for the token.
    Returns:
        str: Encoded JWT token.
    """
    to_encode = data.copy()
    iat = datetime.now(timezone.utc)
    expire = iat + (
        expires_delta or timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    )
    to_encode.update({"exp": expire, "iat": iat})
    return jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.SECURITY_ALGORITHM
    )


def decode_access_token(token: str):
    """Decode a JWT access token and return the payload.
    Args:
        token (str): The JWT token to decode.
    Returns:
        TokenData: Decoded token data.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.SECURITY_ALGORITHM]
        )
        return TokenData(**payload)

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
