from functools import wraps
import inflect
from datetime import datetime, timezone
from typing import Callable, Type, TypeVar, Optional

from sqlalchemy import Column, Integer, DateTime, select
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.ext.asyncio import AsyncSession
from .session import AsyncSessionLocal

p = inflect.engine()
T = TypeVar("T", bound="BareBaseModel")


def with_async_db_session(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(cls_or_self, *args, db: Optional[AsyncSession] = None, **kwargs):
        if db is None:
            async with AsyncSessionLocal() as db:
                return await func(cls_or_self, *args, db=db, **kwargs)
        return await func(cls_or_self, *args, db=db, **kwargs)
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
    @with_async_db_session
    async def create(cls: Type[T], db: Optional[AsyncSession] = None, **kwargs) -> T:
        instance = cls(**kwargs)
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        return instance

    @classmethod
    @with_async_db_session
    async def find(cls: Type[T], _id: int, db: Optional[AsyncSession] = None) -> Optional[T]:
        result = await db.get(cls, _id)
        return result

    @classmethod
    @with_async_db_session
    async def find_by(cls: Type[T], db: Optional[AsyncSession] = None, **kwargs) -> Optional[T]:
        stmt = select(cls).filter_by(**kwargs)
        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    @with_async_db_session
    async def all(cls: Type[T], db: Optional[AsyncSession] = None, ):
        result = await db.execute(select(cls))
        return result.scalars().all()

    @classmethod
    @with_async_db_session
    async def filter_by(cls: Type[T], db: Optional[AsyncSession] = None, **kwargs):
        stmt = select(cls).filter_by(**kwargs)
        result = await db.execute(stmt)
        return result.scalars().all()

    @with_async_db_session
    async def update(self, db: Optional[AsyncSession] = None, **kwargs) -> T:
        for key, value in kwargs.items():
            if value is not None:
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    raise AttributeError(
                        f"{key} is not a valid attribute of {self.__class__.__name__}"
                    )
        await db.commit()
        await db.refresh(self)
        return self

    @with_async_db_session
    async def delete(self, db: Optional[AsyncSession] = None):
        await db.delete(self)
        await db.commit()