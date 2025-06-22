from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.base import BareBaseModel


class Membership(BareBaseModel):
    user_id = Column(
        Integer, ForeignKey("users.id"), primary_key=True, index=True, nullable=False
    )
    group_id = Column(
        Integer, ForeignKey("groups.id"), primary_key=True, index=True, nullable=False
    )
    joined_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")
