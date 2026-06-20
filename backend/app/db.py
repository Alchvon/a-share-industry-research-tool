from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS analysis (
  id TEXT PRIMARY KEY,
  keyword TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS industry_node (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  parent_id TEXT,
  name TEXT NOT NULL,
  level INTEGER NOT NULL,
  description TEXT,
  match_keywords TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS company_candidate (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  industry_node_id TEXT NOT NULL,
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  reason TEXT,
  market_cap REAL,
  revenue REAL,
  roe REAL,
  score REAL,
  is_user_selected INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS stock_snapshot (
  cache_key TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS llm_report (
  id TEXT PRIMARY KEY,
  analysis_id TEXT NOT NULL,
  stock_code TEXT NOT NULL,
  report_type TEXT NOT NULL,
  markdown TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(SCHEMA)

