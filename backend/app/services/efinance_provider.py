from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.akshare_provider import ProviderError


class EfinanceProvider:
    name = "efinance"

    def _stock(self) -> Any:
        try:
            import efinance as ef
        except ImportError as exc:
            raise ProviderError("efinance is not installed") from exc
        return ef.stock

    def available(self) -> tuple[bool, str | None]:
        try:
            import efinance as ef
            return True, getattr(ef, "__version__", None)
        except ImportError as exc:
            return False, str(exc)

    def get_stock_summary(self, code: str) -> dict[str, Any]:
        stock = self._stock()
        try:
            df = stock.get_latest_quote(code)
        except Exception as exc:
            raise ProviderError(f"efinance realtime quote query failed: {exc}") from exc
        if df is None or df.empty:
            raise ProviderError(f"efinance realtime quote returned empty for {code}")
        row = df.iloc[0].to_dict()
        return {
            "code": code,
            "name": _value_any(row, ["股票名称", "名称", "name"]),
            "latest_price": _number_any(row, ["最新价", "最新价格", "price"]),
            "change_pct": _number_any(row, ["涨跌幅", "涨跌幅(%)", "change_pct"]),
            "pe_ttm": _number_any(row, ["市盈率", "动态市盈率", "市盈率-动态"]),
            "pb": _number_any(row, ["市净率", "pb"]),
            "market_cap": _number_any(row, ["总市值", "market_cap"]),
            "float_market_cap": _number_any(row, ["流通市值", "float_market_cap"]),
            "data_time": datetime.now().astimezone().isoformat(),
            "source": self.name,
            "raw_fields": {str(key): _jsonable(value) for key, value in row.items()},
        }

    def get_base_info(self, code: str) -> dict[str, Any]:
        stock = self._stock()
        try:
            series = stock.get_base_info(code)
        except Exception as exc:
            raise ProviderError(f"efinance base info query failed: {exc}") from exc
        if series is None or getattr(series, "empty", False):
            raise ProviderError(f"efinance base info returned empty for {code}")
        row = series.to_dict() if hasattr(series, "to_dict") else dict(series)
        return {
            "code": code,
            "name": _value_any(row, ["股票名称", "名称", "name"]),
            "industry": _value_any(row, ["所处行业", "行业", "industry"]),
            "pe_ttm": _number_any(row, ["市盈率(动)", "市盈率", "动态市盈率", "pe_ttm"]),
            "pb": _number_any(row, ["市净率", "PB", "pb"]),
            "market_cap": _number_any(row, ["总市值", "market_cap"]),
            "float_market_cap": _number_any(row, ["流通市值", "float_market_cap"]),
            "net_profit": _number_any(row, ["净利润", "net_profit"]),
            "roe": _number_any(row, ["ROE", "roe"]),
            "gross_margin": _number_any(row, ["毛利率", "gross_margin"]),
            "net_margin": _number_any(row, ["净利率", "net_margin"]),
            "source": self.name,
            "raw_fields": {str(key): _jsonable(value) for key, value in row.items()},
        }

    def get_financial_indicators(self, code: str) -> list[dict[str, Any]]:
        info = self.get_base_info(code)
        return [
            {
                "report_date": datetime.now().date().isoformat(),
                "revenue": None,
                "net_profit": info.get("net_profit"),
                "roe": info.get("roe"),
                "gross_margin": info.get("gross_margin"),
                "debt_ratio": None,
                "operating_cash_flow": None,
                "capital_expenditure": None,
                "free_cash_flow": None,
                "total_debt": None,
                "cash_balance": None,
                "current_ratio": None,
                "interest_coverage": None,
                "raw_fields": {"source": "efinance_base_info", **(info.get("raw_fields") or {})},
            }
        ]

    def get_kline(
        self,
        code: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        stock = self._stock()
        period_map = {"daily": 101, "weekly": 102, "monthly": 103}
        try:
            df = stock.get_quote_history(
                code,
                beg=start_date,
                end=end_date,
                klt=period_map.get(period, 101),
                fqt=1 if adjust == "qfq" else 0,
            )
        except Exception as exc:
            raise ProviderError(f"efinance kline query failed: {exc}") from exc
        if df is None or df.empty:
            return []
        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            raw = row.to_dict()
            rows.append(
                {
                    "date": _value_any(raw, ["日期", "date"]),
                    "open": _number_any(raw, ["开盘", "open"]),
                    "close": _number_any(raw, ["收盘", "close"]),
                    "high": _number_any(raw, ["最高", "high"]),
                    "low": _number_any(raw, ["最低", "low"]),
                    "volume": _number_any(raw, ["成交量", "volume"]),
                    "amount": _number_any(raw, ["成交额", "amount"]),
                    "change_pct": _number_any(raw, ["涨跌幅", "change_pct"]),
                }
            )
        return [row for row in rows if row["date"]]


def _value_any(row: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() not in {"", "-"}:
            return str(value)
    return None


def _number_any(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = _number(row.get(key))
        if value is not None:
            return value
    return None


def _number(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _jsonable(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return value




