"""Model step via Snowflake Cortex: `SELECT AI_COMPLETE(model, prompt)` on the Snowflake pool.

Drop-in replacement for JsonChatClient (same `complete_json` / `aclose`), so CursorAdapter's
prompts and validation are reused unchanged. Chat messages are flattened into one prompt
because AI_COMPLETE takes a single string. Errors from model *output* are reported with
upstream "cursor" (the API's name for the model step); connection errors come from the
executor as "snowflake".
"""

import json
from typing import Any

from ...errors import upstream_invalid
from ..llm.chat_client import extract_json
from .snowflake_adapter import SqlExecutor


def flatten_messages(messages: list[dict[str, str]]) -> str:
    parts = [f"[{m['role'].upper()}]\n{m['content']}" for m in messages]
    return "\n\n".join(parts) + "\n\n[ASSISTANT]\n"


class CortexChatClient:
    def __init__(self, executor: SqlExecutor, model: str, timeout_s: int) -> None:
        self._executor = executor
        self._model = model  # validated in config; bound as a parameter, never interpolated
        self._timeout_s = timeout_s

    async def complete_json(self, messages: list[dict[str, str]]) -> Any:
        rows = await self._executor.execute(
            "SELECT AI_COMPLETE(?, ?) AS REPLY", [self._model, flatten_messages(messages)], self._timeout_s
        )
        value = next(iter(rows[0].values()), None) if rows else None
        if isinstance(value, str) and value.startswith('"'):
            try:  # AI_COMPLETE's string can arrive JSON-encoded
                value = json.loads(value)
            except ValueError:
                pass
        if not isinstance(value, str) or not value.strip():
            raise upstream_invalid("cursor", "model returned no text")
        parsed = extract_json(value)
        if parsed is None:
            raise upstream_invalid("cursor", "reply was not valid JSON")
        return parsed

    async def aclose(self) -> None:
        return None  # the shared Snowflake executor is closed by the container
