from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, model_serializer

from app.utils.pagination import PaginationParams

from .base import BaseSchema


class GroupCreateRequest(BaseSchema):
    name: Optional[str] = Field(
        None,
        max_length=60,
        min_length=6,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Group name, alphanumeric, 6-60 chars",
    )
    key: str = Field(
        ..., min_length=8, max_length=128, description="Secret key for joining"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Group description"
    )
    capacity: Optional[int] = Field(10, ge=1, le=100)


class GroupListRequest(PaginationParams):
    search: Optional[str] = Field(
        None, description="Search by group name or description"
    )


class GroupJoinRequest(BaseSchema):
    key: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Secret key for joining the group",
    )


class MyGroupListRequest(GroupListRequest):
    """
    Request schema for listing groups that the user belongs to.
    Inherits from PaginationParams for pagination support.
    """

    only_owned: Optional[bool] = Field(
        False,
        description="If true, only groups owned by the user are returned. "
        "Defaults to false.",
    )


class KickMemberRequest(BaseSchema):
    member_uuid: UUID = Field(
        ..., description="UUID of the user to be kicked from the group"
    )


class GroupUpdateRequest(BaseSchema):
    key: Optional[str] = Field(
        None,
        min_length=8,
        max_length=128,
        description="New secret key for the group (optional, if not provided, "
        "the existing key remains unchanged)",
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Group description"
    )
    capacity: Optional[int] = Field(10, ge=1, le=100)


class GroupUpdateLocationRequest(BaseSchema):
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitude in degrees"
    )
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees")
    timestamp: datetime = Field(..., description="Timestamp in ISO 8601 format")


class SimpleGroupResponse(BaseSchema):
    name: str
    uuid: UUID
    description: Optional[str] = None


class MemberResponse(BaseSchema):
    user_uuid: UUID
    user_full_name: Optional[str] = None
    joined_at: datetime

    @model_serializer()
    def serialize(self):
        return {
            "uuid": str(self.user_uuid),
            "name": self.user_full_name,
            "joined_at": self.joined_at.isoformat(),
        }


class GroupDetailResponse(SimpleGroupResponse):
    owner_uuid: Optional[UUID]
    member_count: int = Field(..., ge=0)
    capacity: int = Field(..., ge=1, le=100)
    created_at: datetime
    updated_at: datetime
    memberships: Optional[list[MemberResponse]]

    @model_serializer()
    def serialize(self):
        return {
            "name": self.name,
            "uuid": str(self.uuid),
            "description": self.description,
            "owner": str(self.owner_uuid) if self.owner_uuid else None,
            "member_count": self.member_count,
            "capacity": self.capacity,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "members": (
                [member.serialize() for member in self.memberships]
                if self.memberships
                else []
            ),
        }


class MembershipResponse(BaseSchema):
    user_uuid: UUID
    group_uuid: UUID
    joined_at: datetime
