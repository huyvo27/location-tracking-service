from typing import List, Union
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
    OAuth2PasswordBearer,
)
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.models.user import User
from app.schemas.token import TokenData
from app.utils.enums import UserRole

oauth2_scheme = HTTPBearer(scheme_name="Authorization")


def get_current_user(
    http_authorization_credentials: HTTPAuthorizationCredentials = Depends(
        oauth2_scheme
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode JWT token and return the current user from DB
    """
    try:
        token_data: TokenData = decode_access_token(
            http_authorization_credentials.credentials
        )
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = User.find(db, token_data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def login_required(current_user: User = Depends(get_current_user)):
    return current_user


def permission_required(*roles):
    def wrapper(user: User = Depends(get_current_user)):
        if roles and user.role not in roles:
            raise HTTPException(status_code=403, detail="Permission Denied")
        return user

    return Depends(wrapper)


class PermissionRequired:
    def __init__(
        self,
        allowed_roles: Union[str, UserRole, List[Union[str, UserRole]]],
        *,
        raise_error: bool = True,
        log_access: bool = True,
        enabled: bool = True,
    ):
        if isinstance(allowed_roles, (str, UserRole)):
            self.allowed_roles = [allowed_roles]
        else:
            self.allowed_roles = [str(role) for role in allowed_roles]

        self.raise_error = raise_error
        self.log_access = log_access
        self.enabled = enabled

    def __call__(
        self,
        user: User = Depends(get_current_user),
    ) -> User:

        if self.enabled and str(user.role) not in self.allowed_roles:
            if self.raise_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied.",
                )
            return None

        if self.log_access:
            print(f"[ACCESS] {user.username} accessed with role: {user.role}")

        return user
