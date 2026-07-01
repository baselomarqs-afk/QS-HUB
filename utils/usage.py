"""Usage accounting and entitlement enforcement."""
from __future__ import annotations

import json
from typing import Any

from utils.db import safe_execute, safe_query
from utils.plans import get_plan_for_user, ttl_cache
from utils.db import is_sqlite


EVENT_PROJECT = "project_created"
EVENT_AI_CALL = "ai_call"
EVENT_EXPORT = "export"


def log_usage(
    user_id: int | None,
    event_type: str,
    quantity: int = 1,
    project_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    safe_execute(
        """
        INSERT INTO qto_usage_logs (user_id, project_id, event_type, quantity, metadata)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            user_id,
            project_id,
            event_type,
            quantity,
            json.dumps(metadata or {}, ensure_ascii=False, default=str),
        ),
    )


@ttl_cache(ttl_seconds=60)
def monthly_usage(user_id: int, event_type: str, feature: str = "qto") -> int:
    if is_sqlite():
        df = safe_query(
            """
            SELECT quantity, metadata
            FROM qto_usage_logs
            WHERE user_id=%s
              AND event_type=%s
              AND created_at >= date('now', 'start of month')
            """,
            (user_id, event_type),
        )
    else:
        df = safe_query(
            """
            SELECT quantity, metadata
            FROM qto_usage_logs
            WHERE user_id=%s
              AND event_type=%s
              AND created_at >= DATE_FORMAT(CURRENT_DATE, '%%Y-%%m-01')
            """,
            (user_id, event_type),
        )
    
    if df.empty:
        return 0
        
    total = 0
    for _, row in df.iterrows():
        try:
            meta = json.loads(row["metadata"] or "{}")
            row_feature = meta.get("feature", "qto")
            if row_feature == feature:
                total += int(row["quantity"] or 0)
        except Exception:
            pass
            
    return total


def check_limit(user: dict, event_type: str, amount: int = 1, feature: str = "qto") -> tuple[bool, str]:
    user_id = int(user.get("id"))
    role = user.get("role")
    plan = get_plan_for_user(user_id, role, feature)

    # Per-tool add-on allowance (each tool has its own +1 project products).
    from utils.features import extra_projects_for
    try:
        extra_projects = extra_projects_for(user_id, feature)
    except Exception as e:
        print(f"Error fetching extra projects: {e}")
        extra_projects = 0

    limits = {
        EVENT_PROJECT: plan.projects + extra_projects,
        EVENT_AI_CALL: plan.ai_calls + (extra_projects * 20),
        EVENT_EXPORT: plan.exports + (extra_projects * 5),
    }
    limit = limits.get(event_type)
    if limit is None:
        return True, "OK"
    used = monthly_usage(user_id, event_type, feature)
    if used + amount > limit:
        # Distinguish "base plan exhausted" from "extras also exhausted".
        if event_type == EVENT_PROJECT and used >= (plan.projects + extra_projects):
            return False, f"Plan limit reached for {event_type} ({feature}): {used}/{limit}. You have 0 extra projects remaining."
        return False, f"Plan limit reached for {event_type} ({feature}): {used}/{limit}"
    return True, "OK"


def check_file_size(user: dict, size_bytes: int) -> tuple[bool, str]:
    plan = get_plan_for_user(int(user.get("id")), user.get("role"))
    max_bytes = plan.max_file_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"File exceeds plan limit: {plan.max_file_mb} MB"
    return True, "OK"
