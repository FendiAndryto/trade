"""
TradeGear Configuration — Environment-based settings.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- App ---
    APP_NAME: str = "TradeGear"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://tradegear:tradegear@localhost:5433/tradegear"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT Auth ---
    JWT_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- MT5 Agent ---
    MT5_AGENT_SECRET: str = "CHANGE-ME-agent-shared-secret"

    # --- Rate Limiting ---
    WEBHOOK_RATE_LIMIT: int = 60  # per minute per token
    API_RATE_LIMIT: int = 120  # per minute per user

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
