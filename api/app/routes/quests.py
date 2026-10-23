from fastapi import APIRouter, Request

from app.domain.normalization import QuestRequest, normalize
from app.domain.quest import Quest
from app.errors import request_id_of

router = APIRouter(prefix="/v1")


@router.post("/quests", status_code=201, response_model_by_alias=True)
def create_quest(body: QuestRequest, request: Request) -> Quest:
    normalized = normalize(body, request.app.state.settings)
    return request.app.state.quest_service.create(request_id_of(request), normalized)
