from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import requests

from app.config import DEFAULT_LLM_API_KEY, DEFAULT_LLM_ENDPOINT, DEFAULT_LLM_MODEL
from app.db import get_connection, init_db
from app.models.llm import AnalyzeRequest, AnalyzeResponse, LlmApiConfig
from app.services.analysis_service import AnalysisService
from app.services.valuation_service import build_valuation_snapshot


REPORT_LABELS = {
    "valuation": "估值合理性",
    "financial": "财务健康度",
    "position": "行业地位",
    "risk": "主要风险",
    "overview": "综合分析",
}


class LlmService:
    def analyze(self, payload: AnalyzeRequest) -> AnalyzeResponse:
        context = self._build_context(payload)
        report_type_label = REPORT_LABELS.get(payload.report_type, payload.report_type)
        warnings: list[str] = []

        api_config = payload.api_config
        if not _has_remote_config(api_config) and DEFAULT_LLM_API_KEY:
            api_config = LlmApiConfig(
                endpoint=DEFAULT_LLM_ENDPOINT,
                api_key=DEFAULT_LLM_API_KEY,
                model=DEFAULT_LLM_MODEL,
                temperature=payload.api_config.temperature,
            )
            warnings.append("used_machine_default_llm")

        if not _has_remote_config(api_config):
            warnings.append("used_local_draft_without_llm_config")
            markdown = self._local_draft(context, report_type_label)
            source = "local_draft"
        else:
            prompt = self._build_prompt(context, report_type_label)
            markdown = self._call_openai_compatible(api_config, prompt)
            source = "openai_compatible"

        self._save_report(
            analysis_id=payload.analysis_id,
            stock_code=payload.stock_code,
            report_type=payload.report_type,
            markdown=markdown,
        )

        return AnalyzeResponse(
            analysis_id=payload.analysis_id,
            stock_code=payload.stock_code,
            report_type=payload.report_type,
            markdown_report=markdown,
            source=source,
            warnings=warnings,
        )

    def _build_context(self, payload: AnalyzeRequest) -> dict[str, Any]:
        detail = AnalysisService().get(payload.analysis_id)
        if detail is None:
            raise ValueError("analysis not found")

        candidate = self._find_candidate(payload.analysis_id, payload.stock_code)
        active_node = None
        if candidate is not None:
            active_node = next(
                (node for node in detail.nodes if node.id == candidate["industry_node_id"]),
                None,
            )

        return {
            "analysis": detail.analysis.model_dump(mode="json"),
            "industry_nodes": [node.model_dump(mode="json") for node in detail.nodes],
            "active_node": active_node.model_dump(mode="json") if active_node else None,
            "candidate": candidate,
            "stock_summary": payload.stock_summary or {},
            "stock_kline": payload.stock_kline or {},
            "stock_financial": payload.stock_financial or {},
            "valuation": build_valuation_snapshot(payload.stock_summary, payload.stock_financial, payload.stock_kline),
        }

    def _find_candidate(self, analysis_id: str, stock_code: str) -> dict[str, Any] | None:
        init_db()
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM company_candidate
                WHERE analysis_id = ? AND stock_code = ?
                ORDER BY score DESC
                LIMIT 1
                """,
                (analysis_id, stock_code),
            ).fetchone()

        if row is None:
            return None

        return {
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "industry_node_id": row["industry_node_id"],
            "reason": row["reason"],
            "market_cap": row["market_cap"],
            "revenue": row["revenue"],
            "roe": row["roe"],
            "score": row["score"],
        }

    def _build_prompt(self, context: dict[str, Any], report_type_label: str) -> str:
        return f"""你是A股股票研究助手。
请基于以下结构化数据，生成“{report_type_label}”研究分析。

要求：
1. 明确区分事实、推断和风险；数据缺失时直接说明，不得编造。
2. 如果是估值分析，必须先引用 valuation.methods 里的固定估值结果，再给出进一步判断。
3. 结尾必须输出“### 条件化行动框架”：分别列出“继续观察”“研究条件满足后再考虑”“风险收缩/退出观察”的客观触发条件和失效条件。
4. 该框架只用于研究流程，不提供个人化投资建议，不给出具体买卖价格、仓位比例或保证收益表述。
5. 输出 Markdown。

结构化数据：
{json.dumps(context, ensure_ascii=False, indent=2)}
"""
    def _call_openai_compatible(self, config: LlmApiConfig, prompt: str) -> str:
        url = _chat_completions_url(config.endpoint or "")
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": config.model,
            "temperature": config.temperature,
            "messages": [
                {
                    "role": "system",
                    "content": "你是严谨的A股产业链研究助手，只做研究分析，不提供投资建议。",
                },
                {"role": "user", "content": prompt},
            ],
        }
        response = requests.post(url, headers=headers, json=body, timeout=60)
        if not response.ok:
            raise RuntimeError(f"LLM HTTP {response.status_code}: {response.text[:1200]}")
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"LLM response missing choices[0].message.content: {json.dumps(data, ensure_ascii=False)[:1200]}") from exc
    def _local_draft(self, context: dict[str, Any], report_type_label: str) -> str:
        analysis = context["analysis"]
        candidate = context.get("candidate") or {}
        active_node = context.get("active_node") or {}
        summary = context.get("stock_summary") or {}
        financial = context.get("stock_financial") or {}
        rows = financial.get("rows") or []
        latest_financial = rows[0] if rows else {}
        valuation = context.get("valuation") or {}
        quality = valuation.get("quality") or {}
        stock_name = candidate.get("stock_name") or summary.get("name") or "该公司"
        stock_code = candidate.get("stock_code") or summary.get("code") or "-"
        node_name = active_node.get("name") or "当前产业链环节"
        reason = candidate.get("reason") or "暂无候选理由。"
        valuation_block = valuation.get("markdown", "") if report_type_label in {"估值合理性", "综合分析"} else ""

        common = f"""### 研究对象
{stock_name}（{stock_code}）出现在“{analysis["keyword"]}”主题下的“{node_name}”环节。

### 相关依据
- 候选理由：{reason}
- 最新价：{_display(summary.get("latest_price"))}
- 涨跌幅：{_display(summary.get("change_pct"), suffix="%")}
- PE TTM：{_display(summary.get("pe_ttm"))}
- PB：{_display(summary.get("pb"))}
- PS：{_display(summary.get("ps"))}
- 总市值：{_display(summary.get("market_cap"))}
- ROE：{_display(latest_financial.get("roe"), suffix="%")}
- 毛利率：{_display(latest_financial.get("gross_margin"), suffix="%")}
- 资产负债率：{_display(latest_financial.get("debt_ratio"), suffix="%")}
"""

        if report_type_label == "财务健康度":
            body = f"""### 财务观察
- 财务质量信号：{quality.get("signal", "数据不足")}。
- 质量说明：{quality.get("text", "缺少关键财务指标，暂不能做强判断。")} 
- 最近报告期：{_display(latest_financial.get("report_date"))}
- 营收：{_display(latest_financial.get("revenue"))}
- 归母净利润：{_display(latest_financial.get("net_profit"))}

### 需要继续核验
需要补充至少三到五年营收、利润、现金流和费用率趋势，才能判断盈利质量是否稳定。
"""
        elif report_type_label == "行业地位":
            body = f"""### 行业地位观察
该公司当前被匹配到“{node_name}”环节。若候选理由来自内置模板，说明它在本地产业链知识库中属于该环节代表公司或相关公司；若来自在线概念板块，则说明它命中了对应概念数据。

### 需要继续核验
需要进一步比较该公司在细分环节中的收入占比、产能份额、客户结构、技术壁垒和同行排名。
"""
        elif report_type_label == "主要风险":
            body = """### 主要风险
- 数据风险：行情、财务和概念数据可能存在延迟、缺失或接口失败。
- 匹配风险：产业链归类来自规则、模板或模型推断，需要人工复核。
- 经营风险：需关注行业价格周期、需求波动、竞争加剧、费用率和现金流压力。
- 估值风险：估值倍数需要和同行、成长性、景气度共同判断，不能单看一个指标。
"""
        elif report_type_label == "估值合理性":
            body = valuation_block
        else:
            body = f"""### 综合结论草稿
从已有数据看，系统已完成产业链定位、候选公司匹配、行情读取、财务快照和固定估值检查。当前最有价值的信息是：公司为何与主题相关、估值方法哪些可算、哪些数据仍缺失。

{valuation_block}

### 后续研究重点
优先补充同行公司、三到五年财务趋势、业务结构、行业景气度和近期公告，再交给大模型做更完整的交叉判断。

### 条件化行动框架
- 继续观察：等待至少两个报告期的营收、利润与经营现金流趋势相互验证，并与同行估值进行对照。
- 研究条件满足后再考虑：只有当基本面改善信号、现金流质量与估值安全边际同时得到数据支持时，才进入下一步研究。
- 风险收缩/退出观察：若盈利预期下修、经营现金流持续恶化、负债压力上升或核心产业逻辑被证伪，应重新评估而非沿用原判断。
- 失效条件：数据来源过期、指标口径变化或产业链匹配无法复核时，当前结论自动降级为待验证。
"""

        return f"""## {report_type_label}

{common}
{body}
### 风险提示
本内容仅供研究参考，不构成投资建议。
"""

    def list_reports(self, analysis_id: str, stock_code: str | None = None) -> list[dict[str, str]]:
        init_db()
        query = "SELECT id, analysis_id, stock_code, report_type, markdown, created_at FROM llm_report WHERE analysis_id = ?"
        values: list[str] = [analysis_id]
        if stock_code:
            query += " AND stock_code = ?"
            values.append(stock_code)
        query += " ORDER BY created_at DESC LIMIT 30"
        with get_connection() as conn:
            rows = conn.execute(query, values).fetchall()
        return [
            {
                "id": row["id"],
                "analysis_id": row["analysis_id"],
                "stock_code": row["stock_code"],
                "report_type": row["report_type"],
                "markdown_report": row["markdown"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    def _save_report(self, analysis_id: str, stock_code: str, report_type: str, markdown: str) -> None:

        init_db()
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_report (id, analysis_id, stock_code, report_type, markdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    analysis_id,
                    stock_code,
                    report_type,
                    markdown,
                    datetime.now().astimezone().isoformat(),
                ),
            )
            conn.commit()


def _has_remote_config(config: LlmApiConfig) -> bool:
    return bool(config.endpoint and config.api_key and config.model)


def _chat_completions_url(endpoint: str) -> str:
    trimmed = endpoint.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    return f"{trimmed}/chat/completions"


def _display(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "缺失"
    return f"{value}{suffix}"









