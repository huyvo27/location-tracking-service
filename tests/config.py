import os
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "LOCAL TRACKER (TEST)"
    APP_VERSION: str = "1.0.0-test"
    APP_DESCRIPTION: str = "LOCAL TRACKER API (TEST)"
    APP_URL: str = "http://localhost:8000"
    APP_DOCS_URL: str = "/docs"
    SECRET_KEY: str = "test_secret"
    API_PREFIX: str = ""
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    DATABASE_URL: str = os.getenv("TEST_DATABASE_URL") or "sqlite+aiosqlite:///:memory:"
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT", "")
    DEBUG: bool = True
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 3
    SECURITY_ALGORITHM: str = "HS256"
    LOGGING_CONFIG_FILE: str = str(BASE_DIR / "logging.ini")
    DEFAULT_ADMIN_USERNAME: str = "sys_admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "sys_admin"

    class Config:
        env_file = ".env.test" if os.path.exists(".env.test") else None


settings = Settings()
