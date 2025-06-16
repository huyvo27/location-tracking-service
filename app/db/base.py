from functools import wraps
from math import ceil
import inflect
from datetime import datetime, timezone
from typing import Callable, Type, TypeVar, Optional

from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session
from .session import SessionLocal

p = inflect.engine()
T = TypeVar("T", bound="BareBaseModel")


def with_db_session(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(cls, *args, db: Optional[Session] = None, **kwargs) -> T:
        if db is None:
            with SessionLocal() as db:
                return func(cls, *args, db=db, **kwargs)
        return func(cls, *args, db=db, **kwargs)
    return wrapper


@as_declarative()
class Base:
    __abstract__ = True
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return p.plural(cls.__name__.lower())


class BareBaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    @classmethod
    @with_db_session
    def create(cls: Type[T], db: Optional[Session] = None, **kwargs) -> T:
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance

    @classmethod
    @with_db_session
    def find(cls: Type[T], _id: int, db: Optional[Session] = None) -> Optional[T]:
        return db.query(cls).get(_id)
    
    @classmethod
    @with_db_session
    def find_by(cls: Type[T], db: Optional[Session] = None, **kwargs) -> Optional[T]:
        return db.query(cls).filter_by(**kwargs).first()

    @classmethod
    @with_db_session
    def all(cls: Type[T], db: Optional[Session] = None):
        return db.query(cls)

    @classmethod
    @with_db_session
    def filter_by(cls: Type[T], db: Optional[Session] = None, **kwargs):
        return db.query(cls).filter_by(**kwargs)

    @with_db_session
    def update(self, db: Optional[Session] = None, **kwargs) -> T:
        for key, value in kwargs.items():
            if value is not None:
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    raise AttributeError(
                        f"{key} is not a valid attribute of {self.__class__.__name__}"
                    )
        db.commit()
        db.refresh(self)
        return self

    @with_db_session
    def delete(self, db: Optional[Session] = None):
        db.delete(self)
        db.commit()
