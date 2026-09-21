"""
Atlas – Digital Banking Intelligence Platform
Core Configuration Module

Single source of truth for all Atlas environment configuration.
Uses pydantic-settings for type-safe, validated, environment-driven config.
Never hardcode secrets. Never call os.getenv() outside this module.

Sub-configs use env_prefix for namespace isolation, preventing collisions
between POSTGRES_HOST and REDIS_HOST, for example.
"""

from functools import lru_cache
from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL warehouse connection settings."""

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_", env_file=".env", extra="ignore"
    )

    host: str = "localhost"
    port: int = 5432
    db: str = "atlas_db"
    user: str = "atlas_user"
    password: str = Field(default="atlas_password", min_length=8)
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    @property
    def url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSettings(BaseSettings):
    """Redis cache settings (used from Sprint 5 onwards for KPI caching)."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_", env_file=".env", extra="ignore"
    )

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""

    @property
    def url(self) -> str:
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class JWTSettings(BaseSettings):
    """JWT authentication settings."""

    model_config = SettingsConfigDict(
        env_prefix="JWT_", env_file=".env", extra="ignore"
    )

    secret_key: str = Field(default="insecure-dev-key-change-in-production", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class DataGenerationSettings(BaseSettings):
    """Synthetic data generation parameters."""

    model_config = SettingsConfigDict(
        env_prefix="DATA_", env_file=".env", extra="ignore"
    )

    seed: int = 42
    customer_count: int = 500_000
    transaction_multiplier: int = 10
    history_years: int = 3
    start_date: str = "2022-01-01"
    output_dir: str = "data/raw"


class AnalyticsSettings(BaseSettings):
    """Analytics engine configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ANALYTICS_", env_file=".env", extra="ignore"
    )

    batch_size: int = 10_000
    cache_ttl_seconds: int = 300
    forecast_horizon_days: int = 90
    churn_lookback_days: int = 90


class ETLSettings(BaseSettings):
    """ETL pipeline configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ETL_", env_file=".env", extra="ignore"
    )

    schedule_cron: str = "0 2 * * *"
    staging_path: str = "data/staging"
    raw_path: str = "data/raw"
    batch_size: int = 50_000


class AtlasSettings(BaseSettings):
    """
    Master Atlas settings object.
    Reads ATLAS_* prefixed env vars.
    Sub-configs are instantiated as properties to avoid prefix collision.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ATLAS_",
        extra="ignore",
        case_sensitive=False,
    )

    env: Literal["development", "staging", "production"] = "development"
    version: str = "1.0.0"
    secret_key: str = Field(default="insecure-dev-key-change-in-production", min_length=16)
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Sprint 6: lightweight API credential (single static key via X-API-Key
    # header). Deliberately not full JWT auth — JWTSettings above already
    # models secret/algorithm/expiry for that, and is reserved for the real
    # user-auth build-out in a later infrastructure sprint. This flag lets
    # the guard be switched off entirely for local development.
    api_key: str = Field(default="insecure-dev-key-change-in-production", min_length=8)
    api_key_enabled: bool = True

    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    public_url: str = "http://localhost:8000"

    # ─── Sub-config accessors ─────────────────────────────────────────────────
    # Properties (not fields) avoids pydantic trying to parse sub-models
    # from the ATLAS_ namespace and avoids env_prefix collisions.

    @property
    def db(self) -> DatabaseSettings:
        return DatabaseSettings()

    @property
    def redis(self) -> RedisSettings:
        return RedisSettings()

    @property
    def jwt(self) -> JWTSettings:
        return JWTSettings()

    @property
    def data(self) -> DataGenerationSettings:
        return DataGenerationSettings()

    @property
    def analytics(self) -> AnalyticsSettings:
        return AnalyticsSettings()

    @property
    def etl(self) -> ETLSettings:
        return ETLSettings()

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env == "development"


@lru_cache(maxsize=1)
def get_settings() -> AtlasSettings:
    """
    Return cached AtlasSettings singleton.
    Parsed once at startup; safe to call anywhere.

    FastAPI dependency usage:
        from backend.app.core.config import get_settings
        def endpoint(s: AtlasSettings = Depends(get_settings)): ...
    """
    return AtlasSettings()


# Module-level convenience alias
settings = get_settings()
