import asyncio
import json
import random
import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ...errors import AppError, upstream_invalid, upstream_timeout, upstream_unavailable

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Parse JSON from a model reply, tolerating Markdown code fences and surrounding prose. Returns None if absent."""
    candidates = [text.strip()]
    fenced = _FENCE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except ValueError:
            continue
    return None


def _backoff_seconds(attempt: int) -> float:
    base = 0.25 * 2 ** (attempt - 1)
    return base + random.random() * base


class JsonChatClient:
    """Client for an OpenAI-compatible `/chat/completions` endpoint that returns the reply parsed as JSON.

    Retries are bounded and only apply to transient failures.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_s: float,
        max_retries: int,
        json_mode: bool,
        http: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._json_mode = json_mode
        self._http = http or httpx.AsyncClient(timeout=timeout_s)
        self._sleep = sleep

    async def aclose(self) -> None:
        await self._http.aclose()

    async def complete_json(self, messages: list[dict[str, str]]) -> Any:
        content = await self._complete(messages)
        parsed = extract_json(content)
        if parsed is None:
            raise upstream_invalid("cursor", "reply was not valid JSON")
        return parsed

    async def _complete(self, messages: list[dict[str, str]]) -> str:
        body: dict[str, Any] = {"model": self._model, "messages": messages, "temperature": 0.2}
        if self._json_mode:
            body["response_format"] = {"type": "json_object"}
        headers = {"authorization": f"Bearer {self._api_key}"}

        last_error: AppError = upstream_unavailable("cursor")
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await self._sleep(_backoff_seconds(attempt))
            try:
                res = await self._http.post(self._url, json=body, headers=headers)
            except httpx.TimeoutException:
                last_error = upstream_timeout("cursor")
                continue
            except httpx.HTTPError:
                last_error = upstream_unavailable("cursor")
                continue

            if res.status_code >= 400:
                # Never include the upstream body in errors: it may echo prompts or keys.
                last_error = upstream_unavailable("cursor")
                if res.status_code in RETRYABLE_STATUS:
                    continue
                raise last_error

            try:
                payload = res.json()
            except ValueError:
                raise upstream_invalid("cursor", "response body was not JSON") from None
            try:
                content = payload["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                content = None
            if not isinstance(content, str) or not content.strip():
                raise upstream_invalid("cursor", "response had no message content")
            return content
        raise last_error
