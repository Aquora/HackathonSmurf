"""Snowflake candidate lookup.

Calls a stored procedure that takes (preferences VARIANT, address STRING) and returns a
VARIANT object whose `locations` array holds 10 {name, address, closingTime, ...} objects.
See ../snowflake/README.md (LOCAL_QUEST.APP.FIND_QUEST_LOCATIONS).
"""

import asyncio
import json
import logging
import queue
import threading
from typing import Any, Protocol

from ...config import Settings
from ...domain.types import Preferences
from ...errors import AppError, upstream_invalid, upstream_timeout, upstream_unavailable

log = logging.getLogger(__name__)

SqlParam = str | int | float | bool | None


class SqlExecutor(Protocol):
    """Runs one parameterized (qmark) statement and returns rows as dicts keyed by column name."""

    async def execute(self, sql: str, params: list[SqlParam], timeout_s: int) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...


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
        if s.SNOWFLAKE_PRIVATE_KEY_PATH:
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
