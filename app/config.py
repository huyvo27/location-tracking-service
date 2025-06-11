import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "FASTAPI BASE APP")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION", "FastAPI Base App")
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    APP_DOCS_URL: str = os.getenv("APP_DOCS_URL", "/docs")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    API_PREFIX: str = ""
    BACKEND_CORS_ORIGINS: list = ["*"]
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT", "")
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 3  # Token expired after 3 days
    SECURITY_ALGORITHM: str = "HS256"
    LOGGING_CONFIG_FILE: str = os.path.join(BASE_DIR, "logging.ini")
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_EMAIL: str = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")

    class Config:
        env_file = ".env" if os.getenv("USE_DOTENV", "true").lower() == "true" else None


settings = Settings()
