"""
Application configuration.

Single source of truth for environment-driven settings. No module should read
os.environ directly — everything goes through this Settings object so that
config has one place to change and one place to mock in tests.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Sentinel"
    ENVIRONMENT: str = "development"  # development | test | production
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"

    # --- JWT / Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # noqa: S105 (placeholder default only)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 7

    # --- Password hashing ---
    BCRYPT_ROUNDS: int = 12

    # --- Rate limiting (login) ---
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300  # 5 minutes

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor. lru_cache ensures the .env file is parsed once
    per process, and lets tests override via dependency_overrides rather than
    re-parsing environment on every call.
    """
    return Settings()
