import logging
import os

from app.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOGGING_CONFIG_FILE = os.path.join(BASE_DIR, "logging.ini")

LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logging.config.fileConfig(settings.LOGGING_CONFIG_FILE, disable_existing_loggers=False)

logger = logging.getLogger("app")
