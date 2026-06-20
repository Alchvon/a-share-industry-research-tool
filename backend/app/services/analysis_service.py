from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.db import get_connection, init_db
from app.models.analysis import AnalysisDetail, AnalysisRecord, IndustryNode


def now_local() -> datetime:
    return datetime.now().astimezone()


class AnalysisService:
    def create(self, keyword: str) -> AnalysisRecord:
        init_db()
        timestamp = now_local()
        record = AnalysisRecord(
            id=str(uuid.uuid4()),
            keyword=keyword.strip(),
            status="created",
            created_at=timestamp,
            updated_at=timestamp,
        )

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO analysis (id, keyword, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.keyword,
                    record.status,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                ),
            )
            conn.commit()

        return record

    def get(self, analysis_id: str) -> AnalysisDetail | None:
        init_db()
        with get_connection() as conn:
            analysis_row = conn.execute(
                "SELECT * FROM analysis WHERE id = ?",
                (analysis_id,),
            ).fetchone()
            if analysis_row is None:
                return None

            node_rows = conn.execute(
                """
                SELECT * FROM industry_node
                WHERE analysis_id = ?
                ORDER BY sort_order ASC
                """,
                (analysis_id,),
            ).fetchall()

        return AnalysisDetail(
            analysis=_analysis_from_row(analysis_row),
            nodes=[_node_from_row(row) for row in node_rows],
        )

    def list_recent(self, limit: int = 20) -> list[AnalysisRecord]:
        init_db()
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_analysis_from_row(row) for row in rows]

    def delete(self, analysis_id: str) -> bool:
        init_db()
        with get_connection() as conn:
            row = conn.execute("SELECT id FROM analysis WHERE id = ?", (analysis_id,)).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM llm_report WHERE analysis_id = ?", (analysis_id,))
            conn.execute("DELETE FROM company_candidate WHERE analysis_id = ?", (analysis_id,))
            conn.execute("DELETE FROM industry_node WHERE analysis_id = ?", (analysis_id,))
            conn.execute("DELETE FROM analysis WHERE id = ?", (analysis_id,))
            conn.commit()
        return True

    def export_backup(self, analysis_id: str) -> dict[str, object] | None:
        detail = self.get(analysis_id)
        if detail is None:
            return None
        with get_connection() as conn:
            candidate_rows = conn.execute(
                "SELECT * FROM company_candidate WHERE analysis_id = ? ORDER BY industry_node_id, score DESC, stock_code",
                (analysis_id,),
            ).fetchall()
            report_rows = conn.execute(
                "SELECT stock_code, report_type, markdown, created_at FROM llm_report WHERE analysis_id = ? ORDER BY created_at",
                (analysis_id,),
            ).fetchall()
        return {
            "format": "stock-chain-analysis-backup",
            "version": 1,
            "exported_at": now_local().isoformat(),
            "analysis": {
                "keyword": detail.analysis.keyword,
                "status": detail.analysis.status,
                "created_at": detail.analysis.created_at.isoformat(),
            },
            "nodes": [node.model_dump(mode="json") for node in detail.nodes],
            "candidates": [
                {
                    "industry_node_id": row["industry_node_id"],
                    "stock_code": row["stock_code"],
                    "stock_name": row["stock_name"],
                    "reason": row["reason"],
                    "market_cap": row["market_cap"],
                    "revenue": row["revenue"],
                    "roe": row["roe"],
                    "score": row["score"],
                    "is_user_selected": bool(row["is_user_selected"]),
                }
                for row in candidate_rows
            ],
            "reports": [dict(row) for row in report_rows],
        }

    def import_backup(self, backup: dict[str, object]) -> tuple[AnalysisRecord, int, int, int]:
        if backup.get("format") != "stock-chain-analysis-backup":
            raise ValueError("不是本工具导出的备份文件")
        source_analysis = backup.get("analysis")
        if not isinstance(source_analysis, dict) or not str(source_analysis.get("keyword") or "").strip():
            raise ValueError("备份文件缺少研究主题")
        raw_nodes = backup.get("nodes")
        raw_candidates = backup.get("candidates")
        raw_reports = backup.get("reports")
        if not isinstance(raw_nodes, list) or not isinstance(raw_candidates, list):
            raise ValueError("备份文件结构不完整")
        if len(raw_nodes) > 100 or len(raw_candidates) > 1000:
            raise ValueError("备份文件超过本地导入上限")

        record = self.create(str(source_analysis["keyword"]).strip())
        node_id_map: dict[str, str] = {}
        imported_nodes = 0
        imported_candidates = 0
        imported_reports = 0
        with get_connection() as conn:
            for index, raw_node in enumerate(raw_nodes, start=1):
                if not isinstance(raw_node, dict) or not str(raw_node.get("name") or "").strip():
                    continue
                old_id = str(raw_node.get("id") or "")
                new_id = str(uuid.uuid4())
                node_id_map[old_id] = new_id
                conn.execute(
                    """
                    INSERT INTO industry_node (id, analysis_id, parent_id, name, level, description, match_keywords, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_id,
                        record.id,
                        None,
                        str(raw_node["name"]).strip(),
                        max(1, min(int(raw_node.get("level") or 1), 3)),
                        str(raw_node.get("description") or ""),
                        json.dumps(raw_node.get("match_keywords") or [], ensure_ascii=False),
                        index,
                    ),
                )
                imported_nodes += 1

            for raw_candidate in raw_candidates:
                if not isinstance(raw_candidate, dict):
                    continue
                target_node_id = node_id_map.get(str(raw_candidate.get("industry_node_id") or ""))
                code = str(raw_candidate.get("stock_code") or "").strip()
                name = str(raw_candidate.get("stock_name") or "").strip()
                if not target_node_id or len(code) != 6 or not name:
                    continue
                conn.execute(
                    """
                    INSERT INTO company_candidate (id, analysis_id, industry_node_id, stock_code, stock_name, reason, market_cap, revenue, roe, score, is_user_selected)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()), record.id, target_node_id, code, name,
                        raw_candidate.get("reason"), raw_candidate.get("market_cap"), raw_candidate.get("revenue"),
                        raw_candidate.get("roe"), raw_candidate.get("score"), int(bool(raw_candidate.get("is_user_selected", True))),
                    ),
                )
                imported_candidates += 1

            for raw_report in raw_reports if isinstance(raw_reports, list) else []:
                if not isinstance(raw_report, dict) or not str(raw_report.get("stock_code") or "").strip() or not str(raw_report.get("markdown") or ""):
                    continue
                conn.execute(
                    "INSERT INTO llm_report (id, analysis_id, stock_code, report_type, markdown, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid.uuid4()), record.id, str(raw_report["stock_code"]).strip(),
                        str(raw_report.get("report_type") or "overview"), str(raw_report["markdown"]),
                        str(raw_report.get("created_at") or now_local().isoformat()),
                    ),
                )
                imported_reports += 1
            conn.commit()

        status = str(source_analysis.get("status") or "matched")
        self.update_status(record.id, status if status in {"created", "decomposed", "matched"} else "matched")
        refreshed = self.get(record.id)
        return refreshed.analysis if refreshed else record, imported_nodes, imported_candidates, imported_reports
    def update_status(self, analysis_id: str, status: str) -> None:

        init_db()
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE analysis
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, now_local().isoformat(), analysis_id),
            )
            conn.commit()


def _analysis_from_row(row) -> AnalysisRecord:
    return AnalysisRecord(
        id=row["id"],
        keyword=row["keyword"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


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



