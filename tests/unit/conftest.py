from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from tests.unit.config import TestConfig


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TestConfig.DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
def async_session(test_engine):
    return sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(async_session) -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
