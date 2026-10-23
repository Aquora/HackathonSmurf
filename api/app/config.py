"""Backend-owned configuration, read from environment variables (prefix LQ_).

Owner-confirmed input defaults (90 minutes, $30, no preference) are baked in.
Still-unresolved policies (currency code, start/timezone fallback) have no
default: when unset, a request that needs them fails with CONFIGURATION_ERROR
instead of the server guessing.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LQ_", env_file=".env", extra="ignore")

    defaults_version: str = "defaults_v1"
    default_available_seconds: int = Field(default=5400, gt=0)
    default_budget_amount_minor: int = Field(default=3000, ge=0)
    # Unresolved: which dollar currency the $30 default means. No silent "USD".
    default_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    # Currencies accepted on supplied budgets. Empty means "only default_currency".
    supported_currencies: list[str] = Field(default_factory=list)

    # Unresolved: fallbacks when the user omits start/timezone. A configured
    # anchor is a neighborhood point, never presented as the user's location.
    neighborhood_anchor_latitude: float | None = Field(default=None, ge=-90, le=90)
    neighborhood_anchor_longitude: float | None = Field(default=None, ge=-180, le=180)
    default_timezone: str | None = None

    # Input limits (proposed; freeze with the contract).
    max_available_seconds: int = 8 * 3600
    max_budget_amount_minor: int = 100_000
    max_interests: int = 10
    max_interest_length: int = 40

    def accepted_currencies(self) -> set[str]:
        accepted = set(self.supported_currencies)
        if self.default_currency:
            accepted.add(self.default_currency)
        return accepted


@lru_cache
def get_settings() -> Settings:
    return Settings()
