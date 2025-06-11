from typing import Generic, Sequence, Type, TypeVar
from fastapi import Query
from pydantic import BaseModel, Field

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


def paginate(
    query: Query, params: PaginationParams, schema: Type[BaseModel]
) -> PaginatedData:
    total = query.count()
    items = (
        query.offset((params.page - 1) * params.page_size).limit(params.page_size).all()
    )

    metadata = Metadata(
        page=params.page,
        page_size=params.page_size,
        total_items=total,
        total_pages=(total + params.page_size - 1) // params.page_size,
    )

    return PaginatedData[schema](items=items, metadata=metadata)
