from requests import Session
from sqlalchemy import Column, String, Boolean, DateTime, or_

from app.db.base import BareBaseModel


class User(BareBaseModel):
    full_name = Column(String, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    role = Column(String, default="guest")
    last_login = Column(DateTime)
