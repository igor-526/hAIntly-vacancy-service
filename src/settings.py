from functools import cached_property

from pydantic import AnyHttpUrl, Field, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    app_title: str = Field(default="FastAPI Template", alias="APP_TITLE")

    sentry_enabled: bool = Field(default=False, alias="SENTRY_ENABLED")
    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE", ge=0.0, le=1.0)
    sentry_release: str | None = Field(default=None, alias="SENTRY_RELEASE")

    postgres_user: str = Field(default="app", alias="POSTGRES_USER")
    postgres_password: str = Field(default="app", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="app", alias="POSTGRES_DB")
    hh_app_token: str = Field(alias="HH_APP_TOKEN", min_length=10)
    hh_api_url: AnyHttpUrl = Field(alias="HH_API_URL")
    hh_user_agent: str = Field(alias="HH_USER_AGENT", min_length=3)
    hh_timeout_seconds: float = Field(default=10, alias="HH_TIMEOUT_SECONDS", gt=0)
    hh_retry_count: int = Field(default=2, alias="HH_RETRY_COUNT", ge=0, le=5)
    hh_retry_backoff_seconds: float = Field(default=0.5, alias="HH_RETRY_BACKOFF_SECONDS", ge=0, le=10)
    celery_broker_url: RedisDsn = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: RedisDsn = Field(alias="CELERY_RESULT_BACKEND")
    dictionary_lock_url: RedisDsn = Field(alias="DICTIONARY_LOCK_URL")
    dictionary_lock_ttl_seconds: int = Field(default=900, alias="DICTIONARY_LOCK_TTL_SECONDS", gt=0)
    dictionary_max_age_hours: int = Field(alias="VACANCY_DICTIONARY_MAX_AGE_HOURS", gt=0)
    dictionary_seed_timeout_seconds: int = Field(default=900, alias="DICTIONARY_SEED_TIMEOUT_SECONDS", gt=0)
    profile_service_url: AnyHttpUrl = Field(alias="PROFILE_SERVICE_URL")
    profile_service_timeout_seconds: float = Field(default=5, alias="PROFILE_SERVICE_TIMEOUT_SECONDS", gt=0)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> Settings:
        if self.sentry_enabled and not self.sentry_dsn:
            raise ValueError("SENTRY_DSN is required when SENTRY_ENABLED=true")
        return self

    @cached_property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()  # type: ignore[call-arg]
