"""Per-feature entitlements (Work Programme / Cash Flow) and their saved history.

Each feature is sold as a one-time 50 AED product that grants ONE credit. A credit
is consumed when a NEW module project is saved. Mirrors the existing
`extra_projects_allowance` add-on model. Provider/Dodo wiring lives in
utils/payments.py; this module only touches the database.
"""
from __future__ import annotations

import json
from datetime import datetime

from utils.db import safe_query, safe_execute

# feature key -> credits column on qto_users
FEATURES = {"programme": "programme_credits", "cashflow": "cashflow_credits"}

# Every tool has its OWN purchasable "extra project" (+1) allowance. This maps a
# feature to the qto_users column that stores that allowance, so the add-on for
# one tool never leaks into another tool's limit.
FEATURE_EXTRA_COL = {
    "qto": "extra_projects_allowance",
    "programme": "programme_credits",
    "cashflow": "cashflow_credits",
}


def extra_projects_for(user_id: int, feature: str) -> int:
    """Purchasable +1 project add-ons the user still has (UNUSED) for THIS tool.

    These are ONE-TIME credits: each is consumed when a project is created beyond
    the monthly tier quota. They are NOT a permanent bump to the monthly limit.
    """
    col = FEATURE_EXTRA_COL.get(feature)
    if not col:
        return 0
    df = safe_query(f"SELECT {col} AS c FROM qto_users WHERE id=%s", (user_id,))
    if df.empty:
        return 0
    try:
        return int(df.iloc[0]["c"] or 0)
    except Exception:
        return 0


def consume_extra_project(user_id: int, feature: str, n: int = 1) -> bool:
    """Atomically spend ONE one-time '+1 project' add-on for this tool.

    The guarded `>= n` clause makes it safe under concurrency and never lets the
    balance go negative. Returns whether the row still had enough to spend.
    """
    col = FEATURE_EXTRA_COL.get(feature)
    if not col:
        return False
    ok, _ = safe_execute(
        f"UPDATE qto_users SET {col} = {col} - %s WHERE id=%s AND {col} >= %s",
        (n, user_id, n),
    )
    return bool(ok)


def _credit_col(feature: str) -> str:
    col = FEATURES.get(feature)
    if not col:
        raise ValueError(f"Unknown feature: {feature}")
    return col


def get_credits(user_id: int, feature: str) -> int:
    col = _credit_col(feature)
    df = safe_query(f"SELECT {col} AS c FROM qto_users WHERE id=%s", (user_id,))
    if df.empty:
        return 0
    try:
        return int(df.iloc[0]["c"] or 0)
    except Exception:
        return 0


def grant_credit(user_id: int, feature: str, n: int = 1):
    col = _credit_col(feature)
    return safe_execute(f"UPDATE qto_users SET {col} = {col} + %s WHERE id=%s", (n, user_id))


def consume_credit(user_id: int, feature: str, n: int = 1):
    col = _credit_col(feature)
    return safe_execute(
        f"UPDATE qto_users SET {col} = {col} - %s WHERE id=%s AND {col} >= %s",
        (n, user_id, n),
    )


def count_projects(user_id: int, feature: str) -> int:
    df = safe_query(
        "SELECT COUNT(*) AS c FROM qto_module_projects WHERE user_id=%s AND feature=%s",
        (user_id, feature),
    )
    if df.empty:
        return 0
    try:
        return int(df.iloc[0]["c"] or 0)
    except Exception:
        return 0


def has_access(user_id: int, feature: str, is_admin: bool = False) -> bool:
    """The tool is visible if the user has a credit to spend OR already owns a
    saved project for that feature (so they keep access to view/edit it)."""
    if is_admin:
        return True
    return get_credits(user_id, feature) > 0 or count_projects(user_id, feature) > 0


def _parse(v):
    try:
        return json.loads(v) if isinstance(v, str) else (v or {})
    except Exception:
        return {}


def save_module_project(user_id, feature, name, config, summary, project_id=None):
    config_json = json.dumps(config or {}, ensure_ascii=False, default=str)
    summary_json = json.dumps(summary or {}, ensure_ascii=False, default=str)
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if project_id:
        safe_execute(
            "UPDATE qto_module_projects SET name=%s, date=%s, config_data=%s, summary_data=%s WHERE id=%s AND user_id=%s AND feature=%s",
            (name, date_str, config_json, summary_json, project_id, user_id, feature),
        )
        return project_id
    ok, err = safe_execute(
        "INSERT INTO qto_module_projects (user_id, feature, name, date, config_data, summary_data) VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, feature, name, date_str, config_json, summary_json),
    )
    if not ok:
        return None
    df = safe_query(
        "SELECT id FROM qto_module_projects WHERE user_id=%s AND feature=%s ORDER BY id DESC LIMIT 1",
        (user_id, feature),
    )
    return int(df.iloc[0]["id"]) if not df.empty else None


def list_module_projects(user_id, feature):
    df = safe_query(
        "SELECT id, name, date, summary_data FROM qto_module_projects WHERE user_id=%s AND feature=%s ORDER BY id DESC",
        (user_id, feature),
    )
    out = []
    for _, row in df.iterrows():
        out.append({
            "id": int(row["id"]), "name": row["name"], "date": row["date"],
            "summary": _parse(row["summary_data"]),
        })
    return out


def get_module_project(user_id, feature, project_id):
    df = safe_query(
        "SELECT id, name, date, config_data, summary_data FROM qto_module_projects WHERE id=%s AND user_id=%s AND feature=%s",
        (project_id, user_id, feature),
    )
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "id": int(row["id"]), "name": row["name"], "date": row["date"],
        "config": _parse(row["config_data"]), "summary": _parse(row["summary_data"]),
    }


def delete_module_project(user_id, feature, project_id):
    return safe_execute(
        "DELETE FROM qto_module_projects WHERE id=%s AND user_id=%s AND feature=%s",
        (project_id, user_id, feature),
    )
