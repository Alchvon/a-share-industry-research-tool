from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.llm import LlmApiConfig


class CreateAnalysisRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=80)


class AnalysisRecord(BaseModel):
    id: str
    keyword: str
    status: str
    created_at: datetime
    updated_at: datetime


class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    keyword: str
    status: str


class IndustryNode(BaseModel):
    id: str
    analysis_id: str
    parent_id: str | None = None
    name: str
    level: int
    description: str
    match_keywords: list[str]
    sort_order: int


class DecomposeIndustryRequest(BaseModel):
    analysis_id: str | None = None
    keyword: str = Field(..., min_length=1, max_length=80)
    api_config: LlmApiConfig = Field(default_factory=LlmApiConfig)


class DecomposeIndustryResponse(BaseModel):
    keyword: str
    nodes: list[IndustryNode]
    source: str
    warnings: list[str] = Field(default_factory=list)


class UpsertIndustryNodeRequest(BaseModel):
    analysis_id: str
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=300)
    match_keywords: list[str] = Field(default_factory=list)
    level: int = Field(default=1, ge=1, le=3)
    parent_id: str | None = None


class UpdateIndustryNodeRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    match_keywords: list[str] | None = None
    level: int | None = Field(default=None, ge=1, le=3)
    parent_id: str | None = None


class AnalysisDetail(BaseModel):
    analysis: AnalysisRecord
    nodes: list[IndustryNode]



class AnalysisBackupImportRequest(BaseModel):
    backup: dict[str, Any]


class AnalysisBackupImportResponse(BaseModel):
    analysis_id: str
    keyword: str
    imported_nodes: int
    imported_candidates: int
    imported_reports: int
