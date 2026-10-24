import re
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# Snowflake identifiers cannot be bound as parameters, so the procedure name is
# restricted to plain (optionally qualified) identifiers to rule out SQL injection.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*){0,2}$")
_MODEL_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


class ConfigError(Exception):
    pass


class Settings(BaseSettings):
    """Loaded from environment variables, then `../.env` (the project's main .env when run
    from api/), then `.env`. Later files override earlier ones; real environment variables win."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), env_ignore_empty=True, extra="ignore", case_sensitive=True
    )

    APP_ENV: Literal["development", "test", "production"] = "development"
    HOST: str = "0.0.0.0"
    PORT: int = Field(8080, ge=1, le=65535)
    LOG_LEVEL: Literal["critical", "error", "warning", "info", "debug"] = "info"
    TRUST_PROXY: bool = False
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []
    RATE_LIMIT_PER_MINUTE: int = Field(30, ge=1)
    QUEST_TIMEZONE: str = "America/Los_Angeles"
    ALLOW_MOCK_IN_PRODUCTION: bool = False
    # Shared secret the web server sends as "Authorization: Bearer <token>" on /v1/*. Required in
    # production so strangers can't spend Snowflake credits; optional in development.
    API_AUTH_TOKEN: SecretStr | None = None

    # snowflake = Cortex AI_COMPLETE with SNOWFLAKE_AI_MODEL (a llama model); mock = offline regex/fixtures.
    AI_PROVIDER: Literal["snowflake", "mock"] = "mock"
    SNOWFLAKE_AI_MODEL: str = "llama3.3-70b"

    DATA_PROVIDER: Literal["snowflake", "mock"] = "mock"
    SNOWFLAKE_ACCOUNT: str | None = None
    SNOWFLAKE_USER: str | None = None
    SNOWFLAKE_PASSWORD: SecretStr | None = None
    SNOWFLAKE_PRIVATE_KEY_PATH: str | None = None
    # The same key as PEM text, for hosts that only offer environment variables (escaped "\n" is fine).
    # Takes precedence over SNOWFLAKE_PRIVATE_KEY_PATH.
    SNOWFLAKE_PRIVATE_KEY: SecretStr | None = None
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE: SecretStr | None = None
    SNOWFLAKE_WAREHOUSE: str | None = None
    SNOWFLAKE_DATABASE: str | None = None
    SNOWFLAKE_SCHEMA: str | None = None
    SNOWFLAKE_ROLE: str | None = None
    SNOWFLAKE_LOCATIONS_PROCEDURE: str = "LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS"
    SNOWFLAKE_QUERY_TIMEOUT_S: int = Field(20, ge=1, le=300)
    SNOWFLAKE_POOL_MAX: int = Field(4, ge=1, le=50)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @field_validator("QUEST_TIMEZONE")
    @classmethod
    def _check_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(f'"{v}" is not an IANA time zone') from e
        return v

    @field_validator("SNOWFLAKE_AI_MODEL")
    @classmethod
    def _check_model(cls, v: str) -> str:
        if not _MODEL_NAME.match(v):
            raise ValueError("must be a Cortex model name such as llama3.3-70b")
        return v

    @field_validator("SNOWFLAKE_LOCATIONS_PROCEDURE")
    @classmethod
    def _check_identifier(cls, v: str) -> str:
        if not _IDENTIFIER.match(v):
            raise ValueError("must be a plain, optionally qualified identifier")
        return v

    @model_validator(mode="after")
    def _check_providers(self) -> "Settings":
        missing: list[str] = []
        if self.DATA_PROVIDER == "snowflake" or self.AI_PROVIDER == "snowflake":
            missing += [k for k in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER") if getattr(self, k) is None]
            if self.SNOWFLAKE_PASSWORD is None and self.SNOWFLAKE_PRIVATE_KEY_PATH is None and self.SNOWFLAKE_PRIVATE_KEY is None:
                missing.append("SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PRIVATE_KEY")
        if self.APP_ENV == "production" and self.API_AUTH_TOKEN is None:
            missing.append("API_AUTH_TOKEN (required in production)")
        if self.API_AUTH_TOKEN is not None and len(self.API_AUTH_TOKEN.get_secret_value()) < 32:
            raise ValueError("API_AUTH_TOKEN must be at least 32 characters (e.g. openssl rand -hex 32)")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        if self.APP_ENV == "production" and not self.ALLOW_MOCK_IN_PRODUCTION and self.uses_mock:
            raise ValueError(
                "Mock providers are disabled in production. Set AI_PROVIDER=snowflake and DATA_PROVIDER=snowflake, "
                "or set ALLOW_MOCK_IN_PRODUCTION=true for a labeled demo deployment."
            )
        return self

    @property
    def uses_mock(self) -> bool:
        return self.AI_PROVIDER == "mock" or self.DATA_PROVIDER == "mock"


def load_settings(**overrides: object) -> Settings:
    """Load and validate settings, raising ConfigError with a readable message."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as e:
        parts = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msg = err["msg"].removeprefix("Value error, ")
            parts.append(f"{loc} {msg}".strip())
        raise ConfigError("Invalid environment: " + "; ".join(parts)) from None
