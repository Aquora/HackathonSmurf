import json
import re
from typing import Any, Protocol

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


class JsonChatClient(Protocol):
    """A model client: takes chat messages and returns the reply parsed as JSON."""

    async def complete_json(self, messages: list[dict[str, str]]) -> Any: ...

    async def aclose(self) -> None: ...


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
