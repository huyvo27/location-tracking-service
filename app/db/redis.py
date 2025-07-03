from redis.asyncio import ConnectionPool, Redis

from app.config import settings
from app.core.logger import logger

pools = [
    ConnectionPool.from_url(url=url, max_connections=settings.REDIS_MAX_CONNECTIONS)
    for url in settings.REDIS_URLS
]

redis_clients = [Redis(connection_pool=pool, decode_responses=True) for pool in pools]


async def close_redis_clients() -> None:
    """
    Close all Redis connections and pools.
    """
    for client in redis_clients:
        try:
            await client.aclose()
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")

    for pool in pools:
        try:
            await pool.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting pool: {e}")
