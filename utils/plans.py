"""Subscription plans and entitlement checks."""
from __future__ import annotations

from dataclasses import dataclass

from utils.db import safe_query
import time

def ttl_cache(ttl_seconds: int = 300):
    def decorator(func):
        cache = {}
        def wrapped(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in cache:
                val, timestamp = cache[key]
                if now - timestamp < ttl_seconds:
                    return val
            val = func(*args, **kwargs)
            cache[key] = (val, now)
            return val
        
        def clear():
            cache.clear()
        wrapped.clear = clear
        return wrapped
    return decorator


@dataclass(frozen=True)
class PlanLimits:
    tier: int
    name: str
    monthly_price_aed: int
    projects: int
    ai_calls: int
    exports: int
    max_file_mb: int


PLANS: dict[int, PlanLimits] = {
    0: PlanLimits(0, "Inactive", 0, 0, 0, 0, 0),
    1: PlanLimits(1, "Starter", 50, 1, 40, 5, 25),
    2: PlanLimits(2, "Professional", 120, 3, 150, 20, 50),
    3: PlanLimits(3, "Business", 250, 8, 600, 80, 100),
    4: PlanLimits(4, "Studio", 500, 20, 2000, 250, 200),
}


@ttl_cache(ttl_seconds=300)
def get_active_subscription(user_id: int, feature: str = "qto") -> dict | None:
    df = safe_query(
        """
        SELECT id, user_id, feature, plan_tier, provider, provider_customer_id,
               provider_subscription_id, status,
               current_period_start, current_period_end, cancel_at_period_end,
               projects_used, ai_calls_used, exports_used, created_at, updated_at
        FROM qto_subscriptions
        WHERE user_id=%s AND feature=%s AND status IN ('active', 'trialing')
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, feature),
    )
    if df.empty:
        return None
    return df.to_dict("records")[0]


@ttl_cache(ttl_seconds=300)
def get_plan_for_user(user_id: int, role: str | None = None, feature: str = "qto") -> PlanLimits:
    if role == "admin":
        return PlanLimits(99, "Admin", 0, 999999, 999999, 999999, 500)
    sub = get_active_subscription(user_id, feature)
    return PLANS.get(int(sub.get("plan_tier", 0)), PLANS[0]) if sub else PLANS[0]
