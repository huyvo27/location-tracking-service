import uuid

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import ORMBase


class Group(ORMBase):
    uuid = Column(
        UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True
    )
    name = Column(String(255), index=True, unique=True, nullable=False)
    description = Column(String(1024), nullable=True)
    hashed_key = Column(String(255))
    capacity = Column(Integer, default=10)
    member_count = Column(Integer, default=1)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    owner = relationship("User", back_populates="owned_groups")

    memberships = relationship(
        "Membership",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    members = relationship(
        "User",
        secondary="memberships",
        back_populates="groups",
        overlaps="user,group,memberships",
        lazy="selectin",
    )

    @property
    def owner_uuid(self) -> UUID:
        """
        Returns the UUID of the group owner.
        """
        return self.owner.uuid if self.owner else None
