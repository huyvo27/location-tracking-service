from pydantic import BaseModel

from app.schemas.response import PaginatedResponse, Response
from app.utils.pagination import PaginatedData


class DummySchema(BaseModel):
    id: int
    name: str


def test_response_success():
    data = DummySchema(id=1, name="Alice")
    resp = Response[DummySchema].success(data=data)
    assert resp.code == "000"
    assert resp.message == "Success"
    assert resp.data == data


def test_response_error():
    resp = Response[DummySchema].error(code="404", message="Not found")
    assert resp.code == "404"
    assert resp.message == "Not found"
    assert resp.data is None


def test_paginated_response_success():
    data = DummySchema(id=1, name="Alice")
    paginated = PaginatedData[DummySchema](
        items=[data],
        metadata={"page": 1, "page_size": 10, "total_items": 1, "total_pages": 1},
    )
    resp = PaginatedResponse[DummySchema].success(data=paginated)
    assert resp.code == "000"
    assert resp.message == "Success"
    assert resp.data == paginated
