"""Shared error envelope (docs/TEAM-CONTRACT.md §5 "Failure behavior").

Every failure, including framework validation and unknown routes, is returned as
{"error": {code, message, request_id, details: {field_errors, suggested_adjustments, ...}}}.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        field_errors: list[dict[str, str]] | None = None,
        suggested_adjustments: list[dict[str, str]] | None = None,
        extra_details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field_errors = field_errors or []
        self.suggested_adjustments = suggested_adjustments or []
        self.extra_details = extra_details or {}


def validation_error(field_errors: list[dict[str, str]]) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", "The request is invalid.", field_errors=field_errors)


def configuration_error(message: str) -> ApiError:
    return ApiError(503, "CONFIGURATION_ERROR", message)


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def envelope(request: Request, err: ApiError) -> JSONResponse:
    details: dict[str, Any] = {
        "field_errors": err.field_errors,
        "suggested_adjustments": err.suggested_adjustments,
        **err.extra_details,
    }
    request_id = request_id_of(request)
    body = {
        "error": {
            "code": err.code,
            "message": err.message,
            "request_id": request_id,
            "details": details,
        }
    }
    # Set here too: unhandled errors are answered outside the request-ID middleware.
    return JSONResponse(
        status_code=err.status_code, content=body, headers={"X-Request-ID": request_id}
    )


def _field_path(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p != "body"]
    return ".".join(parts) or "body"


async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    return envelope(request, exc)


async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    field_errors = [
        {"field": _field_path(tuple(e.get("loc", ()))), "message": e.get("msg", "Invalid value.")}
        for e in exc.errors()
    ]
    return envelope(request, validation_error(field_errors))


async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    code = codes.get(exc.status_code, "INTERNAL_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return envelope(request, ApiError(exc.status_code, code, message))


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error (request_id=%s)", request_id_of(request))
    return envelope(request, ApiError(500, "INTERNAL_ERROR", "An unexpected error occurred."))


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation)
    app.add_exception_handler(StarletteHTTPException, _handle_http)
    app.add_exception_handler(Exception, _handle_unexpected)
