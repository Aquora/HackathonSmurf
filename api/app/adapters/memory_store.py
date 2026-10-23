"""Process-local quest store for development. Data is lost on restart."""

from threading import Lock

from app.domain.quest import Quest


class InMemoryQuestStore:
    def __init__(self) -> None:
        self._quests: dict[str, Quest] = {}
        self._lock = Lock()

    def save(self, quest: Quest) -> None:
        with self._lock:
            self._quests[quest.quest_id] = quest

    def get(self, quest_id: str) -> Quest | None:
        with self._lock:
            return self._quests.get(quest_id)
