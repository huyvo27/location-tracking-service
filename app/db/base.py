from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Optional, Type, TypeVar

import inflect
from sqlalchemy import Column, DateTime, Integer, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from app.exceptions.base import DatabaseError

from .session import AsyncSessionLocal

p = inflect.engine()
T = TypeVar("T", bound="BareBaseModel")


def with_async_db_session(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(cls_or_self, *args, db: Optional[AsyncSession] = None, **kwargs):
        try:
            if db is None:
                async with AsyncSessionLocal() as db:
                    return await func(cls_or_self, *args, db=db, **kwargs)
            return await func(cls_or_self, *args, db=db, **kwargs)
        except Exception as e:
            raise DatabaseError(f"Query failed: {str(e)}")

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
    async def find(
        cls: Type[T], _id: int, db: Optional[AsyncSession] = None
    ) -> Optional[T]:
        result = await db.get(cls, _id)
        return result

    @classmethod
    @with_async_db_session
    async def find_by(
        cls: Type[T], db: Optional[AsyncSession] = None, use_or: bool = False, **kwargs
    ) -> Optional[T]:
        stmt = select(cls)
        filters = []
        for key, value in kwargs.items():
            if not hasattr(cls, key):
                raise AttributeError(f"Invalid field: {key}")
            column = getattr(cls, key)
            filters.append(column == value)

        if filters:
            if use_or:
                stmt = stmt.where(or_(*filters))
            else:
                stmt = stmt.where(*filters)

        result = await db.execute(stmt)
        return result.scalars().first()

    @classmethod
    @with_async_db_session
    async def all(
        cls: Type[T],
        db: Optional[AsyncSession] = None,
    ):
        result = await db.execute(select(cls))
        return result.scalars().all()

    @classmethod
    @with_async_db_session
    async def filter_by(
        cls: Type[T],
        db: Optional[AsyncSession] = None,
        contains: dict = None,
        offset: int = 0,
        limit: int = 50,
        case_insensitive: bool = True,
        as_stmt: bool = False,
        **kwargs,
    ):
        stmt = select(cls).filter_by(**kwargs)

        if contains:
            filters = []
            for key, value in contains.items():
                if not hasattr(cls, key):
                    raise AttributeError(f"Invalid field: {key}")
                column = getattr(cls, key)
                if case_insensitive:
                    filters.append(column.ilike(f"%{value}%"))
                else:
                    filters.append(column.like(f"%{value}%"))
                stmt = stmt.where(*filters)
        if as_stmt:
            return stmt

        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @with_async_db_session
    async def update(self, db: Optional[AsyncSession] = None, **kwargs) -> T:
        for key, value in kwargs.items():
            if value is not None:
                if hasattr(self, key):
                    setattr(self, key, value)
                else:
                    raise AttributeError(f"Invalid field: {key}")
        await db.commit()
        await db.refresh(self)
        return self

    @with_async_db_session
    async def delete(self, db: Optional[AsyncSession] = None):
        await db.delete(self)
        await db.commit()
