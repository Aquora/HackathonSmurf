from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness only; does not claim upstream providers are ready."""
    return {"status": "ok"}
