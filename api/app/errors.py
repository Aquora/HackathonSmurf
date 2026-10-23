from typing import Any, Literal

ErrorCode = Literal[
    "VALIDATION_ERROR",
    "UPSTREAM_UNAVAILABLE",
    "UPSTREAM_TIMEOUT",
    "UPSTREAM_INVALID_RESPONSE",
    "NO_FEASIBLE_ROUTE",
    "RATE_LIMITED",
    "NOT_FOUND",
    "INTERNAL_ERROR",
]
Upstream = Literal["cursor", "snowflake"]


class AppError(Exception):
    def __init__(self, status_code: int, code: ErrorCode, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def upstream_unavailable(upstream: Upstream) -> AppError:
    return AppError(503, "UPSTREAM_UNAVAILABLE", f"The {upstream} service is unavailable. Please try again.", {"upstream": upstream})


def upstream_timeout(upstream: Upstream) -> AppError:
    return AppError(504, "UPSTREAM_TIMEOUT", f"The {upstream} service timed out. Please try again.", {"upstream": upstream})


def upstream_invalid(upstream: Upstream, reason: str, issues: list[str] | None = None) -> AppError:
    details: dict[str, Any] = {"upstream": upstream}
    if issues:
        details["issues"] = issues
    return AppError(502, "UPSTREAM_INVALID_RESPONSE", f"The {upstream} service returned an invalid response: {reason}", details)
