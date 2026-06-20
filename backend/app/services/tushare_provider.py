from __future__ import annotations

from datetime import date
from typing import Any

from app.config import TUSHARE_TOKEN
from app.services.akshare_provider import ProviderError


class TushareProvider:
    name = "tushare"

    def __init__(self, token: str | None = None) -> None:
        self.token = (token or TUSHARE_TOKEN or "").strip()

    def available(self) -> tuple[bool, str | None]:
        if not self.token:
            return False, "未配置 STOCK_CHAIN_TUSHARE_TOKEN"
        try:
            import tushare as ts
        except ImportError as exc:
            return False, f"tushare is not installed: {exc}"
        return True, getattr(ts, "__version__", None)

    def _pro(self) -> Any:
        if not self.token:
            raise ProviderError("Tushare token is not configured")
        try:
            import tushare as ts
        except ImportError as exc:
            raise ProviderError("tushare is not installed") from exc
        try:
            ts.set_token(self.token)
            return ts.pro_api(self.token)
        except Exception as exc:
            raise ProviderError(f"Tushare init failed: {exc}") from exc

    def get_stock_summary(self, code: str) -> dict[str, Any]:
        pro = self._pro()
        ts_code = _ts_code(code)
        trade_date = _today_yyyymmdd()
        try:
            basic = pro.daily_basic(ts_code=ts_code, trade_date=trade_date)
            if basic is None or basic.empty:
                basic = pro.daily_basic(ts_code=ts_code)
            info = pro.stock_basic(ts_code=ts_code, fields="ts_code,name,industry")
        except Exception as exc:
            raise ProviderError(f"Tushare summary query failed: {exc}") from exc
        if basic is None or basic.empty:
            raise ProviderError(f"Tushare daily_basic returned empty for {code}")
        row = basic.iloc[0].to_dict()
        info_row = info.iloc[0].to_dict() if info is not None and not info.empty else {}
        return {
            "code": code,
            "name": _value_any(info_row, ["name"]),
            "industry": _value_any(info_row, ["industry"]),
            "latest_price": None,
            "change_pct": None,
            "pe_ttm": _number_any(row, ["pe_ttm", "pe"]),
            "pb": _number_any(row, ["pb"]),
            "ps": _number_any(row, ["ps_ttm", "ps"]),
            "market_cap": _scale_10000_to_yuan(_number_any(row, ["total_mv"])),
            "float_market_cap": _scale_10000_to_yuan(_number_any(row, ["circ_mv"])),
            "source": self.name,
            "raw_fields": {str(key): _jsonable(value) for key, value in {**row, **info_row}.items()},
        }

    def get_financial_indicators(self, code: str) -> list[dict[str, Any]]:
        pro = self._pro()
        ts_code = _ts_code(code)
        try:
            indicator = pro.fina_indicator(ts_code=ts_code, limit=8)
            income = pro.income(ts_code=ts_code, limit=8, fields="ts_code,end_date,revenue,n_income_attr_p")
        except Exception as exc:
            raise ProviderError(f"Tushare financial query failed: {exc}") from exc
        if indicator is None or indicator.empty:
            return []

        income_by_date: dict[str, dict[str, Any]] = {}
        if income is not None and not income.empty:
            for _, row in income.iterrows():
                raw = row.to_dict()
                end_date = _value_any(raw, ["end_date"])
                if end_date:
                    income_by_date[end_date] = raw

        rows: list[dict[str, Any]] = []
        for _, row in indicator.iterrows():
            raw = row.to_dict()
            end_date = _value_any(raw, ["end_date"])
            income_raw = income_by_date.get(end_date or "", {})
            rows.append(
                {
                    "report_date": _format_date(end_date),
                    "revenue": _number_any(income_raw, ["revenue"]),
                    "net_profit": _number_any(income_raw, ["n_income_attr_p"]),
                    "roe": _number_any(raw, ["roe", "roe_waa"]),
                    "gross_margin": _number_any(raw, ["grossprofit_margin"]),
                    "debt_ratio": _number_any(raw, ["debt_to_assets"]),
                    "raw_fields": {"source": "tushare", **{str(key): _jsonable(value) for key, value in {**raw, **income_raw}.items()}},
                }
            )
        return [row for row in rows if row["report_date"]]


def _ts_code(code: str) -> str:
    stripped = code.strip()
    suffix = "SH" if stripped.startswith(("6", "9")) else "SZ"
    return f"{stripped}.{suffix}"


def _today_yyyymmdd() -> str:
    return date.today().strftime("%Y%m%d")


def _format_date(value: str | None) -> str:
    if not value or len(value) != 8:
        return value or ""
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _scale_10000_to_yuan(value: float | None) -> float | None:
    return value * 10000 if value is not None else None


def _value_any(row: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() not in {"", "-", "nan", "None"}:
            return str(value).strip()
    return None


def _number_any(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None or str(value).strip() in {"", "-", "nan", "None"}:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _jsonable(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value
