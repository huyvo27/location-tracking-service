import logging
import os

from fastapi.middleware import Middleware

from app.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logging.config.fileConfig(settings.LOGGING_CONFIG_FILE, disable_existing_loggers=False)

logger = logging.getLogger("app")


class LoggingMiddleware:
    async def __call__(self, scope, receive, send):
        logger.info(f"Request: {scope['method']} {scope['path']}")
        await send(receive)
        logger.info("Response sent")


middleware = [Middleware(LoggingMiddleware)]
