from __future__ import annotations

import json
import re
from typing import Any

import requests

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS
from app.services.akshare_provider import ProviderError


class SinaProvider:
    name = "sina"

    def __init__(self, timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def available(self) -> tuple[bool, str | None]:
        return True, "jsonp_kline"

    def get_stock_summary(self, code: str) -> dict[str, Any]:
        symbol = _to_sina_symbol(code)
        url = "https://hq.sinajs.cn/list=" + symbol
        try:
            response = requests.get(
                url,
                headers={"Referer": "https://finance.sina.com.cn"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response.encoding = "gb18030"
            values = _extract_realtime_values(response.text)
        except Exception as exc:
            raise ProviderError(f"Sina realtime quote query failed: {exc}") from exc

        latest = _number_at(values, 3)
        previous_close = _number_at(values, 2)
        change_pct = None
        if latest is not None and previous_close not in (None, 0):
            change_pct = (latest - previous_close) / previous_close * 100
        return {
            "code": code,
            "name": values[0] if values else None,
            "latest_price": latest,
            "change_pct": change_pct,
            "pe_ttm": None,
            "pb": None,
            "market_cap": None,
            "float_market_cap": None,
            "data_time": _realtime_time(values),
            "source": self.name,
            "raw_fields": {"sina_values": values[:40]},
        }
    def get_kline(
        self,
        code: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        if period != "daily":
            raise ProviderError("Sina provider currently supports daily kline only")
        symbol = _to_sina_symbol(code)
        url = (
            "https://quotes.sina.cn/cn/api/jsonp_v2.php/var%20kline=/"
            "CN_MarketDataService.getKLineData"
        )
        try:
            response = requests.get(
                url,
                params={"symbol": symbol, "scale": 240, "ma": "no", "datalen": 1200},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = _extract_jsonp_array(response.text)
        except Exception as exc:
            raise ProviderError(f"Sina kline query failed: {exc}") from exc

        rows: list[dict[str, Any]] = []
        start_iso = _to_iso_date(start_date)
        end_iso = _to_iso_date(end_date)
        for raw in payload:
            day = str(raw.get("day") or "")[:10]
            if not day or day < start_iso or day > end_iso:
                continue
            rows.append(
                {
                    "date": day,
                    "open": _number(raw.get("open")),
                    "close": _number(raw.get("close")),
                    "high": _number(raw.get("high")),
                    "low": _number(raw.get("low")),
                    "volume": _number(raw.get("volume")),
                    "amount": _number(raw.get("amount")),
                    "change_pct": None,
                }
            )
        return rows



def _extract_realtime_values(text: str) -> list[str]:
    match = re.search(r'="(.*)";?\s*$', text.strip(), flags=re.S)
    if not match:
        raise ValueError("unexpected Sina realtime payload")
    return match.group(1).split(",")


def _number_at(values: list[str], index: int) -> float | None:
    if index >= len(values):
        return None
    return _number(values[index])


def _realtime_time(values: list[str]) -> str:
    if len(values) > 31 and values[30] and values[31]:
        return f"{values[30]}T{values[31]}"
    return datetime.now().astimezone().isoformat()

def _to_sina_symbol(code: str) -> str:
    normalized = code.strip()
    if normalized.startswith(("sh", "sz")):
        return normalized.replace(".", "")
    if normalized.startswith(("6", "9")):
        return f"sh{normalized}"
    return f"sz{normalized}"


def _extract_jsonp_array(text: str) -> list[dict[str, Any]]:
    match = re.search(r"=\s*\(?\s*(\[.*\])\s*\)?\s*;?\s*$", text.strip(), flags=re.S)
    if not match:
        raise ValueError("unexpected Sina JSONP payload")
    data = json.loads(match.group(1))
    if not isinstance(data, list):
        raise ValueError("Sina payload is not a list")
    return [item for item in data if isinstance(item, dict)]


def _to_iso_date(value: str) -> str:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    return text[:10]


def _number(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None



