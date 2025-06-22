from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import BaseSchema


class GroupBase(BaseSchema):
    name: Optional[str] = Field(
        None, max_length=60, min_length=6, pattern=r"^[a-zA-Z0-9_]+$"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Group description"
    )
    capacity: Optional[int] = Field(10, ge=1, le=100)


class GroupCreateRequest(GroupBase):
    name: str = Field(..., description="Group name, alphanumeric, 6-60 chars")
    key: str = Field(
        ..., min_length=8, max_length=128, description="Secret key for joining"
    )


class GroupJoinRequest(BaseSchema):
    group_uuid: UUID = Field(..., description="UUID of the group to join")
    key: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Secret key for joining the group",
    )


class GroupUpdateLocationRequest(BaseSchema):
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in degrees"
    )
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees")
    timestamp: datetime = Field(..., description="Timestamp in ISO 8601 format")


class GroupResponse(GroupBase):
    uuid: UUID
    name: str
    owner_uuid: UUID
    member_count: int = Field(..., ge=0)
    capacity: int
    created_at: datetime
    updated_at: datetime
