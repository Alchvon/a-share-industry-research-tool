from __future__ import annotations

from datetime import datetime
from typing import Any

SNAPSHOTS: dict[str, dict[str, Any]] = {
    "600600": {"name": "青岛啤酒", "pe_ttm": 24.0, "pb": 3.1, "ps": 3.2, "market_cap": 98000000000, "roe": 14.5, "gross_margin": 38.0, "debt_ratio": 42.0, "net_profit": 4300000000, "revenue": 34000000000, "dividend_yield": 2.1},
    "600132": {"name": "重庆啤酒", "pe_ttm": 22.0, "pb": 18.0, "ps": 4.0, "market_cap": 30000000000, "roe": 45.0, "gross_margin": 50.0, "debt_ratio": 58.0, "net_profit": 1300000000, "revenue": 15000000000, "dividend_yield": 3.0},
    "000729": {"name": "燕京啤酒", "pe_ttm": 28.0, "pb": 2.6, "ps": 2.2, "market_cap": 30000000000, "roe": 8.5, "gross_margin": 42.0, "debt_ratio": 34.0, "net_profit": 900000000, "revenue": 14000000000, "dividend_yield": 1.2},
    "002461": {"name": "珠江啤酒", "pe_ttm": 27.0, "pb": 2.4, "ps": 3.5, "market_cap": 18000000000, "roe": 8.8, "gross_margin": 45.0, "debt_ratio": 25.0, "net_profit": 650000000, "revenue": 5500000000, "dividend_yield": 1.6},
    "600573": {"name": "惠泉啤酒", "pe_ttm": 45.0, "pb": 2.9, "ps": 4.2, "market_cap": 3000000000, "roe": 5.5, "gross_margin": 31.0, "debt_ratio": 18.0, "net_profit": 65000000, "revenue": 700000000, "dividend_yield": 0.8},
    "601865": {"name": "福莱特", "pe_ttm": 18.0, "pb": 2.2, "ps": 2.0, "market_cap": 52000000000, "roe": 12.0, "gross_margin": 22.0, "debt_ratio": 56.0, "net_profit": 2800000000, "revenue": 21000000000, "dividend_yield": 1.1},
    "000001": {"name": "平安银行", "pe_ttm": 4.5, "pb": 0.45, "ps": 1.1, "market_cap": 205000000000, "roe": 10.5, "gross_margin": None, "debt_ratio": None, "net_profit": 46000000000, "revenue": 165000000000, "dividend_yield": 2.8},
}


def enrich_summary(summary: dict[str, Any]) -> dict[str, Any]:
    code = str(summary.get("code") or "").strip()
    snapshot = SNAPSHOTS.get(code)
    if not snapshot:
        return summary
    enriched = dict(summary)
    raw_fields = dict(enriched.get("raw_fields") or {})
    filled = False
    for key in ["name", "pe_ttm", "pb", "ps", "market_cap"]:
        if enriched.get(key) is None and snapshot.get(key) is not None:
            enriched[key] = snapshot[key]
            filled = True
    warnings = list(enriched.get("warnings") or [])
    if filled:
        warnings.append("used_local_financial_snapshot")
    raw_fields["local_financial_snapshot"] = snapshot
    enriched["warnings"] = warnings
    enriched["raw_fields"] = raw_fields
    return enriched


def financial_rows_from_snapshot(code: str) -> list[dict[str, Any]]:
    snapshot = SNAPSHOTS.get(str(code).strip())
    if not snapshot:
        return []
    return [
        {
            "report_date": datetime.now().date().isoformat(),
            "revenue": snapshot.get("revenue"),
            "net_profit": snapshot.get("net_profit"),
            "roe": snapshot.get("roe"),
            "gross_margin": snapshot.get("gross_margin"),
            "debt_ratio": snapshot.get("debt_ratio"),
            "operating_cash_flow": snapshot.get("operating_cash_flow"),
            "capital_expenditure": snapshot.get("capital_expenditure"),
            "free_cash_flow": snapshot.get("free_cash_flow"),
            "total_debt": snapshot.get("total_debt"),
            "cash_balance": snapshot.get("cash_balance"),
            "current_ratio": snapshot.get("current_ratio"),
            "interest_coverage": snapshot.get("interest_coverage"),
            "raw_fields": {"source": "local_financial_snapshot", **snapshot},
        }
    ]



