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
        """Create a new record in the database.
        Args:
            db (AsyncSession): Database session.
            **kwargs: Fields to set on the new record as keyword arguments.
        Returns:
            T: Created instance of the model.
        Example:
            await Model.create(db=db, name="John Doe", age=30)
        """
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
        """Find a record by its primary key.
        Args:
            _id (int): Primary key of the record.
            db (AsyncSession): Database session.
        Returns:
            Optional[T]: Found record or None.
        Example:
            await Model.find(db=db, _id=1)
        """
        result = await db.get(cls, _id)
        return result

    @classmethod
    @with_async_db_session
    async def find_by(
        cls: Type[T], db: Optional[AsyncSession] = None, use_or: bool = False, **kwargs
    ) -> Optional[T]:
        """Find a record by given criteria.
        Args:
            db (AsyncSession): Database session.
            use_or (bool): If True, use OR condition for multiple criteria.
            **kwargs: Filter criteria as keyword arguments.
        Returns:
            Optional[T]: Found record or None.
        Example:
            await Model.find_by(db=db, username="john", email="join@example.com", use_or=True)
        """
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
        """Get all records of the model.
        Args:
            db (AsyncSession): Database session.
        Returns:
            List[T]: List of all records of the model.
        Example:
            await Model.all(db=db)
        """

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
        """Filter records by given criteria.
        Args:
            db (AsyncSession): Database session.
            contains (dict): Dictionary of fields to search for partial matches.
            offset (int): Offset for pagination.
            limit (int): Limit for pagination.
            case_insensitive (bool): Whether to perform case-insensitive search.
            as_stmt (bool): If True, return SQLAlchemy statement instead of results.
            **kwargs: Additional filter criteria.\n
                {attribute_name}__in (list): Filter by a list of values for the attribute.\n
                attribute_name (any): Filter by exact match for the attribute.
        Returns:
            List[T] or SQLAlchemy statement: Filtered records or SQLAlchemy statement.
        Example:
           await Model.filter_by(db=db, department__in=["HR", "IT"], contains={"name": "john"})
        """
        stmt = select(cls)
        filters = []
        for key, value in kwargs.items():
            if key.endswith("__in"):
                field = key[:-4]
                if not hasattr(cls, field):
                    raise AttributeError(f"Invalid field: {field}")
                column = getattr(cls, field)
                filters.append(column.in_(value))
            else:
                if not hasattr(cls, key):
                    raise AttributeError(f"Invalid field: {key}")
                column = getattr(cls, key)
                filters.append(column == value)

        if contains:
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
        """Update the current instance with new values.
        Args:
            db (AsyncSession): Database session.
            **kwargs: Fields to update as keyword arguments.
        Returns:
            T: Updated instance.
        Example:
            await instance.update(db=db, name="New Name", age=30)
        """
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
        """Delete the current instance from the database.
        Args:
            db (AsyncSession): Database session.
        Example:
            await instance.delete(db=db)
        """
        await db.delete(self)
        await db.commit()
