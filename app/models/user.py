import uuid

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import ORMBase
from app.models.group import Group  # noqa: F401
from app.models.membership import Membership  # noqa: F401
from app.utils.enums import UserRole


class User(ORMBase):
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True
    )
    full_name = Column(String, index=True)
    username = Column(String(255), unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, index=True, nullable=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    role = Column(String, default=UserRole.USER.value)
    last_login = Column(DateTime)

    owned_groups = relationship(
        "Group", back_populates="owner", cascade="all, delete-orphan"
    )

    memberships = relationship(
        "Membership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    groups = relationship(
        "Group",
        secondary="memberships",
        back_populates="members",
        overlaps="group,user,memberships",
        lazy="selectin",
    )

    @property
    def uuid_str(self):
        return str(self.uuid)
