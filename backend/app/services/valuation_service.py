from __future__ import annotations

from typing import Any


def build_valuation_snapshot(
    stock_summary: dict[str, Any] | None,
    stock_financial: dict[str, Any] | None,
    stock_kline: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = stock_summary or {}
    financial = stock_financial or {}
    kline = stock_kline or {}
    rows = financial.get("rows") or []
    latest_financial = rows[0] if rows else {}
    raw_fields = summary.get("raw_fields") or {}
    local_snapshot = raw_fields.get("local_financial_snapshot") or {}
    growth = _net_profit_growth(rows)

    revenue = _number(latest_financial.get("revenue")) or _number(local_snapshot.get("revenue"))
    market_cap = _number(summary.get("market_cap"))
    ps = _number(summary.get("ps")) or _divide(market_cap, revenue)
    dividend_yield = _number(local_snapshot.get("dividend_yield"))
    roe = _number(latest_financial.get("roe")) or _number(local_snapshot.get("roe"))
    gross_margin = _number(latest_financial.get("gross_margin")) or _number(local_snapshot.get("gross_margin"))
    debt_ratio = _number(latest_financial.get("debt_ratio")) or _number(local_snapshot.get("debt_ratio"))

    methods = [
        _method("PE 市盈率", "股价 ÷ 每股收益（EPS）", summary.get("pe_ttm"), _pe_note(summary.get("pe_ttm"))),
        _method("PB 市净率", "股价 ÷ 每股净资产（BPS）", summary.get("pb"), _pb_note(summary.get("pb"), roe)),
        _method("PEG", "PE ÷ 净利润增长率（%）", _peg(summary.get("pe_ttm"), growth), "用最近两期净利润粗略估算增长率，周期口径需人工复核。"),
        _method("PS 市销率", "总市值 ÷ 主营业务收入", ps, "由数据源直接给出，或用总市值和最近营收粗算。"),
        _method("股息率", "每股股利 ÷ 股价 × 100%", dividend_yield, "若本地或上游数据提供分红率，则作为现金回报参考。"),
        _method("PCF 市现率", "股价 ÷ 每股经营现金流", None, "当前数据源未提供每股经营现金流。"),
        _method("EV/EBITDA", "企业价值 ÷ EBITDA", None, "当前数据源未提供净负债和 EBITDA。"),
        _method("DCF", "未来自由现金流折现", None, "需要未来自由现金流、折现率和终值假设。"),
        _method("DDM", "未来股利折现", None, "需要稳定股利预测和必要报酬率。"),
        _method("RIM/EBO", "账面净资产 + 未来超额收益现值", _rim_signal(summary.get("pb"), roe), "当前用 PB 与 ROE 做方向性提示，数值越高说明 ROE 对 PB 的覆盖越强。"),
        _method("SOTP 分部估值", "各业务板块分别估值后加总", None, "需要分业务收入、利润和可比倍数。"),
        _method("可比交易法", "参考同行交易倍数", None, "需要近期并购或股权交易样本。"),
    ]
    quality = _quality_summary(roe, gross_margin, debt_ratio, growth)
    return {
        "summary": {
            "available_count": sum(1 for item in methods if item["value"] is not None),
            "data_source": summary.get("source"),
            "financial_source": financial.get("source"),
            "kline_source": kline.get("source"),
            "net_profit_growth_pct": growth,
            "roe": roe,
            "gross_margin": gross_margin,
            "debt_ratio": debt_ratio,
            "quality_signal": quality["signal"],
        },
        "methods": methods,
        "quality": quality,
        "markdown": valuation_markdown(methods, growth, quality),
    }


def valuation_markdown(methods: list[dict[str, Any]], growth: float | None, quality: dict[str, Any] | None = None) -> str:
    lines = ["### 固定估值方法检查", "", "| 方法 | 公式 | 当前结果 | 说明 |", "| --- | --- | --- | --- |"]
    for item in methods:
        lines.append(
            f"| {item['name']} | {item['formula']} | {_display(item['value'], item.get('suffix', ''))} | {item['note']} |"
        )
    lines.extend([
        "",
        f"净利润增长率粗算：{_display(growth, '%')}。",
    ])
    if quality:
        lines.extend([
            "",
            f"财务质量提示：{quality.get('signal', '数据不足')}。{quality.get('text', '')}",
        ])
    lines.extend([
        "",
        "说明：固定估值只做机械计算和数据可得性检查；是否合理仍需结合行业周期、公司质量、成长性和风险，由人工或大模型进一步判断。",
    ])
    return "\n".join(lines)


def _method(name: str, formula: str, value: Any, note: str) -> dict[str, Any]:
    suffix = "%" if name == "股息率" else ""
    return {"name": name, "formula": formula, "value": _number(value), "suffix": suffix, "note": note}


def _peg(pe: Any, growth: float | None) -> float | None:
    pe_value = _number(pe)
    if pe_value is None or growth in (None, 0):
        return None
    return pe_value / growth


def _rim_signal(pb: Any, roe: Any) -> float | None:
    pb_value = _number(pb)
    roe_value = _number(roe)
    if pb_value is None or roe_value is None:
        return None
    return roe_value / pb_value if pb_value else None


def _net_profit_growth(rows: list[dict[str, Any]]) -> float | None:
    profits = [_number(row.get("net_profit")) for row in rows[:2]]
    if len(profits) < 2 or profits[0] is None or profits[1] in (None, 0):
        return None
    return (profits[0] - profits[1]) / abs(profits[1]) * 100


def _quality_summary(roe: float | None, gross_margin: float | None, debt_ratio: float | None, growth: float | None) -> dict[str, Any]:
    score = 0
    notes: list[str] = []
    if roe is not None:
        if roe >= 15:
            score += 2
            notes.append("ROE 较强")
        elif roe >= 8:
            score += 1
            notes.append("ROE 中等")
        else:
            notes.append("ROE 偏弱")
    if gross_margin is not None:
        if gross_margin >= 35:
            score += 1
            notes.append("毛利率较高")
        elif gross_margin < 15:
            score -= 1
            notes.append("毛利率偏低")
    if debt_ratio is not None:
        if debt_ratio <= 45:
            score += 1
            notes.append("资产负债率较稳")
        elif debt_ratio >= 70:
            score -= 1
            notes.append("资产负债率偏高")
    if growth is not None:
        if growth > 10:
            score += 1
            notes.append("净利润增长为正")
        elif growth < -10:
            score -= 1
            notes.append("净利润下滑明显")
    signal = "偏强" if score >= 3 else "中性" if score >= 1 else "偏弱" if notes else "数据不足"
    return {"signal": signal, "score": score, "text": "；".join(notes) or "缺少 ROE、毛利率、负债率或利润增长数据。"}


def _pe_note(pe: Any) -> str:
    value = _number(pe)
    if value is None:
        return "当前数据源未提供 PE TTM。"
    if value < 0:
        return "PE 为负，通常意味着盈利为负或口径异常，需要重点复核。"
    if value <= 15:
        return "PE 处于较低区间，需结合行业周期判断是否为低估或盈利下行。"
    if value <= 35:
        return "PE 处于中等区间，需重点比较成长性和同行估值。"
    return "PE 偏高，通常需要较强成长性或行业景气度支撑。"


def _pb_note(pb: Any, roe: Any) -> str:
    pb_value = _number(pb)
    roe_value = _number(roe)
    if pb_value is None:
        return "当前数据源未提供 PB。"
    if roe_value is None:
        return "PB 已取得，但缺少 ROE，暂不能判断净资产收益质量。"
    return "PB 需要和 ROE 一起看；高 ROE 可以部分解释更高 PB，低 ROE 则需警惕估值压力。"


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _number(value: Any) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _display(value: Any, suffix: str = "") -> str:
    number = _number(value)
    if number is None:
        return "数据不足"
    return f"{number:.2f}{suffix}"
