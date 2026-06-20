from __future__ import annotations

from fastapi import APIRouter

from app.services.local_knowledge import supported_topics


router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/topics")
def topics() -> dict[str, object]:
    return {"topics": supported_topics()}
