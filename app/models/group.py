from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import BareBaseModel


class Group(BareBaseModel):
    name = Column(String(255), index=True, unique=True, nullable=False)
    key = Column(String(255))
    capacity = Column(Integer, default=10)
    owner_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    owner = relationship("User", back_populates="owned_groups")

    memberships = relationship("Membership", back_populates="group", cascade="all, delete-orphan")

    members = relationship(
    "User",
    secondary="memberships",
    back_populates="groups",
    overlaps="user,group,memberships",
    lazy="selectin"
)
