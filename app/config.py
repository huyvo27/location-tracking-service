import os
from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "LOCAL TRACKING SERVICE"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "LOCAL TRACKING SERVICE"
    APP_URL: str = "http://localhost:8000"
    APP_DOCS_URL: str = "/docs"
    SECRET_KEY: str = ""
    API_PREFIX: str = ""
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    DATABASE_URL: str = ""
    DATABASE_HOST: str = ""
    DATABASE_PORT: str = ""
    DB_DEBUG: bool = False
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 3
    SECURITY_ALGORITHM: str = "HS256"
    LOGGING_CONFIG_FILE: str = str(BASE_DIR / "logging.ini")
    DEFAULT_ADMIN_USERNAME: str = "sys_admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "sys_admin"
    REDIS_URLS: Union[str, List[str]] = []
    REDIS_MAX_CONNECTIONS: int = 100
    GROUP_LOCATION_TTL: int = 600

    @field_validator("REDIS_URLS", mode="before")
    @classmethod
    def parse_redis_urls(cls, v):
        if isinstance(v, str):
            return [url.strip() for url in v.split(",") if url.strip()]
        return v

    class Config:
        env_file = ".env" if os.getenv("USE_DOTENV", "true").lower() == "true" else None


settings = Settings()
