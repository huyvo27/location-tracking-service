import uuid
from typing import AsyncGenerator

from fastapi import HTTPException
from redis.asyncio import ConnectionError as RedisConnectionError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logger import logger
from app.db.redis import redis_clients
from app.db.session import AsyncSessionLocal
from app.utils.consistent_hash import get_server_index


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def get_redis(_uuid: str) -> Redis:
    """
    Dependency to get a Redis client for a given UUID using consistent hashing.
    Tries fallback servers if the primary server is unavailable.

    Args:
        uuid (str): UUID key to determine the Redis server.

    Returns:
        Redis: The Redis client for the selected server.

    Raises:
        HTTPException: If no Redis servers are available or the UUID is invalid.
    """
    if not redis_clients:
        logger.error("No Redis clients initialized")
        raise HTTPException(status_code=503, detail="No Redis servers available")

    try:
        uuid.UUID(_uuid)
    except ValueError:
        logger.error(f"Invalid UUID format: {_uuid}")
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    num_servers = len(redis_clients)
    server_idx = get_server_index(_uuid, num_servers)
    attempts = 0

    while attempts < num_servers:
        try:
            client = redis_clients[server_idx]
            await client.ping()
            return client
        except (RedisConnectionError, TimeoutError) as e:
            logger.warning(
                f"Failed to connect to Redis server {settings.REDIS_URLs[server_idx]} "
                f"for UUID {_uuid}: {str(e)}"
            )
            server_idx = (server_idx + 1) % num_servers
            attempts += 1

    logger.error(
        f"No available Redis servers for UUID {_uuid} after {attempts} attempts"
    )
    raise HTTPException(status_code=503, detail="No available Redis servers")
