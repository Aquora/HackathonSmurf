import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .domain.types import QuestRoute, UserRequest
from .errors import AppError
from .services.quest_service import QuestService

log = logging.getLogger("app")

BODY_LIMIT_BYTES = 16 * 1024
_REQUEST_ID = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "cross-origin-resource-policy": "same-origin",
    "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
}


def _error(status: int, code: str, message: str, request_id: str | None, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message, "requestId": request_id}
    if details is not None:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status, headers={"x-request-id": request_id or ""})


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """Reject request bodies over the limit, whether or not Content-Length is sent."""

    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        length = headers.get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.limit):
            await _error(413, "VALIDATION_ERROR", "Request body is too large.", None)(scope, receive, send)
            return

        received = 0
        started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not started:
                await _error(413, "VALIDATION_ERROR", "Request body is too large.", None)(scope, receive, send)


class FixedWindowRateLimiter:
    """In-memory per-client limit. Per process: use a shared store when running several instances."""

    def __init__(self, per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_minute = per_minute
        self._clock = clock
        self._windows: dict[str, tuple[int, int]] = {}

    def hit(self, key: str) -> int | None:
        """Record a request. Returns seconds to wait if over the limit, else None."""
        now = self._clock()
        window = int(now // 60)
        if len(self._windows) > 10_000:  # drop stale entries
            self._windows = {k: v for k, v in self._windows.items() if v[0] == window}
        start, count = self._windows.get(key, (window, 0))
        if start != window:
            start, count = window, 0
        count += 1
        self._windows[key] = (start, count)
        if count > self.per_minute:
            return max(1, int(60 - (now % 60)))
        return None


def create_app(
    service: QuestService,
    *,
    cors_origins: list[str],
    rate_limit_per_minute: int,
    docs_enabled: bool = True,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        if on_shutdown:
            await on_shutdown()

    app = FastAPI(
        title="Local Quest API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    limiter = FixedWindowRateLimiter(rate_limit_per_minute)

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id

        if request.url.path != "/health":
            client = request.client.host if request.client else "unknown"
            retry_after = limiter.hit(client)
            if retry_after is not None:
                response = _error(429, "RATE_LIMITED", f"Too many requests. Try again in {retry_after} seconds.", request_id)
                response.headers["retry-after"] = str(retry_after)
                return response

        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        for k, v in _SECURITY_HEADERS.items():
            # Swagger UI at /docs loads assets from a CDN, so it keeps FastAPI's defaults for CSP.
            if k == "content-security-policy" and request.url.path in ("/docs", "/docs/oauth2-redirect"):
                continue
            response.headers.setdefault(k, v)
        # Request bodies (messages, addresses) are never logged.
        log.info(
            "%s %s -> %d (%.0f ms) id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
            request_id,
        )
        return response

    # Added after the http middleware so it wraps it (outermost): preflight and CORS headers apply to every response.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type", "x-request-id"],
        expose_headers=["x-request-id"],
    )
    app.add_middleware(BodyLimitMiddleware, limit=BODY_LIMIT_BYTES)

    def rid(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        level = logging.WARNING if exc.status_code >= 500 else logging.INFO
        log.log(level, "%s: %s details=%s id=%s", exc.code, exc.message, exc.details, rid(request))
        return _error(exc.status_code, exc.code, exc.message, rid(request), exc.details)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return _error(400, "VALIDATION_ERROR", "Malformed JSON body.", rid(request))
        details = [
            {"path": ".".join(str(p) for p in e["loc"][1:] if p != "body") or "body", "message": e["msg"]} for e in errors
        ]
        return _error(400, "VALIDATION_ERROR", "Invalid request body.", rid(request), details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            return _error(404, "NOT_FOUND", "Route not found.", rid(request))
        return _error(exc.status_code, "VALIDATION_ERROR", str(exc.detail), rid(request))

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error id=%s", rid(request))
        return _error(500, "INTERNAL_ERROR", "Something went wrong. Please try again.", rid(request))

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness only; does not check Cursor or Snowflake."""
        return {"status": "ok"}

    @app.post(
        "/v1/quests",
        response_model=QuestRoute,
        response_model_exclude_none=True,
        responses={400: {}, 422: {}, 429: {}, 502: {}, 503: {}, 504: {}},
    )
    async def create_quest(body: UserRequest) -> QuestRoute:
        """Turn a free-text request and start address into a validated round-trip quest."""
        result = await service.create_quest(body)
        return result.route

    return app
