from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.exceptions import UserNotFound
from app.models.user import User
from app.schemas.token import TokenData

oauth2_scheme = HTTPBearer(scheme_name="Authorization", auto_error=False)


async def get_token_data(
    http_authorization_credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
) -> TokenData:
    """
    Decode JWT token and return the token data.
    """
    try:
        return decode_access_token(http_authorization_credentials.credentials)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )


async def get_current_user(
    token_data: TokenData = Depends(get_token_data),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode JWT token and return the current user from DB
    """
    user = await User.find_by(db=db, uuid=token_data.sub)
    if not user:
        raise UserNotFound()

    return user


async def login_required(current_user: User = Depends(get_current_user)):
    return current_user


def permission_required(*roles):
    async def wrapper(user: User = Depends(get_current_user)):
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Permission Denied")
        return user

    return Depends(wrapper)
