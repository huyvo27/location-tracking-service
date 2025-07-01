from typing import AsyncGenerator, Generator
from unittest import mock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from tests.utils import generate_strong_password, random_lower_string

NUMBER_OF_REDIS_SERVER = 2

@pytest.fixture(scope="session")
def postgres_url():
    try:
        with PostgresContainer("postgres:15") as postgres:
            yield postgres.get_connection_url(driver="psycopg")
    except Exception as e:
        pytest.fail(f"Failed to start Postgres container: {e}")


@pytest.fixture(scope="session")
def redis_urls():
    urls = []
    containers = []

    try:
        for _ in range(NUMBER_OF_REDIS_SERVER):
            container = RedisContainer("redis:8.0.2")
            container.start()
            containers.append(container)

            host = container.get_container_host_ip()
            port = container.get_exposed_port(6379)
            urls.append(f"redis://{host}:{port}")

        yield urls
    except Exception as e:
        pytest.fail(f"Failed to start Redis containers: {e}")
    finally:
        for container in containers:
            container.stop()


@pytest.fixture(scope="session")
def default_admin():
    return {
        "username": f"admin-{random_lower_string(8)}",
        "password": generate_strong_password(),
    }


@pytest.fixture(autouse=True)
def override_settings(postgres_url: str, redis_urls: str, default_admin: dict):
    with mock.patch.dict(
        "os.environ",
        {
            "DATABASE_URL": postgres_url,
            "REDIS_URLs": ",".join(redis_urls),
            "DEFAULT_ADMIN_USERNAME": default_admin["username"],
            "DEFAULT_ADMIN_PASSWORD": default_admin["password"],
        },
    ):
        from app.config import Settings

        with mock.patch("app.config.settings", new=Settings()):
            yield


@pytest.fixture
def client() -> Generator:
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def async_client():
    from app.main import app

    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac


@pytest_asyncio.fixture
async def pg_db() -> AsyncGenerator[AsyncSession, None]:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
        await session.close()
