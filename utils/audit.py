"""Audit logging for admin and sensitive SaaS actions."""
from __future__ import annotations

import json
from typing import Any

from utils.db import safe_execute


def audit_log(
    action: str,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    safe_execute(
        """
        INSERT INTO qto_audit_logs
            (actor_user_id, action, target_type, target_id, metadata)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            actor_user_id,
            action,
            target_type,
            str(target_id) if target_id is not None else None,
            json.dumps(metadata or {}, ensure_ascii=False, default=str),
        ),
    )
