from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer
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

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")

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

    @classmethod
    async def add_membership(cls, db, user_id, group_id):
        existing_membership = await cls.find_by(
            db=db, user_id=user_id, group_id=group_id
        )
        if existing_membership:
            print(
                f"Membership for user_id={user_id}, group_id={group_id} already exists"
            )
            return existing_membership

        membership = await cls.create(db=db, user_id=user_id, group_id=group_id)
        return membership
