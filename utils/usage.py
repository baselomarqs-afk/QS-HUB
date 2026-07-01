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


def project_entitlement(user: dict, feature: str = "qto") -> dict:
    """Single source of truth for 'can this user create a project right now?'.

    Monthly model: the tier gives `base` projects PER MONTH (resets monthly).
    Add-ons are ONE-TIME credits consumed only when creating beyond the monthly
    base — they are not a permanent bump. So a user can create when they still
    have room in the month OR they hold at least one unused add-on credit.
    """
    user_id = int(user.get("id"))
    role = user.get("role")
    is_admin = role == "admin"
    plan = get_plan_for_user(user_id, role, feature)
    base = plan.projects
    from utils.features import extra_projects_for
    try:
        credits = 0 if is_admin else extra_projects_for(user_id, feature)
    except Exception as e:
        print(f"Error fetching extra projects: {e}")
        credits = 0
    used = monthly_usage(user_id, EVENT_PROJECT, feature)
    can_create = is_admin or (used < base) or (credits > 0)
    return {"base": base, "used": used, "credits": credits, "can_create": can_create, "is_admin": is_admin}


def check_limit(user: dict, event_type: str, amount: int = 1, feature: str = "qto") -> tuple[bool, str]:
    user_id = int(user.get("id"))
    role = user.get("role")
    plan = get_plan_for_user(user_id, role, feature)

    if event_type == EVENT_PROJECT:
        ent = project_entitlement(user, feature)
        if ent["can_create"]:
            return True, "OK"
        return False, (
            f"Monthly project limit reached for {feature}: {ent['used']}/{ent['base']} this month, "
            f"and you have 0 extra projects left. Add a project or upgrade your plan."
        )

    # AI calls / exports still scale with any unused add-ons the user holds.
    from utils.features import extra_projects_for
    try:
        extra_projects = extra_projects_for(user_id, feature)
    except Exception:
        extra_projects = 0
    limits = {
        EVENT_AI_CALL: plan.ai_calls + (extra_projects * 20),
        EVENT_EXPORT: plan.exports + (extra_projects * 5),
    }
    limit = limits.get(event_type)
    if limit is None:
        return True, "OK"
    used = monthly_usage(user_id, event_type, feature)
    if used + amount > limit:
        return False, f"Plan limit reached for {event_type} ({feature}): {used}/{limit}"
    return True, "OK"


def settle_project_creation(user: dict, feature: str = "qto", metadata: dict | None = None) -> None:
    """Log a newly-created project AND spend one add-on credit if it went beyond
    the monthly tier quota. Call this INSTEAD of log_usage at creation time.
    """
    user_id = int(user.get("id"))
    role = user.get("role")
    md = dict(metadata or {})
    if feature != "qto":
        md.setdefault("feature", feature)

    # Count what existed BEFORE this project (fresh, not the 60s-cached value).
    monthly_usage.clear()
    used_before = monthly_usage(user_id, EVENT_PROJECT, feature)

    log_usage(user_id, EVENT_PROJECT, metadata=md)
    monthly_usage.clear()

    if role != "admin":
        plan = get_plan_for_user(user_id, role, feature)
        if used_before >= plan.projects:
            # Monthly quota was already full → this one is covered by a one-time add-on.
            from utils.features import consume_extra_project
            consume_extra_project(user_id, feature, 1)


def check_file_size(user: dict, size_bytes: int) -> tuple[bool, str]:
    plan = get_plan_for_user(int(user.get("id")), user.get("role"))
    max_bytes = plan.max_file_mb * 1024 * 1024
    if size_bytes > max_bytes:
        return False, f"File exceeds plan limit: {plan.max_file_mb} MB"
    return True, "OK"
