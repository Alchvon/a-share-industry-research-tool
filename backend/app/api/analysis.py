from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.analysis import (
    AnalysisBackupImportRequest,
    AnalysisBackupImportResponse,
    AnalysisDetail,
    AnalysisRecord,
    CreateAnalysisRequest,
    CreateAnalysisResponse,
)
from app.services.analysis_service import AnalysisService


router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analysis", response_model=CreateAnalysisResponse)
def create_analysis(payload: CreateAnalysisRequest) -> CreateAnalysisResponse:
    record = AnalysisService().create(payload.keyword)
    return CreateAnalysisResponse(
        analysis_id=record.id,
        keyword=record.keyword,
        status=record.status,
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: str) -> AnalysisDetail:
    detail = AnalysisService().get(analysis_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return detail


@router.get("/history", response_model=list[AnalysisRecord])
def history(limit: int = Query(default=20, ge=1, le=100)) -> list[AnalysisRecord]:
    return AnalysisService().list_recent(limit=limit)
@router.delete("/analysis/{analysis_id}")
def delete_analysis(analysis_id: str) -> dict[str, bool]:
    deleted = AnalysisService().delete(analysis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="analysis not found")
    return {"deleted": True}




@router.get("/analysis/{analysis_id}/backup")
def export_analysis_backup(analysis_id: str) -> dict[str, object]:
    backup = AnalysisService().export_backup(analysis_id)
    if backup is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return backup


@router.post("/analysis/import", response_model=AnalysisBackupImportResponse)
def import_analysis_backup(payload: AnalysisBackupImportRequest) -> AnalysisBackupImportResponse:
    try:
        record, node_count, candidate_count, report_count = AnalysisService().import_backup(payload.backup)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AnalysisBackupImportResponse(
        analysis_id=record.id,
        keyword=record.keyword,
        imported_nodes=node_count,
        imported_candidates=candidate_count,
        imported_reports=report_count,
    )
