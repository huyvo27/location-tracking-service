import random

import pytest
from sqlalchemy import Column, String

from app.db.base import ORMBase

pytestmark = pytest.mark.asyncio


class DummyModel(ORMBase):
    __tablename__ = "dummymodels"
    name = Column(String)


def random_id():
    return random.randint(1, 20)


async def test_create(db_session):
    dummies = []
    for id in range(1, 21):
        ins = await DummyModel.create(db=db_session, name=f"dummy_{id}")
        dummies.append(ins)
    id = random_id()
    assert dummies[id - 1].id == id


async def test_find_returns_result(db_session):
    id = random_id()
    result = await DummyModel.find(id, db=db_session)
    assert result.name == f"dummy_{id}"


async def test_find_by_and_all(db_session):
    # find_by
    name = f"dummy_{random.randint(1, 20)}"
    result = await DummyModel.find_by(db=db_session, name=name)
    assert result.name == name

    # all
    result = await DummyModel.all(db=db_session, limit=10, offset=0)
    assert len(result) == 10
    assert result[0].name == "dummy_1"


async def test_filter_by_in_and_contains(db_session):
    result1 = await DummyModel.filter_by(db=db_session, contains={"name": "9"})
    result2 = await DummyModel.filter_by(
        db=db_session, name__in=["dummy_9", "dummy_19"]
    )
    assert len(result2) == 2
    assert result1 == result2


async def test_update(db_session):
    id = random_id()
    new_name = "updated_dummy"

    random_dummy = await DummyModel.find(id, db=db_session)
    old_name = random_dummy.name

    await random_dummy.update(db=db_session, name=new_name)

    updated = await DummyModel.find(id, db=db_session)

    assert updated.name != old_name
    assert updated.name == new_name and updated.id == id


async def test_save(db_session):
    id = random_id()
    new_name = "test_save_dummy"

    random_dummy = await DummyModel.find(id, db=db_session)
    old_name = random_dummy.name

    random_dummy.name = new_name
    await random_dummy.save(db=db_session)

    updated = await DummyModel.find(id, db=db_session)

    assert updated.name != old_name
    assert updated.name == new_name and updated.id == id


async def test_delete(db_session):
    id = random_id()
    dummy = await DummyModel.find(id, db=db_session)

    await dummy.delete(db=db_session)

    dummy = await DummyModel.find(id, db=db_session)

    assert dummy is None
