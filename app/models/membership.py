from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base, CRUDMixin


class Membership(Base, CRUDMixin):
    user_id = Column(
        Integer, ForeignKey("users.id"), primary_key=True, index=True, nullable=False
    )
    group_id = Column(
        Integer, ForeignKey("groups.id"), primary_key=True, index=True, nullable=False
    )
    joined_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="memberships", lazy="selectin")
    group = relationship("Group", back_populates="memberships", lazy="selectin")

    @property
    def user_uuid(self):
        """
        Returns the UUID of the user in this membership.
        """
        return self.user.uuid if self.user else None

    @property
    def user_full_name(self):
        """
        Returns the full name of the user in this membership.
        """
        return self.user.full_name if self.user else None

    @property
    def group_uuid(self):
        """
        Returns the UUID of the group in this membership.
        """
        return self.group.uuid if self.group else None
