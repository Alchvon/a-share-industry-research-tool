from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CompanyCandidate(BaseModel):
    id: str
    analysis_id: str
    industry_node_id: str
    stock_code: str
    stock_name: str
    reason: str | None = None
    market_cap: float | None = None
    revenue: float | None = None
    roe: float | None = None
    score: float | None = None
    is_user_selected: bool = True
    match_source: str | None = None
    score_details: dict[str, Any] = Field(default_factory=dict)


class MatchCompanyRequest(BaseModel):
    analysis_id: str
    industry_node_ids: list[str] | None = None
    limit_per_node: int = Field(default=5, ge=1, le=10)


class MatchCompanyResponse(BaseModel):
    analysis_id: str
    candidates: list[CompanyCandidate]
    source: str
    warnings: list[str] = Field(default_factory=list)


class CreateCompanyCandidateRequest(BaseModel):
    analysis_id: str
    industry_node_id: str
    stock_code: str = Field(..., min_length=6, max_length=6)
    stock_name: str = Field(..., min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=300)
    market_cap: float | None = None
    revenue: float | None = None
    roe: float | None = None
    score: float | None = Field(default=50, ge=0, le=100)


class UpdateCompanyCandidateRequest(BaseModel):
    industry_node_id: str | None = None
    stock_code: str | None = Field(default=None, min_length=6, max_length=6)
    stock_name: str | None = Field(default=None, min_length=1, max_length=80)
    reason: str | None = Field(default=None, max_length=300)
    market_cap: float | None = None
    revenue: float | None = None
    roe: float | None = None
    score: float | None = Field(default=None, ge=0, le=100)
    is_user_selected: bool | None = None

