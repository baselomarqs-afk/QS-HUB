"""Simple DB-backed background job scaffolding."""
from __future__ import annotations

import json
from typing import Any

from utils.db import get_connection, safe_execute, safe_query


def enqueue_job(
    job_type: str,
    payload: dict[str, Any],
    user_id: int | None = None,
    project_id: int | None = None,
) -> int | None:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO qto_background_jobs (user_id, project_id, job_type, status, payload)
                    VALUES (%s, %s, %s, 'queued', %s)
                    """,
                    (user_id, project_id, job_type, json.dumps(payload, ensure_ascii=False, default=str)),
                )
                job_id = cur.lastrowid
            conn.commit()
        return int(job_id) if job_id else None
    except Exception:
        return None


def next_job(job_type: str | None = None) -> dict | None:
    if job_type:
        df = safe_query(
            "SELECT * FROM qto_background_jobs WHERE status='queued' AND job_type=%s ORDER BY id LIMIT 1",
            (job_type,),
        )
    else:
        df = safe_query("SELECT * FROM qto_background_jobs WHERE status='queued' ORDER BY id LIMIT 1")
    if df.empty:
        return None
    return df.to_dict("records")[0]


def mark_job_started(job_id: int) -> None:
    safe_execute("UPDATE qto_background_jobs SET status='running', started_at=NOW() WHERE id=%s", (job_id,))


def mark_job_done(job_id: int, result: dict[str, Any] | None = None) -> None:
    safe_execute(
        "UPDATE qto_background_jobs SET status='done', result=%s, finished_at=NOW() WHERE id=%s",
        (json.dumps(result or {}, ensure_ascii=False, default=str), job_id),
    )


def mark_job_failed(job_id: int, error: str) -> None:
    safe_execute(
        "UPDATE qto_background_jobs SET status='failed', error=%s, finished_at=NOW() WHERE id=%s",
        (error[:5000], job_id),
    )
