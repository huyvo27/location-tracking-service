from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.schemas.base import BaseSchema, datetime_to_gmt_str


class DummyObj:
    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at


class DummySchema(BaseSchema):
    id: int
    created_at: datetime


def test_datetime_to_gmt_str_with_tzinfo():
    dt = datetime(2024, 6, 1, 12, 30, 45, tzinfo=ZoneInfo("UTC"))
    result = datetime_to_gmt_str(dt)
    assert result == "2024-06-01T12:30:45+0000"


def test_datetime_to_gmt_str_without_tzinfo():
    dt = datetime(2024, 6, 1, 12, 30, 45)
    result = datetime_to_gmt_str(dt)
    assert result == "2024-06-01T12:30:45+0000"


def test_datetime_to_gmt_str_with_non_utc_tz():
    dt = datetime(2024, 6, 1, 15, 30, 45, tzinfo=ZoneInfo("Asia/Bangkok"))
    result = datetime_to_gmt_str(dt)
    # Asia/Bangkok is UTC+7
    assert result == "2024-06-01T15:30:45+0700"


def test_base_schema_from_obj():
    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    obj = DummyObj(id=1, created_at=dt)
    schema = DummySchema.from_obj(obj)
    assert schema.id == 1
    assert schema.created_at == dt


def test_base_schema_serializable_dict():
    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    schema = DummySchema(id=2, created_at=dt)
    result = schema.serializable_dict()
    assert result["id"] == 2
    assert result["created_at"] == "2024-06-01T12:00:00+00:00"


def test_base_schema_serializable_dict_with_kwargs():
    dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    schema = DummySchema(id=3, created_at=dt)
    result = schema.serializable_dict(by_alias=True)
    assert result["id"] == 3
    assert result["created_at"] == "2024-06-01T12:00:00+00:00"
