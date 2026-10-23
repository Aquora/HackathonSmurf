import re
import uuid

from fastapi import FastAPI, Request

from app.adapters.fixture_catalog import FixtureCandidateSource
from app.adapters.fixture_routing import StraightLineRouter
from app.adapters.memory_store import InMemoryQuestStore
from app.ai.template_planner import TemplatePlanner
from app.config import Settings, get_settings
from app.errors import install_error_handlers
from app.routes import health, quests
from app.services.quest_service import QuestService

_CLIENT_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def build_quest_service(settings: Settings) -> QuestService:
    # Only fixture adapters exist so far; live Snowflake/model/routing adapters plug in here.
    return QuestService(
        candidates=FixtureCandidateSource(),
        planner=TemplatePlanner(),
        router=StraightLineRouter(),
        store=InMemoryQuestStore(),
    )


def create_app(
    settings: Settings | None = None, quest_service: QuestService | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Local Quest API", version="0.1.0")
    app.state.settings = settings
    app.state.quest_service = quest_service or build_quest_service(settings)

    @app.middleware("http")
    async def assign_request_id(request: Request, call_next):
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _CLIENT_REQUEST_ID.match(supplied) else f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(quests.router)
    return app


app = create_app()
