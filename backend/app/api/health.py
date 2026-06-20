from __future__ import annotations

from fastapi import APIRouter

from app.services.stock_data_service import StockDataService


router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    service = StockDataService()
    return {
        "ok": True,
        "provider": service.provider_status().model_dump(),
    }

