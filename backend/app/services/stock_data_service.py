from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from datetime import date, datetime, timedelta
from typing import Any

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS
from app.models.stock import (
    PeerComparisonItem,
    PeerComparisonResponse,
    ProviderStatus,
    StockFinancialResponse,
    StockKlineResponse,
    StockSummary,
)
from app.services import cache_service
from app.services.akshare_provider import AkshareProvider, ProviderError
from app.services.baostock_provider import BaostockProvider
from app.services.efinance_provider import EfinanceProvider
from app.services.financial_snapshot import enrich_summary, financial_rows_from_snapshot
from app.services.sina_provider import SinaProvider
from app.services.tushare_provider import TushareProvider


class StockDataService:
    def __init__(
        self,
        provider: AkshareProvider | None = None,
        kline_provider: BaostockProvider | None = None,
        realtime_provider: EfinanceProvider | None = None,
        sina_provider: SinaProvider | None = None,
        tushare_provider: TushareProvider | None = None,
    ) -> None:
        self.provider = provider or AkshareProvider()
        self.kline_provider = kline_provider or BaostockProvider()
        self.realtime_provider = realtime_provider or EfinanceProvider()
        self.sina_provider = sina_provider or SinaProvider()
        self.tushare_provider = tushare_provider or TushareProvider()

    def provider_status(self) -> ProviderStatus:
        try:
            self.provider._ak()
            return ProviderStatus(name=self.provider.name, available=True)
        except ProviderError as exc:
            return ProviderStatus(name=self.provider.name, available=False, detail=str(exc))

    def get_summary(self, code: str, force_refresh: bool = False) -> StockSummary:
        normalized_code = code.strip()
        cache_key = f"stock-summary:v6:{normalized_code}"

        cached = cache_service.get_json(cache_key)
        if cached is not None and not force_refresh:
            cached["warnings"] = [*cached.get("warnings", []), "served_from_cache"]
            return StockSummary(**cached)

        warnings: list[str] = []
        for provider_name, fn in [
            (self.sina_provider.name, self.sina_provider.get_stock_summary),
            (self.realtime_provider.name, self.realtime_provider.get_stock_summary),
            (self.provider.name, self.provider.get_stock_summary),
        ]:
            try:
                payload = self._call_provider(fn, normalized_code, provider_name=provider_name)
                payload.setdefault("industry", None)
                payload.setdefault("ps", None)
                payload["source"] = payload.get("source") or provider_name
                payload = self._enrich_summary_with_tushare(normalized_code, payload, warnings)
                payload = self._enrich_summary_with_efinance_base(normalized_code, payload, warnings)
                payload["warnings"] = warnings
                payload = enrich_summary(payload)
                cache_service.set_json(cache_key, payload)
                return StockSummary(**payload)
            except ProviderError as exc:
                warnings.append(str(exc))

        empty_payload = {
            "code": normalized_code,
            "name": None,
            "industry": None,
            "latest_price": None,
            "change_pct": None,
            "pe_ttm": None,
            "pb": None,
            "ps": None,
            "market_cap": None,
            "float_market_cap": None,
            "data_time": datetime.now().astimezone().isoformat(),
            "source": "multi_provider",
            "warnings": warnings,
            "raw_fields": {},
        }
        if force_refresh and cached is not None:
            cached["warnings"] = [*cached.get("warnings", []), "refresh_failed_served_from_cache"]
            return StockSummary(**cached)
        empty_payload = self._enrich_summary_with_tushare(normalized_code, empty_payload, warnings)
        empty_payload = self._enrich_summary_with_efinance_base(normalized_code, empty_payload, warnings)
        empty_payload = enrich_summary(empty_payload)
        return StockSummary(**empty_payload)

    def get_kline(self, code: str, period: str = "daily", days: int = 365, force_refresh: bool = False) -> StockKlineResponse:
        normalized_code = code.strip()
        normalized_period = period.strip() or "daily"
        normalized_days = max(1, min(days, 3650))
        cache_key = f"stock-kline:v2:{normalized_code}:{normalized_period}:{normalized_days}"

        cached = cache_service.get_json(cache_key)
        if cached is not None and not force_refresh:
            cached["warnings"] = [*cached.get("warnings", []), "served_from_cache"]
            return StockKlineResponse(**cached)

        end = date.today()
        start = end - timedelta(days=normalized_days)
        start_ak = start.strftime("%Y%m%d")
        end_ak = end.strftime("%Y%m%d")
        warnings: list[str] = []

        providers = []
        if normalized_period == "daily":
            providers.append((self.sina_provider.name, self.sina_provider.get_kline))
            providers.append((self.realtime_provider.name, self.realtime_provider.get_kline))
            providers.append((self.kline_provider.name, self.kline_provider.get_kline))
        providers.append((self.provider.name, self.provider.get_kline))

        for provider_name, fn in providers:
            try:
                rows = self._call_provider(fn, normalized_code, normalized_period, start_ak, end_ak, provider_name=provider_name)
                if not rows:
                    warnings.append(f"{provider_name}_returned_empty_kline")
                    continue
                payload = {
                    "code": normalized_code,
                    "period": normalized_period,
                    "points": rows,
                    "source": provider_name,
                    "warnings": warnings,
                }
                cache_service.set_json(cache_key, payload)
                return StockKlineResponse(**payload)
            except ProviderError as exc:
                warnings.append(str(exc))

        if force_refresh and cached is not None:
            cached["warnings"] = [*cached.get("warnings", []), "refresh_failed_served_from_cache"]
            return StockKlineResponse(**cached)
        return StockKlineResponse(
            code=normalized_code,
            period=normalized_period,
            points=[],
            source="multi_provider",
            warnings=warnings,
        )

    def get_financial(self, code: str, force_refresh: bool = False) -> StockFinancialResponse:
        normalized_code = code.strip()
        cache_key = f"stock-financial:v5:{normalized_code}"

        cached = cache_service.get_json(cache_key)
        if cached is not None and not force_refresh:
            cached["warnings"] = [*cached.get("warnings", []), "served_from_cache"]
            return StockFinancialResponse(**cached)

        warnings: list[str] = []
        try:
            rows = self._call_provider(self.provider.get_financial_indicators, normalized_code, provider_name=self.provider.name)
            if rows:
                payload = {
                    "code": normalized_code,
                    "rows": rows[:20],
                    "source": self.provider.name,
                    "warnings": warnings,
                }
                cache_service.set_json(cache_key, payload)
                return StockFinancialResponse(**payload)
            warnings.append("akshare_returned_empty_financial")
        except ProviderError as exc:
            warnings.append(str(exc))

        if self.tushare_provider.token:
            try:
                rows = self._call_provider(self.tushare_provider.get_financial_indicators, normalized_code, provider_name=self.tushare_provider.name)
                if rows:
                    payload = {
                        "code": normalized_code,
                        "rows": rows[:20],
                        "source": self.tushare_provider.name,
                        "warnings": [*warnings, "used_tushare"],
                    }
                    cache_service.set_json(cache_key, payload)
                    return StockFinancialResponse(**payload)
                warnings.append("tushare_returned_empty_financial")
            except ProviderError as exc:
                warnings.append(str(exc))

        try:
            rows = self._call_provider(self.realtime_provider.get_financial_indicators, normalized_code, provider_name=self.realtime_provider.name)
            if rows:
                payload = {
                    "code": normalized_code,
                    "rows": rows[:20],
                    "source": "efinance_base_info",
                    "warnings": [*warnings, "used_efinance_base_info"],
                }
                cache_service.set_json(cache_key, payload)
                return StockFinancialResponse(**payload)
            warnings.append("efinance_returned_empty_financial")
        except ProviderError as exc:
            warnings.append(str(exc))

        snapshot_rows = financial_rows_from_snapshot(normalized_code)
        if snapshot_rows:
            payload = {
                "code": normalized_code,
                "rows": snapshot_rows,
                "source": "local_financial_snapshot",
                "warnings": [*warnings, "used_local_financial_snapshot"],
            }
            cache_service.set_json(cache_key, payload)
            return StockFinancialResponse(**payload)

        if force_refresh and cached is not None:
            cached["warnings"] = [*cached.get("warnings", []), "refresh_failed_served_from_cache"]
            return StockFinancialResponse(**cached)
        return StockFinancialResponse(
            code=normalized_code,
            rows=[],
            source="multi_provider",
            warnings=warnings,
        )


    def compare(self, codes: list[str]) -> PeerComparisonResponse:
        normalized_codes = list(dict.fromkeys(code.strip() for code in codes if code.strip()))[:8]
        items_by_code: dict[str, PeerComparisonItem] = {}
        warnings: list[str] = []

        def load_item(code: str) -> PeerComparisonItem:
            summary = self.get_summary(code)
            financial = self.get_financial(code)
            latest = financial.rows[0] if financial.rows else None
            return PeerComparisonItem(
                code=code,
                name=summary.name,
                industry=summary.industry,
                latest_price=summary.latest_price,
                change_pct=summary.change_pct,
                pe_ttm=summary.pe_ttm,
                pb=summary.pb,
                ps=summary.ps,
                market_cap=summary.market_cap,
                roe=latest.roe if latest else None,
                gross_margin=latest.gross_margin if latest else None,
                debt_ratio=latest.debt_ratio if latest else None,
                report_date=latest.report_date if latest else None,
                source=f"{summary.source} / {financial.source}",
                warnings=[*summary.warnings, *financial.warnings],
            )

        with ThreadPoolExecutor(max_workers=min(4, len(normalized_codes) or 1)) as executor:
            futures = {executor.submit(load_item, code): code for code in normalized_codes}
            for future in as_completed(futures):
                code = futures[future]
                try:
                    items_by_code[code] = future.result()
                except Exception as exc:
                    warnings.append(f"{code}_comparison_failed: {exc}")

        return PeerComparisonResponse(
            items=[items_by_code[code] for code in normalized_codes if code in items_by_code],
            warnings=warnings,
        )
    def _enrich_summary_with_tushare(self, code: str, payload: dict[str, Any], warnings: list[str]) -> dict[str, Any]:

        needs_tushare = any(payload.get(key) is None for key in ["name", "industry", "pe_ttm", "pb", "ps", "market_cap", "float_market_cap"])
        if not self.tushare_provider.token or not needs_tushare:
            return payload
        try:
            base = self._call_provider(self.tushare_provider.get_stock_summary, code, provider_name=self.tushare_provider.name)
        except ProviderError as exc:
            warnings.append(str(exc))
            return payload

        enriched = dict(payload)
        raw_fields = dict(enriched.get("raw_fields") or {})
        filled = False
        for key in ["name", "industry", "pe_ttm", "pb", "ps", "market_cap", "float_market_cap"]:
            if enriched.get(key) is None and base.get(key) is not None:
                enriched[key] = base[key]
                filled = True
        raw_fields["tushare"] = base.get("raw_fields") or {}
        enriched["raw_fields"] = raw_fields
        if filled:
            warnings.append("used_tushare")
        return enriched
    def _enrich_summary_with_efinance_base(self, code: str, payload: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        needs_base = any(payload.get(key) is None for key in ["name", "industry", "pe_ttm", "pb", "market_cap", "float_market_cap"])
        if not needs_base:
            return payload
        try:
            base = self._call_provider(self.realtime_provider.get_base_info, code, provider_name=self.realtime_provider.name)
        except ProviderError as exc:
            warnings.append(str(exc))
            return payload

        enriched = dict(payload)
        raw_fields = dict(enriched.get("raw_fields") or {})
        for key in ["name", "industry", "pe_ttm", "pb", "market_cap", "float_market_cap"]:
            if enriched.get(key) is None and base.get(key) is not None:
                enriched[key] = base[key]
        raw_fields["efinance_base_info"] = base.get("raw_fields") or {}
        enriched["raw_fields"] = raw_fields
        warnings.append("used_efinance_base_info")
        return enriched

    def _call_provider_summary(self, code: str) -> dict:
        return self._call_provider(self.provider.get_stock_summary, code)

    def _call_provider(self, fn, *args, provider_name: str | None = None):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(fn, *args)
        try:
            return future.result(timeout=DEFAULT_PROVIDER_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            future.cancel()
            raise ProviderError(
                f"{provider_name or self.provider.name} query timed out after "
                f"{DEFAULT_PROVIDER_TIMEOUT_SECONDS:g}s"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)




















