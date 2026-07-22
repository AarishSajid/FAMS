"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://agriverse_user:agriverse_pass@localhost:5432/agriverse"
    AGRIVERSE_DB_URL: str = "postgresql://remote_user:password@agriverse-db.com:5432/agriverse_prod"
    SYNC_INTERVAL_MINUTES: int = 60

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET: str = "your-agriverse-jwt-secret-here"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Redis & RabbitMQ ──────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    # ── Weather API ───────────────────────────────────────────
    WEATHER_API_KEY: str = ""
    WEATHER_API_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # ── Server ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — reads .env once at startup."""
    return Settings()
