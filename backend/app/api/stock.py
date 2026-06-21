from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query

from app.models.stock import CompanyResearchResponse, PeerComparisonResponse, StockFinancialResponse, StockKlineResponse, StockSummary
from app.services.company_research_service import CompanyResearchService
from app.services.stock_data_service import StockDataService


router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/{code}/summary", response_model=StockSummary)
def stock_summary(
    code: str = Path(..., min_length=6, max_length=6),
    refresh: bool = Query(default=False),
) -> StockSummary:
    service = StockDataService()
    return service.get_summary(code, force_refresh=refresh)


@router.get("/{code}/kline", response_model=StockKlineResponse)
def stock_kline(
    code: str = Path(..., min_length=6, max_length=6),
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    days: int = Query(default=365, ge=1, le=3650),
    refresh: bool = Query(default=False),
) -> StockKlineResponse:
    service = StockDataService()
    return service.get_kline(code, period=period, days=days, force_refresh=refresh)


@router.get("/{code}/financial", response_model=StockFinancialResponse)
def stock_financial(
    code: str = Path(..., min_length=6, max_length=6),
    refresh: bool = Query(default=False),
) -> StockFinancialResponse:
    service = StockDataService()
    return service.get_financial(code, force_refresh=refresh)



@router.get("/{code}/research", response_model=CompanyResearchResponse)
def company_research(
    code: str = Path(..., min_length=6, max_length=6),
    refresh: bool = Query(default=False),
) -> CompanyResearchResponse:
    return CompanyResearchService().get_research(code, force_refresh=refresh)


@router.get("/compare", response_model=PeerComparisonResponse)
def stock_compare(codes: str = Query(..., min_length=6, max_length=80)) -> PeerComparisonResponse:
    parsed_codes = list(dict.fromkeys(code.strip() for code in codes.replace("，", ",").split(",") if len(code.strip()) == 6))
    if not parsed_codes:
        raise HTTPException(status_code=400, detail="请提供至少一个六位股票代码")
    return StockDataService().compare(parsed_codes)



