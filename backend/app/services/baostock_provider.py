from __future__ import annotations

import socket
from datetime import datetime
from typing import Any

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS
from app.services.akshare_provider import ProviderError


class BaostockProvider:
    name = "baostock"

    def __init__(self, timeout_seconds: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def _bs(self) -> Any:
        try:
            import baostock as bs
        except ImportError as exc:
            raise ProviderError("Baostock is not installed") from exc
        return bs

    def available(self) -> tuple[bool, str | None]:
        try:
            bs = self._bs()
            return True, getattr(bs, "__version__", None)
        except ProviderError as exc:
            return False, str(exc)

    def get_kline(
        self,
        code: str,
        period: str,
        start_date: str,
        end_date: str,
        adjust: str = "qfq",
    ) -> list[dict[str, Any]]:
        if period != "daily":
            raise ProviderError("Baostock only supports daily kline in this app")

        bs_code = _to_baostock_code(code)
        bs_adjust = {"qfq": "2", "hfq": "1", "": "3", None: "3"}.get(adjust, "2")
        bs = self._bs()
        socket.setdefaulttimeout(self.timeout_seconds)
        login = bs.login()
        try:
            if getattr(login, "error_code", "0") != "0":
                raise ProviderError(f"Baostock login failed: {login.error_msg}")
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,code,open,high,low,close,volume,amount,pctChg,turn,peTTM,pbMRQ,psTTM",
                start_date=_to_iso_date(start_date),
                end_date=_to_iso_date(end_date),
                frequency="d",
                adjustflag=bs_adjust,
            )
            if getattr(rs, "error_code", "0") != "0":
                raise ProviderError(f"Baostock kline query failed: {rs.error_msg}")
            rows: list[dict[str, Any]] = []
            while rs.next():
                raw = dict(zip(rs.fields, rs.get_row_data()))
                rows.append(
                    {
                        "date": raw.get("date"),
                        "open": _number(raw.get("open")),
                        "close": _number(raw.get("close")),
                        "high": _number(raw.get("high")),
                        "low": _number(raw.get("low")),
                        "volume": _number(raw.get("volume")),
                        "amount": _number(raw.get("amount")),
                        "change_pct": _number(raw.get("pctChg")),
                    }
                )
            return [row for row in rows if row["date"]]
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Baostock kline query failed: {exc}") from exc
        finally:
            try:
                bs.logout()
            except Exception:
                pass


def _to_baostock_code(code: str) -> str:
    normalized = code.strip()
    if normalized.startswith(("sh.", "sz.")):
        return normalized
    if normalized.startswith(("6", "9")):
        return f"sh.{normalized}"
    return f"sz.{normalized}"


def _to_iso_date(value: str) -> str:
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text


def _number(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
