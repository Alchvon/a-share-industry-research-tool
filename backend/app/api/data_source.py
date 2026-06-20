from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
from typing import Any, Callable

from fastapi import APIRouter, Query

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS
from app.services.akshare_provider import AkshareProvider, ProviderError
from app.services.baostock_provider import BaostockProvider
from app.services.efinance_provider import EfinanceProvider
from app.services.sina_provider import SinaProvider
from app.services.tushare_provider import TushareProvider


router = APIRouter(prefix="/api/data-source", tags=["data-source"])


@router.get("/diagnostics")
def diagnostics(include_remote: bool = Query(default=True)) -> dict[str, Any]:
    provider = AkshareProvider(timeout_seconds=min(DEFAULT_PROVIDER_TIMEOUT_SECONDS, 5))
    baostock_provider = BaostockProvider(timeout_seconds=min(DEFAULT_PROVIDER_TIMEOUT_SECONDS, 5))
    efinance_provider = EfinanceProvider()
    sina_provider = SinaProvider(timeout_seconds=min(DEFAULT_PROVIDER_TIMEOUT_SECONDS, 5))
    tushare_provider = TushareProvider()
    checks = [_check_package(provider), _check_baostock_package(baostock_provider), _check_efinance_package(efinance_provider), _check_sina_provider(sina_provider), _check_tushare_provider(tushare_provider)]
    tushare_available, _ = tushare_provider.available()
    if include_remote:
        checks.extend(
            [
                _run_check("A股实时行情", lambda: provider.get_spot_table().head(1).to_dict("records")),
                _run_check("概念板块列表", lambda: provider.get_concept_boards().head(1).to_dict("records")),
                _run_check("样例K线-Baostock", lambda: baostock_provider.get_kline("000001", "daily", "20250101", "20251231")[:1]),
                _run_check("样例K线-Sina", lambda: sina_provider.get_kline("000001", "daily", "20250101", "20251231")[:1]),
                _run_check("样例K线-efinance", lambda: efinance_provider.get_kline("000001", "daily", "20250101", "20251231")[:1]),
                _run_check("样例行情-efinance", lambda: [efinance_provider.get_stock_summary("000001")]),
                _run_check("样例K线-AKShare", lambda: provider.get_kline("000001", "daily", "20250101", "20251231")[:1]),
                _run_check("样例财务指标-AKShare", lambda: provider.get_financial_indicators("000001")[:1]),
                _run_check("样例财务指标-Tushare", lambda: tushare_provider.get_financial_indicators("000001")[:1]),
            ]
        )

    return {
        "provider": provider.name,
        "checked_at": datetime.now().astimezone().isoformat(),
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def _check_package(provider: AkshareProvider) -> dict[str, Any]:
    try:
        ak = provider._ak()
        return {
            "name": "AKShare Python包",
            "ok": True,
            "detail": f"已安装 {getattr(ak, '__version__', 'unknown')}",
        }
    except ProviderError as exc:
        return {"name": "AKShare Python包", "ok": False, "detail": str(exc)}



def _check_baostock_package(provider: BaostockProvider) -> dict[str, Any]:
    available, detail = provider.available()
    return {
        "name": "Baostock Python包",
        "ok": available,
        "detail": f"已安装 {detail or 'unknown'}" if available else detail,
    }


def _check_efinance_package(provider: EfinanceProvider) -> dict[str, Any]:
    available, detail = provider.available()
    return {
        "name": "efinance Python包",
        "ok": available,
        "detail": f"已安装 {detail or 'unknown'}" if available else detail,
    }


def _check_sina_provider(provider: SinaProvider) -> dict[str, Any]:
    available, detail = provider.available()
    return {
        "name": "Sina K线接口",
        "ok": available,
        "detail": detail,
    }


def _check_tushare_provider(provider: TushareProvider) -> dict[str, Any]:
    available, detail = provider.available()
    if available:
        return {"name": "Tushare 可选数据源", "ok": True, "detail": f"已配置 {detail or 'unknown'}"}
    return {"name": "Tushare 可选数据源", "ok": True, "detail": detail or "未配置，已跳过"}
def _run_check(name: str, fn: Callable[[], Any]) -> dict[str, Any]:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        data = future.result(timeout=min(DEFAULT_PROVIDER_TIMEOUT_SECONDS, 5))
        sample_size = len(data) if hasattr(data, "__len__") else None
        return {
            "name": name,
            "ok": True,
            "detail": "接口可返回数据",
            "sample_size": sample_size,
        }
    except TimeoutError:
        future.cancel()
        return {"name": name, "ok": False, "detail": "接口超时，可能是网络或上游数据源受限"}
    except Exception as exc:
        return {"name": name, "ok": False, "detail": str(exc)}
    finally:
        executor.shutdown(wait=False, cancel_futures=True)






