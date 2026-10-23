import re
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, HttpUrl, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Snowflake identifiers cannot be bound as parameters, so the procedure name is
# restricted to plain (optionally qualified) identifiers to rule out SQL injection.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*(\.[A-Za-z_][A-Za-z0-9_$]*){0,2}$")


class ConfigError(Exception):
    pass


class Settings(BaseSettings):
    """Loaded from environment variables, then `.env`. Real environment variables win."""

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore", case_sensitive=True)

    APP_ENV: Literal["development", "test", "production"] = "development"
    HOST: str = "0.0.0.0"
    PORT: int = Field(8080, ge=1, le=65535)
    LOG_LEVEL: Literal["critical", "error", "warning", "info", "debug"] = "info"
    TRUST_PROXY: bool = False
    CORS_ORIGINS: Annotated[list[str], NoDecode] = []
    RATE_LIMIT_PER_MINUTE: int = Field(30, ge=1)
    QUEST_TIMEZONE: str = "America/Los_Angeles"
    ALLOW_MOCK_IN_PRODUCTION: bool = False

    AI_PROVIDER: Literal["cursor", "mock"] = "mock"
    CURSOR_API_BASE_URL: HttpUrl | None = None
    CURSOR_API_KEY: SecretStr | None = None
    CURSOR_MODEL: str | None = None
    CURSOR_TIMEOUT_S: float = Field(30, ge=1)
    CURSOR_MAX_RETRIES: int = Field(2, ge=0, le=5)
    CURSOR_JSON_MODE: bool = True

    DATA_PROVIDER: Literal["snowflake", "mock"] = "mock"
    SNOWFLAKE_ACCOUNT: str | None = None
    SNOWFLAKE_USER: str | None = None
    SNOWFLAKE_PASSWORD: SecretStr | None = None
    SNOWFLAKE_PRIVATE_KEY_PATH: str | None = None
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

    @field_validator("SNOWFLAKE_LOCATIONS_PROCEDURE")
    @classmethod
    def _check_identifier(cls, v: str) -> str:
        if not _IDENTIFIER.match(v):
            raise ValueError("must be a plain, optionally qualified identifier")
        return v

    @model_validator(mode="after")
    def _check_providers(self) -> "Settings":
        missing: list[str] = []
        if self.AI_PROVIDER == "cursor":
            missing += [k for k in ("CURSOR_API_BASE_URL", "CURSOR_API_KEY", "CURSOR_MODEL") if getattr(self, k) is None]
        if self.DATA_PROVIDER == "snowflake":
            missing += [k for k in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER") if getattr(self, k) is None]
            if self.SNOWFLAKE_PASSWORD is None and self.SNOWFLAKE_PRIVATE_KEY_PATH is None:
                missing.append("SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        if self.APP_ENV == "production" and not self.ALLOW_MOCK_IN_PRODUCTION and self.uses_mock:
            raise ValueError(
                "Mock providers are disabled in production. Set AI_PROVIDER=cursor and DATA_PROVIDER=snowflake, "
                "or set ALLOW_MOCK_IN_PRODUCTION=true for a labeled demo deployment."
            )
        return self

    @property
    def uses_mock(self) -> bool:
        return self.AI_PROVIDER == "mock" or self.DATA_PROVIDER == "mock"

    @property
    def cursor_base_url(self) -> str:
        return str(self.CURSOR_API_BASE_URL).rstrip("/")


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
