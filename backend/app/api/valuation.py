from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.valuation_service import build_valuation_snapshot


router = APIRouter(prefix="/api/valuation", tags=["valuation"])


class ValuationRequest(BaseModel):
    stock_summary: dict[str, Any] | None = None
    stock_financial: dict[str, Any] | None = None
    stock_kline: dict[str, Any] | None = None


@router.post("/calculate")
def calculate(payload: ValuationRequest) -> dict[str, Any]:
    return build_valuation_snapshot(payload.stock_summary, payload.stock_financial, payload.stock_kline)
