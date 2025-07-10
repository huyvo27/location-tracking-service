from datetime import datetime, timezone
from functools import wraps
from typing import Callable, Optional, Type, TypeVar

import inflect
from sqlalchemy import Column, DateTime, Integer, String, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, as_declarative, declared_attr

from app.exceptions.base import DatabaseError

p = inflect.engine()
T = TypeVar("T", bound="ORMBase")


def with_async_db_session(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(cls_or_self, *args, db: Optional[AsyncSession] = None, **kwargs):
        try:
            if db is None:
                from .session import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    return await func(cls_or_self, *args, db=db, **kwargs)
            return await func(cls_or_self, *args, db=db, **kwargs)
        except Exception as e:
            raise DatabaseError(f"Operation failed: {str(e)}")

    return wrapper


@as_declarative()
class Base:
    __abstract__ = True
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return p.plural(cls.__name__.lower())

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"

    __mapper_args__ = {"confirm_deleted_rows": False}


class CRUDMixin:
    @classmethod
    def _field_validation(cls, field: str) -> None:
        """Validate if the field exists in the model."""
        if not hasattr(cls, field):
            raise AttributeError(f"Invalid field: {field}")

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
    async def initialize(
        cls: Type[T], db: Optional[AsyncSession] = None, **kwargs
    ) -> T:
        """Initialize a new record in the database without committing the transaction.
        Args:
            db (AsyncSession): Database session.
            **kwargs: Fields to set on the new record as keyword arguments.
        Returns:
            T: Initialized instance of the model.
        Example:
            await Model.initialize(db=db, name="John Doe", age=30)
        """
        instance = cls(**kwargs)
        db.add(instance)
        await db.flush()
        return instance

    @classmethod
    @with_async_db_session
    async def find(
        cls: Type[T], _id: int, db: Optional[AsyncSession] = None
    ) -> Optional[T]:
        """Find a record by its primary key ID.
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
            await Model.find_by(
                                db=db,
                                username="john",
                                email="join@example.com",
                                use_or=True
                            )
        """
        stmt = select(cls)
        filters = []
        for key, value in kwargs.items():
            cls._field_validation(key)
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
        limit: int = 1000,
        offset: int = 0,
        order_by: InstrumentedAttribute = None,
        order_desc: bool = False,
        as_stmt: bool = False,
    ):
        """Get all records from the model.
        Args:
            db (AsyncSession): Database session.
            limit (int): Maximum number of records to return.
            offset (int): Offset for pagination.
            order_by (InstrumentedAttribute): Column to order by.
            order_desc (bool): If True, order by descending.
            as_stmt (bool): If True, return SQLAlchemy statement instead of results.
        Returns:
            List[T] or SQLAlchemy statement: List of records or SQLAlchemy statement.
        Example:
            await Model.all(
                            db=db,
                            limit=10,
                            offset=0,
                            order_by=Model.created_at,
                            order_desc=True
                        )
        """
        stmt = select(cls)

        if order_by:
            if order_desc:
                stmt = stmt.order_by(order_by.desc())
            else:
                stmt = stmt.order_by(order_by)

        if as_stmt:
            return stmt

        stmt = stmt.offset(offset).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @classmethod
    @with_async_db_session
    async def filter_by(
        cls: Type[T],
        db: Optional[AsyncSession] = None,
        contains: dict = None,
        offset: int = 0,
        limit: int = 100,
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
                {attribute_name}__in (list): Filter by a list of values
                for the attribute.\n
                attribute_name (any): Filter by exact match for the attribute.
        Returns:
            List[T] or SQLAlchemy statement: Filtered records or SQLAlchemy statement.
        Example:
            await Model.filter_by(
                                    db=db,
                                    department__in=["HR", "IT"],
                                    contains={"name": "john"}
                                )
        """
        stmt = select(cls)
        filters = []
        for key, value in kwargs.items():
            if key.endswith("__in"):
                field = key[:-4]
                cls._field_validation(field)
                column = getattr(cls, field)
                filters.append(column.in_(value))
            else:
                cls._field_validation(key)
                column = getattr(cls, key)
                filters.append(column == value)

        if contains:
            for key, value in contains.items():
                cls._field_validation(key)
                column = getattr(cls, key)
                if not isinstance(column.type, String):
                    continue
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
                self._field_validation(key)
                setattr(self, key, value)
        await db.commit()
        await db.refresh(self)
        return self

    @with_async_db_session
    async def save(self, db: Optional[AsyncSession] = None) -> T:
        """Save the current instance to the database.
        Args:
            db (AsyncSession): Database session.
        Returns:
            T: Saved instance.
        Example:
            await instance.save(db=db)
        """
        db.add(self)
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

    @classmethod
    @with_async_db_session
    async def exists(cls, db: Optional[AsyncSession] = None, **kwargs) -> bool:
        """
        Check if a record exists based on the given criteria.

        Args:
            db (AsyncSession): Optional DB session.
            **kwargs: Filter criteria.

        Returns:
            bool: True if at least one record exists, False otherwise.
        """
        result = await cls.find_by(db=db, **kwargs)
        return result is not None


class ORMBase(Base, CRUDMixin):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
