"""Stop tasks. Code, not the model, picks each stop's task so the choice is random and always valid."""

import random
from collections.abc import Sequence

from .locations import location_key
from .types import QUEST_TASKS, Location, QuestTask

# A model-written description longer than this is replaced with the fallback text.
DESCRIPTION_MAX_LENGTH = 500


def random_task(rng: random.Random | None = None) -> QuestTask:
    return (rng or random).choice(QUEST_TASKS)


def assign_tasks(locations: Sequence[Location], rng: random.Random | None = None) -> dict[str, QuestTask]:
    """Pick one random task per candidate location, keyed by location_key()."""
    return {location_key(loc.name, loc.address): random_task(rng) for loc in locations}


def fallback_description(location: Location, task: QuestTask) -> str:
    """Used when the model's description is missing or unusable. States only known facts."""
    return f"Stop by {location.name} at {location.address}. Your task: {task.text.rstrip('.')}."
