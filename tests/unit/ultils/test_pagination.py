import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

from app.utils.pagination import PaginatedData, PaginationParams, paginate

Base = declarative_base()


class DummyModel(Base):
    __tablename__ = "dummy"
    id = Column(Integer, primary_key=True)
    name = Column(String)


class DummySchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


@pytest.fixture
def dummy_rows():
    return [DummyModel(id=i, name=f"user_{i}") for i in range(1, 21)]


@pytest.fixture
def dummy_schema():
    return DummySchema


@pytest.fixture
def pagination_params():
    return PaginationParams(page=2, page_size=5)


@pytest.mark.asyncio
async def test_paginate_returns_correct_metadata_and_items(
    mocker, dummy_rows, dummy_schema, pagination_params
):
    db = mocker.Mock(spec=AsyncSession)
    stmt = select(DummyModel)
    total_result = mocker.Mock()
    total_result.scalar_one.return_value = len(dummy_rows)
    paginated_result = mocker.Mock()
    paginated_result.scalars.return_value.all.return_value = dummy_rows[5:10]
    db.execute.side_effect = [total_result, paginated_result]

    result = await paginate(db, stmt, pagination_params, dummy_schema)
    assert isinstance(result, PaginatedData)
    assert result.metadata.page == 2
    assert result.metadata.page_size == 5
    assert result.metadata.total_items == 20
    assert result.metadata.total_pages == 4
    assert len(result.items) == 5


@pytest.mark.asyncio
async def test_paginate_empty_result(mocker, dummy_schema):
    db = mocker.Mock(spec=AsyncSession)
    stmt = select(DummyModel)
    total_result = mocker.Mock()
    total_result.scalar_one.return_value = 0
    paginated_result = mocker.Mock()
    paginated_result.scalars.return_value.all.return_value = []
    db.execute.side_effect = [total_result, paginated_result]

    params = PaginationParams(page=1, page_size=10)
    result = await paginate(db, stmt, params, dummy_schema)
    assert result.metadata.total_items == 0
    assert result.metadata.total_pages == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_paginate_last_page_partial(mocker, dummy_rows, dummy_schema):
    db = mocker.Mock(spec=AsyncSession)
    stmt = select(DummyModel)
    total_result = mocker.Mock()
    total_result.scalar_one.return_value = len(dummy_rows)
    paginated_result = mocker.Mock()
    paginated_result.scalars.return_value.all.return_value = dummy_rows[15:20]
    db.execute.side_effect = [total_result, paginated_result]

    params = PaginationParams(page=4, page_size=5)
    result = await paginate(db, stmt, params, dummy_schema)
    assert result.metadata.page == 4
    assert result.metadata.page_size == 5
    assert result.metadata.total_items == 20
    assert result.metadata.total_pages == 4
    assert len(result.items) == 5
