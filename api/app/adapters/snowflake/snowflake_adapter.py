"""Snowflake candidate lookup.

Calls a stored procedure that takes (preferences VARIANT, address STRING) and returns a
VARIANT object whose `locations` array holds 10 {name, address, closingTime, ...} objects.
See ../snowflake/README.md (LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS).
"""

import asyncio
import base64
import json
import logging
import queue
import re
import threading
from typing import Any, Protocol

from ...config import ConfigError, Settings
from ...domain.types import Preferences
from ...errors import AppError, upstream_invalid, upstream_timeout, upstream_unavailable

log = logging.getLogger(__name__)

SqlParam = str | int | float | bool | None


class SqlExecutor(Protocol):
    """Runs one parameterized (qmark) statement and returns rows as dicts keyed by column name."""

    async def execute(self, sql: str, params: list[SqlParam], timeout_s: int) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...


_BASE64 = re.compile(r"[A-Za-z0-9+/]{100,}={0,2}")
_PEM_BLOCK = re.compile(r"-----BEGIN ([A-Z ]+)-----(.*?)-----END \1-----", re.DOTALL)


def _normalize_pem(pem: str) -> str:
    """Rebuild a PEM block however a host's form mangled it: literal \\n, line breaks turned into
    spaces, surrounding quotes, Windows line endings, missing BEGIN/END lines, or the whole .p8
    file base64-encoded onto one line. Only the framing changes; the key bytes are untouched."""
    text = pem.strip().strip("'\"").replace("\\n", "\n")
    match = _PEM_BLOCK.search(text)
    if match:
        label, body = match.group(1), "".join(match.group(2).split())
    else:
        compact = "".join(text.split())
        if not _BASE64.fullmatch(compact):
            raise ValueError(
                "SNOWFLAKE_PRIVATE_KEY is not a PEM key (expected -----BEGIN ... KEY----- ... -----END ... KEY-----, "
                "or the .p8 file as one line of base64)"
            )
        try:  # the whole .p8 file base64-encoded onto one line (`base64 -i key.p8`)
            decoded = base64.b64decode(compact, validate=True).decode("ascii")
        except (ValueError, UnicodeDecodeError):
            decoded = ""
        if "-----BEGIN" in decoded:
            return _normalize_pem(decoded)
        label, body = "PRIVATE KEY", compact  # only the key body, without the BEGIN/END lines
    lines = [body[i : i + 64] for i in range(0, len(body), 64)]
    return "\n".join([f"-----BEGIN {label}-----", *lines, f"-----END {label}-----", ""])


def _der_private_key(pem: str, passphrase: str | None) -> bytes:
    """PEM key text from an environment variable -> unencrypted DER bytes for the connector."""
    from cryptography.hazmat.primitives import serialization  # installed with the connector

    key = serialization.load_pem_private_key(
        _normalize_pem(pem).encode(), password=passphrase.encode() if passphrase else None
    )
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


class SnowflakeLocationProvider:
    def __init__(self, executor: SqlExecutor, procedure: str, timeout_s: int) -> None:
        self._executor = executor
        self._procedure = procedure  # validated as a plain identifier in config
        self._timeout_s = timeout_s

    async def find_locations(self, preferences: Preferences, address: str) -> Any:
        sql = f"CALL {self._procedure}(PARSE_JSON(?), ?)"
        rows = await self._executor.execute(sql, [preferences.model_dump_json(), address], self._timeout_s)
        if not rows:
            raise upstream_invalid("snowflake", "procedure returned no rows")
        # A CALL returns one row with one column named after the procedure. VARIANT arrives as JSON text.
        value = next(iter(rows[0].values()), None)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                raise upstream_invalid("snowflake", "procedure result was not valid JSON") from None
        return value

    async def aclose(self) -> None:
        await self._executor.aclose()


class SnowflakePoolExecutor:
    """Small thread-safe connection pool around the synchronous snowflake-connector-python.

    Statements run in worker threads so they never block the event loop.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._idle: queue.LifoQueue[Any] = queue.LifoQueue()
        self._slots = threading.BoundedSemaphore(settings.SNOWFLAKE_POOL_MAX)
        self._closed = False
        # Parse a key given as text now, so a bad paste fails at startup with a clear message
        # instead of as "upstream unavailable" on every request.
        self._private_key_der: bytes | None = None
        if settings.SNOWFLAKE_PRIVATE_KEY:
            try:
                self._private_key_der = _der_private_key(
                    settings.SNOWFLAKE_PRIVATE_KEY.get_secret_value(),
                    settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.get_secret_value()
                    if settings.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE
                    else None,
                )
            except (ValueError, TypeError) as e:
                # The message never contains key material.
                raise ConfigError(f"SNOWFLAKE_PRIVATE_KEY could not be read: {e}") from None

    def _connect(self) -> Any:
        import snowflake.connector  # imported lazily: heavy, and unused in mock mode

        s = self._settings
        kwargs: dict[str, Any] = {
            "account": s.SNOWFLAKE_ACCOUNT,
            "user": s.SNOWFLAKE_USER,
            "warehouse": s.SNOWFLAKE_WAREHOUSE,
            "database": s.SNOWFLAKE_DATABASE,
            "schema": s.SNOWFLAKE_SCHEMA,
            "role": s.SNOWFLAKE_ROLE,
            "application": "local-quest-api",
            "paramstyle": "qmark",
            "login_timeout": 15,
            "client_session_keep_alive": True,
            "session_parameters": {"STATEMENT_TIMEOUT_IN_SECONDS": s.SNOWFLAKE_QUERY_TIMEOUT_S},
        }
        if self._private_key_der is not None:
            kwargs["authenticator"] = "SNOWFLAKE_JWT"
            kwargs["private_key"] = self._private_key_der
        elif s.SNOWFLAKE_PRIVATE_KEY_PATH:
            kwargs["authenticator"] = "SNOWFLAKE_JWT"
            kwargs["private_key_file"] = s.SNOWFLAKE_PRIVATE_KEY_PATH
            if s.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE:
                kwargs["private_key_file_pwd"] = s.SNOWFLAKE_PRIVATE_KEY_PASSPHRASE.get_secret_value()
        elif s.SNOWFLAKE_PASSWORD:
            kwargs["password"] = s.SNOWFLAKE_PASSWORD.get_secret_value()
        return snowflake.connector.connect(**{k: v for k, v in kwargs.items() if v is not None})

    def _run(self, sql: str, params: list[SqlParam]) -> list[dict[str, Any]]:
        from snowflake.connector import DictCursor

        if not self._slots.acquire(timeout=15):
            raise upstream_unavailable("snowflake")
        conn = None
        try:
            try:
                conn = self._idle.get_nowait()
                if conn.is_closed():
                    conn = self._connect()
            except queue.Empty:
                conn = self._connect()
            with conn.cursor(DictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
            self._idle.put(conn)
            conn = None
            return rows
        finally:
            if conn is not None:  # failed mid-use: discard rather than return a broken connection
                try:
                    conn.close()
                except Exception:  # noqa: BLE001
                    pass
            self._slots.release()

    async def execute(self, sql: str, params: list[SqlParam], timeout_s: int) -> list[dict[str, Any]]:
        if self._closed:
            raise upstream_unavailable("snowflake")
        try:
            # Client-side guard in case connecting or acquiring hangs beyond the statement timeout.
            return await asyncio.wait_for(asyncio.to_thread(self._run, sql, params), timeout=timeout_s + 10)
        except AppError:
            raise
        except TimeoutError:
            raise upstream_timeout("snowflake") from None
        except Exception as e:  # connector errors
            log.warning("snowflake call failed: %s: %s", type(e).__name__, str(e)[:500])
            if "timeout" in str(e).lower() or "cancel" in str(e).lower():
                raise upstream_timeout("snowflake") from None
            raise upstream_unavailable("snowflake") from None

    async def aclose(self) -> None:
        self._closed = True

        def close_all() -> None:
            while True:
                try:
                    self._idle.get_nowait().close()
                except queue.Empty:
                    return
                except Exception:  # noqa: BLE001
                    continue

        await asyncio.to_thread(close_all)
