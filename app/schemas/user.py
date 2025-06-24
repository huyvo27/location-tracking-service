from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, field_validator, ValidationError

from app.utils.enums import UserRole
from app.utils.pagination import PaginationParams

from .base import BaseSchema


class UserBase(BaseSchema):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, pattern=r"^(\+?\d{10,15}|0\d{9,10})$")


class UserUpdateMeRequest(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password must be at least 8 characters long, contain uppercase, lowercase, number, and special character",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        import re
        if (len(v) < 8 or
            not re.search(r"[A-Z]", v) or
            not re.search(r"[a-z]", v) or
            not re.search(r"\d", v) or
            not re.search(r"[@$!%*?&]", v)):
            raise ValueError("Password must be at least 8 characters long, contain uppercase, lowercase, number, and special character")
        return v


class UserRegisterRequest(UserUpdateMeRequest):
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Username must be alphanumeric and between 3 to 20 characters long",
    )


class UserCreateRequest(UserRegisterRequest):
    role: UserRole = Field(UserRole.USER, description="User role, default is USER")
    is_active: bool = Field(True, description="Indicates if the user is active or not")


class UserUpdateRequest(UserUpdateMeRequest):
    role: UserRole = Field(UserRole.USER, description="User role, default is USER")
    is_active: bool = Field(True, description="Indicates if the user is active or not")


class UserResponse(UserBase):
    uuid: UUID
    username: str
    phone_number: Optional[str] = None
    role: UserRole
    is_active: bool
    last_login: Optional[datetime] = None


class UserLimitedResponse(BaseSchema):
    uuid: UUID
    full_name: Optional[str] = None
    is_active: bool


class UserListRequest(PaginationParams):
    search: Optional[str] = Field(
        None, description="Search by name, username, or email"
    )
