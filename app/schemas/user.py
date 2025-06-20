from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.utils.enums import UserRole


class UserBase(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    is_active: bool = True

    model_config = ConfigDict(
        from_attributes=True
    )


class UserCreateRequest(UserBase):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$", description="Username must be alphanumeric and between 3 to 20 characters long")
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.USER


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class UserUpdateMeRequest(UserUpdateRequest):
    is_active: Optional[bool] = Field(None, exclude=True)
    role: Optional[UserRole] = Field(None, exclude=True)


class UserResponse(UserBase):
    uuid: UUID
    username: str
    email: EmailStr
    role: UserRole
    last_login: Optional[datetime] = None
