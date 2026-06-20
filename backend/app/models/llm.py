from __future__ import annotations

from pydantic import BaseModel, Field


class LlmApiConfig(BaseModel):
    endpoint: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float = Field(default=0.1, ge=0, le=2)


class AnalyzeRequest(BaseModel):
    analysis_id: str
    stock_code: str = Field(..., min_length=6, max_length=6)
    report_type: str = Field(default="overview", max_length=40)
    api_config: LlmApiConfig = Field(default_factory=LlmApiConfig)
    stock_summary: dict | None = None
    stock_kline: dict | None = None
    stock_financial: dict | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    stock_code: str
    report_type: str
    markdown_report: str
    source: str
    warnings: list[str] = Field(default_factory=list)




class SavedReport(BaseModel):
    id: str
    analysis_id: str
    stock_code: str
    report_type: str
    markdown_report: str
    created_at: str


class SavedReportListResponse(BaseModel):
    reports: list[SavedReport] = Field(default_factory=list)
