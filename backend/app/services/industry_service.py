from __future__ import annotations

import json
import uuid
from typing import Any

import requests

from app.db import get_connection, init_db
from app.models.analysis import IndustryNode, UpdateIndustryNodeRequest, UpsertIndustryNodeRequest
from app.models.llm import LlmApiConfig
from app.services.analysis_service import AnalysisService, now_local
from app.services.llm_service import _chat_completions_url
from app.services.local_knowledge import select_industry_template


GENERIC_NODES = [
    {
        "name": "上游材料与设备",
        "description": "为该主题提供关键原材料、核心设备和基础工艺的环节。",
        "keywords": ["材料", "设备", "零部件", "上游"],
    },
    {
        "name": "核心制造与平台",
        "description": "直接承载产品制造、平台建设或核心能力供给的环节。",
        "keywords": ["制造", "平台", "核心", "龙头"],
    },
    {
        "name": "系统集成与解决方案",
        "description": "将核心产品组合为行业可用方案，并面向客户交付的环节。",
        "keywords": ["系统集成", "解决方案", "服务商", "项目"],
    },
    {
        "name": "下游应用场景",
        "description": "该主题在具体行业中的落地应用和商业化场景。",
        "keywords": ["应用", "场景", "下游", "客户"],
    },
    {
        "name": "基础设施与配套服务",
        "description": "支撑产业规模化发展的基础设施、运营服务和配套能力。",
        "keywords": ["基础设施", "运营", "配套", "服务"],
    },
]


KEYWORD_TEMPLATES = {
    "人工智能": [
        ("芯片与底层算力", "对应 AI 五层蛋糕中的底层算力，覆盖 GPU、AI 芯片、服务器和高速互联。", ["AI芯片", "GPU", "算力芯片", "服务器", "光模块"]),
        ("算力基础设施", "承载模型训练和推理的数据中心、云平台、液冷、电力和运维能力。", ["算力", "数据中心", "云计算", "液冷", "电源"]),
        ("基础模型与算法", "研发通用大模型、多模态模型、算法框架和模型训练能力。", ["大模型", "多模态", "算法", "机器学习", "自然语言处理"]),
        ("数据与开发工具", "提供训练数据、数据治理、模型开发平台、MLOps 和安全评测。", ["数据要素", "数据服务", "数据标注", "MLOps", "模型安全"]),
        ("应用软件与智能终端", "把 AI 能力落到办公、教育、医疗、金融、工业和智能硬件场景。", ["AI应用", "智能终端", "行业应用", "办公软件", "工业软件"]),
    ],
    "体育用品": [
        ("运动服饰与鞋履", "覆盖运动服装、鞋履、户外服饰和专业运动品牌。", ["运动服饰", "运动鞋", "户外用品", "体育用品", "服装"]),
        ("户外露营与专业装备", "覆盖露营、登山、滑雪、骑行等户外装备和材料。", ["户外用品", "露营", "登山", "滑雪", "帐篷"]),
        ("健身器材与训练设备", "覆盖家用健身、商用健身房、康复训练和运动器械。", ["健身器材", "体育器材", "康复器械", "训练设备"]),
        ("赛事场馆与运营服务", "覆盖赛事运营、体育场馆、全民健身空间和体育服务。", ["体育赛事", "体育场馆", "赛事运营", "全民健身"]),
        ("运动材料与制造配套", "覆盖球类材料、合成革、功能面料、鞋服代工和供应链配套。", ["合成革", "功能面料", "运动材料", "鞋服制造"]),
    ],
    "足球": [
        ("赛事场馆与运营服务", "覆盖足球赛事运营、体育场馆、体育经纪和线下服务。", ["足球", "体育赛事", "体育场馆", "赛事运营"]),
        ("足球装备与运动鞋服", "覆盖足球鞋服、球类用品、训练装备和运动品牌。", ["足球装备", "运动服饰", "运动鞋", "体育用品"]),
        ("运动材料与制造配套", "覆盖足球革、合成革、功能面料和相关制造配套。", ["足球革", "合成革", "运动材料", "功能面料"]),
        ("青训与全民健身", "覆盖校园体育、青训、体育培训和社区运动空间。", ["足球青训", "体育培训", "全民健身", "校园体育"]),
        ("体育彩票与内容服务", "覆盖体育彩票、体育传媒、赛事内容和数字化服务。", ["体育彩票", "体育传媒", "赛事内容", "数字体育"]),
    ],
    "体育": [
        ("赛事场馆与运营服务", "覆盖体育赛事、场馆运营、体育经纪和群众体育服务。", ["体育赛事", "体育场馆", "赛事运营", "体育服务"]),
        ("运动服饰与鞋履", "覆盖运动服装、鞋履、户外服饰和专业运动品牌。", ["运动服饰", "运动鞋", "户外用品", "体育用品"]),
        ("健身器材与训练设备", "覆盖家用健身、商用健身房、康复训练和运动器械。", ["健身器材", "体育器材", "训练设备", "康复器械"]),
        ("户外露营与专业装备", "覆盖露营、登山、滑雪、骑行等户外装备。", ["户外用品", "露营", "登山", "滑雪"]),
        ("体育彩票与内容服务", "覆盖体育彩票、赛事内容、体育传媒和数字体育服务。", ["体育彩票", "体育传媒", "赛事内容", "数字体育"]),
    ],    "固态电池": [
        ("固态电解质", "提供氧化物、硫化物、聚合物等固态电解质材料。", ["固态电解质", "硫化物", "氧化物", "电池材料"]),
        ("正负极材料", "提供高镍正极、硅碳负极、锂金属等关键材料。", ["正极材料", "负极材料", "硅碳负极", "锂金属"]),
        ("电池制造", "负责固态电池电芯研发、制造和量产工艺。", ["固态电池", "动力电池", "电芯", "电池制造"]),
        ("设备与工艺", "提供干法电极、叠片、封装和检测设备。", ["锂电设备", "干法电极", "叠片", "检测设备"]),
        ("整车与储能应用", "固态电池在新能源汽车、低空飞行器和储能中的应用。", ["新能源汽车", "储能", "低空经济", "动力电池"]),
    ],
    "低空经济": [
        ("飞行器制造", "提供无人机、eVTOL、通航飞机等低空飞行器。", ["无人机", "eVTOL", "通航飞机", "航空装备"]),
        ("核心零部件", "提供电机、电池、飞控、传感器和复合材料。", ["飞控", "电机", "传感器", "复合材料"]),
        ("空管与通信导航", "支撑低空飞行监管、通信、导航和监视。", ["低空空管", "北斗导航", "通信", "雷达"]),
        ("运营服务", "提供物流、巡检、文旅、应急等低空运营服务。", ["低空运营", "无人机物流", "巡检", "应急"]),
        ("基础设施", "建设起降场、充换电、地面保障和数字平台。", ["起降场", "充电", "基础设施", "数字平台"]),
    ],
}


class IndustryService:
    def decompose(
        self,
        keyword: str,
        analysis_id: str | None = None,
        api_config: LlmApiConfig | None = None,
    ) -> tuple[list[IndustryNode], list[str], str]:
        init_db()
        normalized_keyword = keyword.strip()
        warnings: list[str] = []

        if analysis_id is None:
            analysis = AnalysisService().create(normalized_keyword)
            analysis_id = analysis.id

        source = "rule_based"
        node_specs = None
        if api_config and _has_remote_config(api_config):
            try:
                node_specs = self._decompose_with_llm(normalized_keyword, api_config)
                source = "openai_compatible"
            except Exception as exc:
                warnings.append(f"llm_decompose_failed: {exc}")

        if node_specs is None:
            node_specs = self._select_template(normalized_keyword)
        if node_specs is None:
            warnings.append("used_rule_based_generic_template")
            node_specs = [
                (
                    spec["name"],
                    spec["description"],
                    [normalized_keyword, *spec["keywords"]],
                )
                for spec in GENERIC_NODES
            ]
        elif source == "rule_based":
            warnings.append("used_rule_based_keyword_template")

        nodes = [
            IndustryNode(
                id=str(uuid.uuid4()),
                analysis_id=analysis_id,
                parent_id=None,
                name=name,
                level=1,
                description=description,
                match_keywords=list(dict.fromkeys([normalized_keyword, *keywords])),
                sort_order=index,
            )
            for index, (name, description, keywords) in enumerate(node_specs, start=1)
        ]

        self.replace_nodes(analysis_id, nodes)
        AnalysisService().update_status(analysis_id, "decomposed")
        return nodes, warnings, source

    def replace_nodes(self, analysis_id: str, nodes: list[IndustryNode]) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM industry_node WHERE analysis_id = ?", (analysis_id,))
            conn.executemany(
                """
                INSERT INTO industry_node (
                  id, analysis_id, parent_id, name, level, description,
                  match_keywords, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        node.id,
                        node.analysis_id,
                        node.parent_id,
                        node.name,
                        node.level,
                        node.description,
                        json.dumps(node.match_keywords, ensure_ascii=False),
                        node.sort_order,
                    )
                    for node in nodes
                ],
            )
            conn.commit()

    def create_node(self, payload: UpsertIndustryNodeRequest) -> IndustryNode:
        init_db()
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM industry_node WHERE analysis_id = ?",
                (payload.analysis_id,),
            ).fetchone()
            sort_order = int(row["max_order"] or 0) + 1
            node = IndustryNode(
                id=str(uuid.uuid4()),
                analysis_id=payload.analysis_id,
                parent_id=payload.parent_id,
                name=payload.name.strip(),
                level=payload.level,
                description=payload.description.strip(),
                match_keywords=_normalize_keywords(payload.match_keywords, payload.name),
                sort_order=sort_order,
            )
            conn.execute(
                """
                INSERT INTO industry_node (
                  id, analysis_id, parent_id, name, level, description,
                  match_keywords, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.analysis_id,
                    node.parent_id,
                    node.name,
                    node.level,
                    node.description,
                    json.dumps(node.match_keywords, ensure_ascii=False),
                    node.sort_order,
                ),
            )
            conn.commit()
        return node

    def update_node(self, node_id: str, payload: UpdateIndustryNodeRequest) -> IndustryNode | None:
        init_db()
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM industry_node WHERE id = ?", (node_id,)).fetchone()
            if row is None:
                return None

            name = payload.name.strip() if payload.name is not None else row["name"]
            description = payload.description.strip() if payload.description is not None else row["description"]
            keywords = (
                _normalize_keywords(payload.match_keywords, name)
                if payload.match_keywords is not None
                else json.loads(row["match_keywords"])
            )
            level = payload.level if payload.level is not None else row["level"]
            parent_id = payload.parent_id if payload.parent_id is not None else row["parent_id"]

            conn.execute(
                """
                UPDATE industry_node
                SET name = ?, description = ?, match_keywords = ?, level = ?, parent_id = ?
                WHERE id = ?
                """,
                (
                    name,
                    description,
                    json.dumps(keywords, ensure_ascii=False),
                    level,
                    parent_id,
                    node_id,
                ),
            )
            conn.commit()

            updated = conn.execute("SELECT * FROM industry_node WHERE id = ?", (node_id,)).fetchone()
        return _node_from_row(updated)

    def delete_node(self, node_id: str) -> bool:
        init_db()
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM industry_node WHERE id = ?", (node_id,)).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM company_candidate WHERE industry_node_id = ?", (node_id,))
            conn.execute("DELETE FROM industry_node WHERE id = ?", (node_id,))
            conn.commit()
        return True

    def _select_template(self, keyword: str):
        return select_industry_template(keyword)
    def _decompose_with_llm(
        self,
        keyword: str,
        api_config: LlmApiConfig,
    ) -> list[tuple[str, str, list[str]]]:
        prompt = f"""你是A股产业链研究助手。
请将用户输入的行业主题拆解为适合A股公司研究的产业链子领域。

要求：
1. 输出 5-8 个子领域。
2. 每个子领域给出简短说明。
3. 每个子领域给出 3-5 个用于匹配A股概念板块或行业板块的关键词。
4. 不要直接推荐股票。
5. 只输出 JSON，不要输出 Markdown 或解释文字。

JSON 格式：
{{
  "nodes": [
    {{
      "name": "子领域名称",
      "description": "一句话说明",
      "match_keywords": ["关键词1", "关键词2", "关键词3"]
    }}
  ]
}}

用户输入：{keyword}
"""
        response = requests.post(
            _chat_completions_url(api_config.endpoint or ""),
            headers={
                "Authorization": f"Bearer {api_config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": api_config.model,
                "temperature": api_config.temperature,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是严谨的A股产业链研究助手，只输出可解析 JSON。",
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_llm_nodes(content)


def _has_remote_config(config: LlmApiConfig) -> bool:
    return bool(config.endpoint and config.api_key and config.model)


def _parse_llm_nodes(content: str) -> list[tuple[str, str, list[str]]]:
    data = _loads_json_content(content)
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list):
        raise ValueError("LLM JSON missing nodes array")

    nodes: list[tuple[str, str, list[str]]] = []
    for raw_node in raw_nodes[:8]:
        if not isinstance(raw_node, dict):
            continue
        name = _clean_text(raw_node.get("name"))
        description = _clean_text(raw_node.get("description"))
        keywords = raw_node.get("match_keywords") or raw_node.get("keywords")
        if not name or not description or not isinstance(keywords, list):
            continue
        cleaned_keywords = [
            item
            for item in (_clean_text(keyword) for keyword in keywords)
            if item
        ][:5]
        if len(cleaned_keywords) < 1:
            cleaned_keywords = [name]
        nodes.append((name, description, cleaned_keywords))

    if len(nodes) < 3:
        raise ValueError("LLM returned too few valid nodes")
    return nodes


def _loads_json_content(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        cleaned = cleaned.removesuffix("```").strip()
    return json.loads(cleaned)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()[:120]


def _normalize_keywords(keywords: list[str], fallback: str) -> list[str]:
    cleaned = [keyword.strip() for keyword in keywords if keyword and keyword.strip()]
    if not cleaned:
        cleaned = [fallback.strip()]
    return list(dict.fromkeys(cleaned))[:8]


def _node_from_row(row) -> IndustryNode:
    return IndustryNode(
        id=row["id"],
        analysis_id=row["analysis_id"],
        parent_id=row["parent_id"],
        name=row["name"],
        level=row["level"],
        description=row["description"] or "",
        match_keywords=json.loads(row["match_keywords"]),
        sort_order=row["sort_order"],
    )


