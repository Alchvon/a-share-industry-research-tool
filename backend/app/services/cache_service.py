from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import CACHE_TTL_SECONDS
from app.db import get_connection, init_db


UTC = timezone.utc


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_json(cache_key: str) -> dict[str, Any] | None:
    init_db()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, expires_at FROM stock_snapshot WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()

    if row is None:
        return None

    expires_at = datetime.fromisoformat(row["expires_at"])
    if expires_at <= now_utc():
        return None

    return json.loads(row["payload"])


def set_json(cache_key: str, payload: dict[str, Any], ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
    init_db()
    fetched_at = now_utc()
    expires_at = fetched_at + timedelta(seconds=ttl_seconds)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO stock_snapshot (cache_key, payload, fetched_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
              payload = excluded.payload,
              fetched_at = excluded.fetched_at,
              expires_at = excluded.expires_at
            """,
            (
                cache_key,
                json.dumps(payload, ensure_ascii=False),
                fetched_at.isoformat(),
                expires_at.isoformat(),
            ),
        )
        conn.commit()
