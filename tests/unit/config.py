import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


class TestConfig:
    DATABASE_URL = os.environ["DATABASE_URL"]
