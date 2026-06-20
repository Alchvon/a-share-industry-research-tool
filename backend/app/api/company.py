from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models.company import (
    CompanyCandidate,
    CreateCompanyCandidateRequest,
    MatchCompanyRequest,
    MatchCompanyResponse,
    UpdateCompanyCandidateRequest,
)
from app.services.company_match_service import CompanyMatchService


router = APIRouter(prefix="/api/company", tags=["company"])


@router.get("", response_model=list[CompanyCandidate])
def list_companies(analysis_id: str = Query(...)) -> list[CompanyCandidate]:
    return CompanyMatchService().list_candidates(analysis_id)


@router.post("", response_model=CompanyCandidate)
def create_company(payload: CreateCompanyCandidateRequest) -> CompanyCandidate:
    return CompanyMatchService().create_candidate(payload)


@router.patch("/{candidate_id}", response_model=CompanyCandidate)
def update_company(candidate_id: str, payload: UpdateCompanyCandidateRequest) -> CompanyCandidate:
    candidate = CompanyMatchService().update_candidate(candidate_id, payload)
    if candidate is None:
        raise HTTPException(status_code=404, detail="candidate not found")
    return candidate


@router.delete("/{candidate_id}")
def delete_company(candidate_id: str) -> dict[str, bool]:
    deleted = CompanyMatchService().delete_candidate(candidate_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="candidate not found")
    return {"deleted": True}


@router.post("/match", response_model=MatchCompanyResponse)
def match_companies(payload: MatchCompanyRequest) -> MatchCompanyResponse:
    candidates, warnings, source = CompanyMatchService().match(
        analysis_id=payload.analysis_id,
        industry_node_ids=payload.industry_node_ids,
        limit_per_node=payload.limit_per_node,
    )
    if "analysis_not_found" in warnings:
        raise HTTPException(status_code=404, detail="analysis not found")

    return MatchCompanyResponse(
        analysis_id=payload.analysis_id,
        candidates=candidates,
        source=source,
        warnings=warnings,
    )
