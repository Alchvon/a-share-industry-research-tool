from __future__ import annotations

import uuid

from app.config import DEFAULT_PROVIDER_TIMEOUT_SECONDS
from app.db import get_connection, init_db
from app.models.analysis import IndustryNode
from app.models.company import (
    CompanyCandidate,
    CreateCompanyCandidateRequest,
    UpdateCompanyCandidateRequest,
)
from app.services.akshare_provider import AkshareProvider, ProviderError
from app.services.analysis_service import AnalysisService
from app.services.local_knowledge import seed_candidates_for_node


SEED_CANDIDATES = {
    "AI芯片": [
        ("688256", "寒武纪", "国产 AI 芯片和智能计算芯片代表公司。", 95),
        ("688041", "海光信息", "国产高端处理器和加速计算相关标的。", 88),
        ("300474", "景嘉微", "图形处理芯片和国产 GPU 相关公司。", 76),
    ],
    "算力基础设施": [
        ("000977", "浪潮信息", "服务器和 AI 算力基础设施核心厂商。", 92),
        ("603019", "中科曙光", "高性能计算、服务器和数据中心相关公司。", 86),
        ("300308", "中际旭创", "高速光模块环节代表公司。", 83),
    ],
    "大模型与算法": [
        ("688111", "金山办公", "办公软件 AI 化和大模型应用代表公司。", 76),
        ("300033", "同花顺", "金融信息服务和 AI 投研应用相关公司。", 72),
        ("002230", "科大讯飞", "智能语音、认知智能和行业 AI 方案公司。", 82),
    ],
    "数据服务": [
        ("300229", "拓尔思", "语义智能、数据治理和内容智能相关公司。", 78),
        ("300058", "蓝色光标", "营销数据和 AIGC 应用相关公司。", 68),
        ("603000", "人民网", "数据确权和内容数据资源相关公司。", 66),
    ],
    "AI应用": [
        ("002230", "科大讯飞", "教育、办公、医疗等 AI 应用落地较多。", 84),
        ("688088", "虹软科技", "计算机视觉算法和智能终端视觉应用。", 72),
        ("300624", "万兴科技", "创意软件和 AIGC 应用相关公司。", 70),
    ],
    "电力与液冷": [
        ("002837", "英维克", "数据中心温控和液冷相关公司。", 86),
        ("300499", "高澜股份", "电力电子与液冷散热相关公司。", 72),
        ("301018", "申菱环境", "数据中心和工业温控设备公司。", 70),
    ],
    "运动服饰与鞋履": [
        ("300005", "探路者", "户外用品和运动服饰相关公司。", 82),
        ("002832", "比音勒芬", "高端运动休闲服饰相关公司。", 78),
        ("603908", "牧高笛", "露营帐篷和户外装备相关公司。", 76),
        ("605080", "浙江自然", "户外运动用品和充气床垫等装备制造商。", 70),
    ],
    "户外露营与专业装备": [
        ("603908", "牧高笛", "露营帐篷和户外装备代表公司。", 84),
        ("300005", "探路者", "户外用品和运动服饰相关公司。", 80),
        ("605080", "浙江自然", "户外运动用品制造商。", 74),
    ],
    "健身器材与训练设备": [
        ("002899", "英派斯", "健身器材和商用训练设备相关公司。", 84),
        ("002105", "信隆健康", "运动休闲和康复器材相关公司。", 70),
        ("300651", "金陵体育", "体育器材和场馆设施相关公司。", 76),
    ],
    "赛事场馆与运营服务": [
        ("600158", "中体产业", "体育赛事、场馆运营和体育彩票相关公司。", 86),
        ("000558", "莱茵体育", "体育空间运营和体育服务相关公司。", 74),
        ("002858", "力盛体育", "体育赛事运营和赛车运动相关公司。", 72),
        ("300651", "金陵体育", "体育器材和体育场馆设施相关公司。", 70),
    ],
    "运动材料与制造配套": [
        ("002395", "双象股份", "合成革、足球革和运动材料相关公司。", 82),
        ("603055", "台华新材", "功能性面料和户外运动材料相关公司。", 74),
        ("300577", "开润股份", "箱包和出行消费品制造供应链相关公司。", 66),
    ],
    "足球装备与运动鞋服": [
        ("002395", "双象股份", "足球革和运动合成材料相关公司。", 82),
        ("300005", "探路者", "户外运动服饰和装备相关公司。", 72),
        ("002832", "比音勒芬", "运动休闲服饰相关公司。", 70),
    ],
    "青训与全民健身": [
        ("600158", "中体产业", "体育服务和全民健身相关公司。", 80),
        ("000558", "莱茵体育", "体育空间运营相关公司。", 72),
        ("300651", "金陵体育", "体育器材和校园体育设施相关公司。", 70),
    ],
    "体育彩票与内容服务": [
        ("600158", "中体产业", "体育彩票和体育服务相关公司。", 80),
        ("002605", "姚记科技", "休闲娱乐、数字内容和体育消费相关标的。", 62),
        ("002229", "鸿博股份", "彩票印刷及相关业务历史布局。", 60),
    ],    "固态电解质": [
        ("300073", "当升科技", "锂电材料及固态电池材料布局相关公司。", 76),
        ("688707", "振华新材", "正极材料和新型电池材料相关公司。", 68),
    ],
    "电池制造": [
        ("300750", "宁德时代", "动力电池龙头，持续布局固态/半固态电池技术。", 96),
        ("002594", "比亚迪", "整车与动力电池一体化龙头。", 90),
        ("002074", "国轩高科", "动力电池厂商，布局固态电池方向。", 78),
    ],
    "飞行器制造": [
        ("688297", "中无人机", "大型无人机系统研制相关公司。", 82),
        ("002085", "万丰奥威", "通航飞机和低空经济相关公司。", 76),
        ("600038", "中直股份", "直升机航空装备核心公司。", 80),
    ],
    "空管与通信导航": [
        ("002151", "北斗星通", "北斗导航芯片、板卡和位置服务公司。", 80),
        ("300101", "振芯科技", "北斗导航和卫星应用相关公司。", 72),
        ("002465", "海格通信", "通信导航和专用通信相关公司。", 74),
    ],
}


class CompanyMatchService:
    def __init__(self, provider: AkshareProvider | None = None) -> None:
        self.provider = provider or AkshareProvider(timeout_seconds=DEFAULT_PROVIDER_TIMEOUT_SECONDS)

    def match(
        self,
        analysis_id: str,
        industry_node_ids: list[str] | None,
        limit_per_node: int,
    ) -> tuple[list[CompanyCandidate], list[str], str]:
        init_db()
        detail = AnalysisService().get(analysis_id)
        if detail is None:
            return [], ["analysis_not_found"], "none"

        selected_ids = set(industry_node_ids or [])
        nodes = [node for node in detail.nodes if not selected_ids or node.id in selected_ids]

        warnings: list[str] = []
        candidates: list[CompanyCandidate] = []
        used_dynamic = False
        fallback_count = 0
        provider_disabled = False
        for node in nodes:
            if provider_disabled:
                node_candidates, provider_warning = [], None
            else:
                node_candidates, provider_warning = self._match_node_with_provider(
                    analysis_id,
                    node,
                    limit_per_node,
                )
            if provider_warning:
                warnings.append(provider_warning)
                provider_disabled = True
            if node_candidates:
                used_dynamic = True
                candidates.extend(node_candidates)
            else:
                fallback_count += 1
                candidates.extend(self._match_node_with_seed(analysis_id, node, limit_per_node))
        if used_dynamic:
            source = "akshare_concept"
            if fallback_count:
                warnings.append(f"{fallback_count}_nodes_used_seed_or_empty_fallback")
        else:
            source = "seed_template"
            warnings.append("used_seed_candidate_template")

        self.replace_candidates(analysis_id, candidates, industry_node_ids)
        AnalysisService().update_status(analysis_id, "matched")
        return candidates, _compact_warnings(warnings), source

    def replace_candidates(
        self,
        analysis_id: str,
        candidates: list[CompanyCandidate],
        industry_node_ids: list[str] | None,
    ) -> None:
        with get_connection() as conn:
            if industry_node_ids:
                conn.executemany(
                    """
                    DELETE FROM company_candidate
                    WHERE analysis_id = ? AND industry_node_id = ?
                    """,
                    [(analysis_id, node_id) for node_id in industry_node_ids],
                )
            else:
                conn.execute("DELETE FROM company_candidate WHERE analysis_id = ?", (analysis_id,))

            conn.executemany(
                """
                INSERT INTO company_candidate (
                  id, analysis_id, industry_node_id, stock_code, stock_name,
                  reason, market_cap, revenue, roe, score, is_user_selected
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.id,
                        item.analysis_id,
                        item.industry_node_id,
                        item.stock_code,
                        item.stock_name,
                        item.reason,
                        item.market_cap,
                        item.revenue,
                        item.roe,
                        item.score,
                        int(item.is_user_selected),
                    )
                    for item in candidates
                ],
            )
            conn.commit()

    def list_candidates(self, analysis_id: str) -> list[CompanyCandidate]:
        init_db()
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM company_candidate
                WHERE analysis_id = ?
                ORDER BY industry_node_id ASC, score DESC, stock_code ASC
                """,
                (analysis_id,),
            ).fetchall()

        return [_candidate_from_row(row) for row in rows]

    def create_candidate(self, payload: CreateCompanyCandidateRequest) -> CompanyCandidate:
        init_db()
        candidate = CompanyCandidate(
            id=str(uuid.uuid4()),
            analysis_id=payload.analysis_id,
            industry_node_id=payload.industry_node_id,
            stock_code=payload.stock_code,
            stock_name=payload.stock_name.strip(),
            reason=payload.reason,
            market_cap=payload.market_cap,
            revenue=payload.revenue,
            roe=payload.roe,
            score=payload.score,
            is_user_selected=True,
            match_source="manual",
            score_details={"人工调整": payload.score or 50},
        )
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO company_candidate (
                  id, analysis_id, industry_node_id, stock_code, stock_name,
                  reason, market_cap, revenue, roe, score, is_user_selected
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.id,
                    candidate.analysis_id,
                    candidate.industry_node_id,
                    candidate.stock_code,
                    candidate.stock_name,
                    candidate.reason,
                    candidate.market_cap,
                    candidate.revenue,
                    candidate.roe,
                    candidate.score,
                    int(candidate.is_user_selected),
                ),
            )
            conn.commit()
        return candidate

    def update_candidate(self, candidate_id: str, payload: UpdateCompanyCandidateRequest) -> CompanyCandidate | None:
        init_db()
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM company_candidate WHERE id = ?", (candidate_id,)).fetchone()
            if row is None:
                return None

            values = {
                "industry_node_id": payload.industry_node_id if payload.industry_node_id is not None else row["industry_node_id"],
                "stock_code": payload.stock_code if payload.stock_code is not None else row["stock_code"],
                "stock_name": payload.stock_name.strip() if payload.stock_name is not None else row["stock_name"],
                "reason": payload.reason if payload.reason is not None else row["reason"],
                "market_cap": payload.market_cap if payload.market_cap is not None else row["market_cap"],
                "revenue": payload.revenue if payload.revenue is not None else row["revenue"],
                "roe": payload.roe if payload.roe is not None else row["roe"],
                "score": payload.score if payload.score is not None else row["score"],
                "is_user_selected": int(payload.is_user_selected) if payload.is_user_selected is not None else row["is_user_selected"],
            }
            conn.execute(
                """
                UPDATE company_candidate
                SET industry_node_id = ?, stock_code = ?, stock_name = ?, reason = ?,
                    market_cap = ?, revenue = ?, roe = ?, score = ?, is_user_selected = ?
                WHERE id = ?
                """,
                (
                    values["industry_node_id"],
                    values["stock_code"],
                    values["stock_name"],
                    values["reason"],
                    values["market_cap"],
                    values["revenue"],
                    values["roe"],
                    values["score"],
                    values["is_user_selected"],
                    candidate_id,
                ),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM company_candidate WHERE id = ?", (candidate_id,)).fetchone()
        return _candidate_from_row(updated)

    def delete_candidate(self, candidate_id: str) -> bool:
        init_db()
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM company_candidate WHERE id = ?", (candidate_id,)).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM company_candidate WHERE id = ?", (candidate_id,))
            conn.commit()
        return True

    def _match_node_with_provider(
        self,
        analysis_id: str,
        node: IndustryNode,
        limit: int,
    ) -> tuple[list[CompanyCandidate], str | None]:
        try:
            ranked = self.provider.get_ranked_concept_candidates(node.match_keywords, limit)
        except ProviderError as exc:
            return [], f"akshare_match_failed:{node.name}:{_short_text(str(exc))}"

        candidates: list[CompanyCandidate] = []
        for index, item in enumerate(ranked, start=1):
            score = max(50, 100 - (index - 1) * 8)
            board_name = item.get("board_name") or "概念板块"
            reason = f"命中 AKShare 概念板块“{board_name}”，按市值/流通市值排序。"
            candidates.append(
                CompanyCandidate(
                    id=str(uuid.uuid4()),
                    analysis_id=analysis_id,
                    industry_node_id=node.id,
                    stock_code=item["code"],
                    stock_name=item["name"],
                    reason=reason,
                    market_cap=item.get("market_cap"),
                    score=float(score),
                    match_source="akshare_concept",
                    score_details={"概念命中": 40, "市值排序": max(10, 40 - (index - 1) * 8), "数据源": 20},
                )
            )
        return candidates, None

    def _match_node_with_seed(self, analysis_id: str, node: IndustryNode, limit: int) -> list[CompanyCandidate]:
        seeds = seed_candidates_for_node(node)
        if not seeds:
            seeds = _fallback_candidates(node)

        return [
            CompanyCandidate(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                industry_node_id=node.id,
                stock_code=code,
                stock_name=name,
                reason=_seed_reason(node, name, reason),
                score=float(score),
                match_source="seed_template",
                score_details={"内置模板": float(score)},
            )
            for code, name, reason, score in seeds[:limit]
        ]



def _seed_candidates_for_node(node: IndustryNode) -> list[tuple[str, str, str, int]]:
    exact = SEED_CANDIDATES.get(node.name)
    if exact:
        return exact

    node_terms = [node.name, *node.match_keywords]
    scored: list[tuple[int, str]] = []
    for seed_name in SEED_CANDIDATES:
        score = _keyword_score(seed_name, node_terms)
        if score > 0:
            scored.append((score, seed_name))
    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[1]))
    merged: list[tuple[str, str, str, int]] = []
    seen_codes: set[str] = set()
    for _, seed_name in scored[:3]:
        for code, name, reason, score in SEED_CANDIDATES[seed_name]:
            if code in seen_codes:
                continue
            seen_codes.add(code)
            merged.append((code, name, reason, score))
    return merged


def _keyword_score(text: str, terms: list[str]) -> int:
    normalized_text = text.lower()
    score = 0
    for term in terms:
        normalized_term = str(term).strip().lower()
        if not normalized_term:
            continue
        if normalized_term in normalized_text or normalized_text in normalized_term:
            score += 100
        for token in _split_tokens(normalized_term):
            if token and token in normalized_text:
                score += 10
    return score


def _split_tokens(value: str) -> list[str]:
    tokens = [value]
    for separator in [" ", "/", "、", ",", "，", "-", "_", "与", "和"]:
        next_tokens: list[str] = []
        for token in tokens:
            next_tokens.extend(token.split(separator))
        tokens = next_tokens
    return [token.strip() for token in tokens if len(token.strip()) >= 2]

def _seed_reason(node: IndustryNode, stock_name: str, base_reason: str) -> str:
    keywords = "、".join(node.match_keywords[:4])
    return f"相关点：{stock_name}匹配到“{node.name}”方向；关键词：{keywords}。{base_reason}"


def _fallback_candidates(node: IndustryNode) -> list[tuple[str, str, str, int]]:
    keyword_text = "、".join(node.match_keywords[:3])
    return [
        (
            "000000",
            "待匹配",
            f"暂未命中内置候选模板，需要后续通过概念板块检索：{keyword_text}",
            0,
        )
    ]


def _compact_warnings(warnings: list[str], limit: int = 4) -> list[str]:
    compacted = [_short_text(warning) for warning in warnings if warning]
    if len(compacted) <= limit:
        return compacted
    remaining = len(compacted) - limit
    return [*compacted[:limit], f"{remaining}_additional_warnings"]


def _short_text(text: str, limit: int = 180) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 3]}..."


def _candidate_from_row(row) -> CompanyCandidate:
    return CompanyCandidate(
        id=row["id"],
        analysis_id=row["analysis_id"],
        industry_node_id=row["industry_node_id"],
        stock_code=row["stock_code"],
        stock_name=row["stock_name"],
        reason=row["reason"],
        market_cap=row["market_cap"],
        revenue=row["revenue"],
        roe=row["roe"],
        score=row["score"],
        is_user_selected=bool(row["is_user_selected"]),
        match_source=_derive_match_source(row["reason"]),
        score_details=_derive_score_details(row["reason"], row["score"]),
    )



def _derive_match_source(reason: str | None) -> str:
    reason_text = reason or ""
    if "AKShare" in reason_text:
        return "akshare_concept"
    if "用户" in reason_text or "手动" in reason_text:
        return "manual"
    if "暂未命中" in reason_text:
        return "fallback"
    return "seed_template"


def _derive_score_details(reason: str | None, score: float | None) -> dict[str, float | str]:
    source = _derive_match_source(reason)
    value = float(score or 0)
    if source == "akshare_concept":
        return {"概念命中": 40, "市值排序": max(0, value - 40), "数据源": 20}
    if source == "manual":
        return {"人工调整": value}
    if source == "fallback":
        return {"待匹配": 0}
    return {"内置模板": value}









