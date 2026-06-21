from __future__ import annotations

from statistics import mean

from app.models.stock import CashflowAssessment, CashflowTrendPoint, CompanyResearchResponse, DebtAssessment
from app.services.stock_data_service import StockDataService


class CompanyResearchService:
    """Build transparent company-research indicators from available financial history."""

    def __init__(self, stock_data: StockDataService | None = None) -> None:
        self.stock_data = stock_data or StockDataService()

    def get_research(self, code: str, force_refresh: bool = False) -> CompanyResearchResponse:
        summary = self.stock_data.get_summary(code, force_refresh=force_refresh)
        financial = self.stock_data.get_financial(code, force_refresh=force_refresh)
        cashflow = _assess_cashflow(financial.rows)
        debt = _assess_debt(financial.rows)
        warnings = list(dict.fromkeys([*summary.warnings, *financial.warnings, *cashflow.warnings, *debt.warnings]))
        return CompanyResearchResponse(code=code, summary=summary, financial=financial, cashflow=cashflow, debt=debt, warnings=warnings)


def _assess_cashflow(rows) -> CashflowAssessment:
    ordered = sorted(rows, key=lambda row: row.report_date)
    historical = [
        CashflowTrendPoint(report_date=row.report_date, operating_cash_flow=row.operating_cash_flow, free_cash_flow=_free_cash_flow(row))
        for row in ordered
        if row.operating_cash_flow is not None or _free_cash_flow(row) is not None
    ]
    if not historical:
        return CashflowAssessment(signal="数据不足", text="当前数据源未提供可用的经营现金流或自由现金流，暂不生成预测。", projection_method="未预测", warnings=["cashflow_data_unavailable"])

    usable_fcf = [point.free_cash_flow for point in historical if point.free_cash_flow is not None]
    usable_ocf = [point.operating_cash_flow for point in historical if point.operating_cash_flow is not None]
    base = usable_fcf[-3:] if usable_fcf else usable_ocf[-3:]
    metric_name = "自由现金流" if usable_fcf else "经营现金流"
    average_value, last_value = mean(base), base[-1]
    growth = 0.0 if not last_value else max(-0.2, min(0.15, (last_value - average_value) / abs(average_value or 1)))
    assumption = f"基于最近 {len(base)} 期{metric_name}均值与最近一期的保守趋势外推；仅作情景估算，不代表公司指引。"
    first_year = _next_year(historical[-1].report_date)
    projected = [
        CashflowTrendPoint(
            report_date=str(first_year + offset), kind="projected", assumption=assumption,
            operating_cash_flow=last_value * ((1 + growth) ** (offset + 1)) if not usable_fcf else None,
            free_cash_flow=last_value * ((1 + growth) ** (offset + 1)) if usable_fcf else None,
        )
        for offset in range(3)
    ]
    positive_count = sum(value > 0 for value in base)
    if positive_count == len(base) and last_value >= average_value:
        signal, text = "较稳健", f"最近 {len(base)} 期{metric_name}均为正，且最近一期不低于近期均值。"
    elif positive_count == 0:
        signal, text = "承压", f"最近 {len(base)} 期{metric_name}均为负，需要核验盈利质量、营运资本与资本开支。"
    else:
        signal, text = "波动", f"最近 {len(base)} 期{metric_name}存在正负波动，不宜仅依据单期数据判断。"
    return CashflowAssessment(signal=signal, text=text, projection_method=f"基于最近 {len(base)} 期{metric_name}的保守趋势外推", points=[*historical, *projected])


def _assess_debt(rows) -> DebtAssessment:
    latest = next((row for row in rows if any([row.debt_ratio is not None, row.total_debt is not None, row.cash_balance is not None, row.current_ratio is not None, row.interest_coverage is not None])), None)
    if latest is None:
        return DebtAssessment(signal="数据不足", text="当前数据源未提供足够的负债明细，需结合最新资产负债表复核。", warnings=["debt_data_unavailable"])

    net_debt = latest.total_debt - latest.cash_balance if latest.total_debt is not None and latest.cash_balance is not None else None
    flags = []
    if latest.debt_ratio is not None and latest.debt_ratio >= 70: flags.append("资产负债率偏高")
    if latest.current_ratio is not None and latest.current_ratio < 1: flags.append("短期偿债覆盖偏弱")
    if latest.interest_coverage is not None and latest.interest_coverage < 2: flags.append("利息保障偏弱")
    if flags:
        signal, text = "需关注", "；".join(flags) + "，建议结合有息负债期限结构和经营现金流持续复核。"
    elif latest.debt_ratio is not None or latest.current_ratio is not None:
        signal, text = "可跟踪", "主要负债指标未触发本地预警阈值，但仍应结合行业和报表口径判断。"
    else:
        signal, text = "数据有限", "仅取得部分负债字段，暂不作强判断。"
    return DebtAssessment(signal=signal, text=text, debt_ratio=latest.debt_ratio, total_debt=latest.total_debt, cash_balance=latest.cash_balance, net_debt=net_debt, current_ratio=latest.current_ratio, interest_coverage=latest.interest_coverage, report_date=latest.report_date)


def _free_cash_flow(row):
    if row.free_cash_flow is not None:
        return row.free_cash_flow
    if row.operating_cash_flow is not None and row.capital_expenditure is not None:
        return row.operating_cash_flow - abs(row.capital_expenditure)
    return None


def _next_year(report_date: str) -> int:
    try:
        return int(report_date[:4]) + 1
    except (TypeError, ValueError):
        return 2027
