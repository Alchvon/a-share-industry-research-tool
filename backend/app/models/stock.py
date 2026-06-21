from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StockSummary(BaseModel):
    code: str
    name: str | None = None
    industry: str | None = None
    latest_price: float | None = None
    change_pct: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
    market_cap: float | None = None
    float_market_cap: float | None = None
    data_time: datetime
    source: str
    warnings: list[str] = Field(default_factory=list)
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class ProviderStatus(BaseModel):
    name: str
    available: bool
    detail: str | None = None


class KlinePoint(BaseModel):
    date: str
    open: float | None = None
    close: float | None = None
    high: float | None = None
    low: float | None = None
    volume: float | None = None
    amount: float | None = None
    change_pct: float | None = None


class StockKlineResponse(BaseModel):
    code: str
    period: str
    points: list[KlinePoint]
    source: str
    warnings: list[str] = Field(default_factory=list)


class FinancialMetricRow(BaseModel):
    report_date: str
    revenue: float | None = None
    net_profit: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_ratio: float | None = None
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None
    total_debt: float | None = None
    cash_balance: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class StockFinancialResponse(BaseModel):
    code: str
    rows: list[FinancialMetricRow]
    source: str
    warnings: list[str] = Field(default_factory=list)


class CashflowTrendPoint(BaseModel):
    report_date: str
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    kind: str = "historical"
    assumption: str | None = None


class CashflowAssessment(BaseModel):
    signal: str
    text: str
    projection_method: str
    points: list[CashflowTrendPoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DebtAssessment(BaseModel):
    signal: str
    text: str
    debt_ratio: float | None = None
    total_debt: float | None = None
    cash_balance: float | None = None
    net_debt: float | None = None
    current_ratio: float | None = None
    interest_coverage: float | None = None
    report_date: str | None = None
    warnings: list[str] = Field(default_factory=list)


class CompanyResearchResponse(BaseModel):
    code: str
    summary: StockSummary
    financial: StockFinancialResponse
    cashflow: CashflowAssessment
    debt: DebtAssessment
    warnings: list[str] = Field(default_factory=list)


class PeerComparisonItem(BaseModel):
    code: str
    name: str | None = None
    industry: str | None = None
    latest_price: float | None = None
    change_pct: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
    market_cap: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    debt_ratio: float | None = None
    report_date: str | None = None
    source: str
    warnings: list[str] = Field(default_factory=list)


class PeerComparisonResponse(BaseModel):
    items: list[PeerComparisonItem]
    warnings: list[str] = Field(default_factory=list)



