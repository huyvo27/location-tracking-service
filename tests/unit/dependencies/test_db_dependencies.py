import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from redis.asyncio import ConnectionError as RedisConnectionError

from app.dependencies.db import get_redis


@pytest.mark.asyncio
async def test_get_redis_no_clients(monkeypatch):
    monkeypatch.setattr("app.dependencies.db.redis_clients", [])

    with pytest.raises(HTTPException) as exc_info:
        await get_redis(str(uuid.uuid4()))

    assert exc_info.value.status_code == 503
    assert "No Redis servers available" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_redis_invalid_uuid(monkeypatch):
    monkeypatch.setattr("app.dependencies.db.redis_clients", [AsyncMock()])

    with pytest.raises(HTTPException) as exc_info:
        await get_redis("invalid-uuid")

    assert exc_info.value.status_code == 400
    assert "Invalid UUID format" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_redis_success(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    monkeypatch.setattr("app.dependencies.db.redis_clients", [mock_redis])
    monkeypatch.setattr(
        "app.dependencies.db.settings", MagicMock(REDIS_URLs=["redis://localhost"])
    )

    client = await get_redis(str(uuid.uuid4()))
    assert client is mock_redis
    mock_redis.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_redis_fallback_success(monkeypatch):
    failing_redis = AsyncMock()
    failing_redis.ping.side_effect = RedisConnectionError("Failing Redis")

    working_redis = AsyncMock()
    working_redis.ping.return_value = True

    monkeypatch.setattr(
        "app.dependencies.db.redis_clients", [failing_redis, working_redis]
    )
    monkeypatch.setattr(
        "app.dependencies.db.settings", MagicMock(REDIS_URLs=["url1", "url2"])
    )

    # Patch get_server_index to force starting at index 0
    with patch("app.dependencies.db.get_server_index", return_value=0):
        client = await get_redis(str(uuid.uuid4()))

    assert client is working_redis
    assert failing_redis.ping.await_count == 1
    assert working_redis.ping.await_count == 1


@pytest.mark.asyncio
async def test_get_redis_all_fail(monkeypatch):
    redis1 = AsyncMock()
    redis1.ping.side_effect = RedisConnectionError("fail")

    redis2 = AsyncMock()
    redis2.ping.side_effect = TimeoutError("timeout")

    monkeypatch.setattr("app.dependencies.db.redis_clients", [redis1, redis2])
    monkeypatch.setattr(
        "app.dependencies.db.settings", MagicMock(REDIS_URLs=["url1", "url2"])
    )

    with patch("app.dependencies.db.get_server_index", return_value=0):
        with pytest.raises(HTTPException) as exc_info:
            await get_redis(str(uuid.uuid4()))

    assert exc_info.value.status_code == 503
    assert "No available Redis servers" in str(exc_info.value.detail)
    assert redis1.ping.await_count == 1
    assert redis2.ping.await_count == 1
