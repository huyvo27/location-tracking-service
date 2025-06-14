from math import ceil
import inflect
from datetime import datetime, timezone
from typing import Type, TypeVar, Optional

from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session

p = inflect.engine()
T = TypeVar("T", bound="BareBaseModel")


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
    def create(cls: Type[T], db: Session, **kwargs) -> T:
        instance = cls(**kwargs)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance

    @classmethod
    def find(cls: Type[T], db: Session, _id: int) -> Optional[T]:
        return db.query(cls).get(_id)

    @classmethod
    def all(cls: Type[T], db: Session):
        return db.query(cls)

    @classmethod
    def filter_by(cls: Type[T], db: Session, **kwargs):
        return db.query(cls).filter_by(**kwargs)

    def update(self, db: Session, **kwargs) -> T:
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

    def delete(self, db: Session):
        db.delete(self)
        db.commit()
