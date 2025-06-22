from typing import Any, Generic, Sequence, Type, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=1000)


class Metadata(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedData(BaseModel, Generic[T]):
    items: Sequence[T]
    metadata: Metadata


async def paginate(
    session: AsyncSession,
    stmt: Any,
    params: PaginationParams,
    schema: Type[BaseModel],
) -> PaginatedData:

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    paginated_stmt = stmt.offset((params.page - 1) * params.page_size).limit(
        params.page_size
    )
    result = await session.execute(paginated_stmt)
    items = result.scalars().all()

    metadata = Metadata(
        page=params.page,
        page_size=params.page_size,
        total_items=total,
        total_pages=(total + params.page_size - 1) // params.page_size,
    )

    return PaginatedData[schema](items=items, metadata=metadata)
