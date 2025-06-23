from typing import List, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.exceptions import UserNotFound
from app.models.user import User
from app.schemas.token import TokenData
from app.utils.enums import UserRole

oauth2_scheme = HTTPBearer(scheme_name="Authorization")


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
    except HTTPException as e:
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


# class PermissionRequired:
#     def __init__(
#         self,
#         allowed_roles: Union[str, UserRole, List[Union[str, UserRole]]],
#         *,
#         raise_error: bool = True,
#         log_access: bool = True,
#         enabled: bool = True,
#     ):
#         if isinstance(allowed_roles, (str, UserRole)):
#             self.allowed_roles = [allowed_roles]
#         else:
#             self.allowed_roles = [str(role) for role in allowed_roles]

#         self.raise_error = raise_error
#         self.log_access = log_access
#         self.enabled = enabled

#     async def __call__(
#         self,
#         user: User = Depends(get_current_user),
#     ) -> User:

#         if self.enabled and str(user.role) not in self.allowed_roles:
#             if self.raise_error:
#                 raise HTTPException(
#                     status_code=status.HTTP_403_FORBIDDEN,
#                     detail=f"Permission denied.",
#                 )
#             return None

#         if self.log_access:
#             logger.info(f"[ACCESS] {user.username} accessed with role: {user.role}")

#         return user
