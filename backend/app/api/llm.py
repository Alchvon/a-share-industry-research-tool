from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import DEFAULT_LLM_API_KEY, DEFAULT_LLM_ENDPOINT, DEFAULT_LLM_MODEL
from app.models.llm import AnalyzeRequest, AnalyzeResponse, SavedReport, SavedReportListResponse
from app.services.llm_service import LlmService


router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/config-status")
def config_status() -> dict[str, object]:
    """Return only non-secret machine-default status for the local UI."""
    return {
        "machine_default_available": bool(DEFAULT_LLM_API_KEY),
        "endpoint": DEFAULT_LLM_ENDPOINT if DEFAULT_LLM_API_KEY else None,
        "model": DEFAULT_LLM_MODEL if DEFAULT_LLM_API_KEY else None,
    }


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return LlmService().analyze(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc





@router.get("/reports", response_model=SavedReportListResponse)
def saved_reports(
    analysis_id: str = Query(..., min_length=1),
    stock_code: str | None = Query(default=None, min_length=6, max_length=6),
) -> SavedReportListResponse:
    reports = [SavedReport(**item) for item in LlmService().list_reports(analysis_id, stock_code)]
    return SavedReportListResponse(reports=reports)
