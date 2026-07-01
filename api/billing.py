from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import get_current_user
from utils.payments import create_checkout_session, auto_sync_user_subscriptions, force_activate_subscription, sync_user_addons
from utils.plans import PLANS, get_active_subscription, get_plan_for_user
from utils.usage import monthly_usage, EVENT_AI_CALL, EVENT_EXPORT, EVENT_PROJECT
from utils.settings import get_setting
from utils.db import safe_query, safe_execute
from utils.features import FEATURES, get_credits, count_projects

router = APIRouter()


@router.get("/feature-access")
async def feature_access(feature: str = Query(...), current_user: dict = Depends(get_current_user)):
    """Whether the user can use a per-project tool (programme / cashflow)."""
    if feature not in FEATURES:
        raise HTTPException(status_code=404, detail="Unknown feature.")
    
    user_id = current_user["id"]
    role = current_user["role"]
    email = current_user["email"]
    is_admin = role == "admin"

    # Auto-sync from Dodo API — so even if webhook was missed, subscription activates on next Dashboard load.
    # (Add-on reconciliation is done only in /subscription to avoid concurrent double-grants, since that
    # endpoint runs once per load and sync_user_addons already grants add-ons for ALL tools in one pass.)
    try:
        auto_sync_user_subscriptions(user_id, email)
    except Exception:
        pass

    plan = get_plan_for_user(user_id, role, feature)

    # Per-tool add-on allowance (qto -> extra_projects_allowance,
    # programme -> programme_credits, cashflow -> cashflow_credits).
    from utils.features import extra_projects_for
    extra_projects = 0 if is_admin else extra_projects_for(user_id, feature)

    # "used" is the SAME monthly count the creation gate (check_limit) uses, so
    # the "X / limit" shown on the dashboard always matches when the button flips.
    projects = monthly_usage(user_id, EVENT_PROJECT, feature)

    limit = 999999 if is_admin else (plan.projects + extra_projects)
    # Consumable model: can create if there's room in the monthly tier quota OR
    # the user still holds an unused one-time add-on credit.
    can_create = is_admin or (projects < plan.projects) or (extra_projects > 0)
    # Keep access to previously-saved projects even after the monthly quota
    # resets or the subscription lapses (viewing history must not disappear).
    total_saved = count_projects(user_id, feature)
    has_had_trial = False
    try:
        df_past = safe_query("SELECT id FROM qto_subscriptions WHERE user_id=%s AND feature=%s LIMIT 1", (user_id, feature))
        has_had_trial = not df_past.empty
    except:
        pass
        
    return {
        "feature": feature,
        "access": is_admin or can_create or total_saved > 0,
        "credits": extra_projects,
        "projects": projects,
        "limit": limit,
        "can_create": can_create,
        "plan_tier": plan.tier,
        "has_had_trial": has_had_trial,
    }

@router.post("/activate")
async def activate_after_payment(feature: str = Query("qto"), current_user: dict = Depends(get_current_user)):
    """Called by the frontend the moment the user returns from Dodo checkout.

    Synchronous + uncached: pulls the subscription straight from Dodo, writes it,
    clears the plan caches, and returns the confirmed status. This is the
    authoritative activation path — it does not depend on the webhook arriving.
    """
    result = force_activate_subscription(current_user["id"], current_user["email"], feature)
    return result


@router.get("/subscription")
async def get_subscription_details(feature: str = Query("qto"), current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    role = current_user["role"]
    email = current_user["email"]

    # Auto-sync on every load: pull subscriptions AND add-ons from Dodo and
    # reconcile any missing ones. This is the authoritative recovery path — it
    # does not rely on the webhook OR on the post-payment redirect reaching the
    # app (which it doesn't, since the app is embedded in an iframe).
    try:
        auto_sync_user_subscriptions(user_id, email)
        sync_user_addons(user_id, email)
    except Exception:
        pass

    sub = get_active_subscription(user_id, feature)
    plan = get_plan_for_user(user_id, role, feature)
    
    # Extra projects (per-tool add-on allowance)
    from utils.features import extra_projects_for
    extra_projects = extra_projects_for(user_id, feature)
        
    usage_projects = monthly_usage(user_id, EVENT_PROJECT, feature)
    usage_exports = monthly_usage(user_id, EVENT_EXPORT, feature)
    usage_ai = monthly_usage(user_id, EVENT_AI_CALL, feature)
    
    has_had_trial = False
    try:
        df_past = safe_query("SELECT id FROM qto_subscriptions WHERE user_id=%s AND feature=%s LIMIT 1", (user_id, feature))
        has_had_trial = not df_past.empty
    except:
        pass

    is_admin = role == "admin"
    # Consumable model: create if there's monthly room OR an unused add-on credit.
    can_create = is_admin or (usage_projects < plan.projects) or (extra_projects > 0)

    return {
        "plan_name": plan.name,
        "plan_tier": plan.tier,
        "subscription_status": sub.get("status") if sub else "inactive",
        "current_period_end": sub.get("current_period_end") if sub else None,
        "extra_projects": extra_projects,
        "project_limit": plan.projects + extra_projects,
        "can_create": can_create,
        "monthly_base": plan.projects,
        "has_had_trial": has_had_trial,
        "usage": {
            "projects": usage_projects,
            "exports": usage_exports,
            "ai_calls": usage_ai
        },
        "plans_catalog": [
            {
                "tier": tier,
                "name": p.name,
                "price_aed": p.monthly_price_aed,
                "projects_limit": p.projects,
                "ai_calls": p.ai_calls,
                "exports": p.exports
            } for tier, p in PLANS.items() if tier > 0
        ]
    }

@router.get("/checkout")
async def get_checkout_url(
    tier: str = Query(...), # e.g. "1", "2", "3", "4", "addon"
    feature: str = Query("qto"), # "qto", "programme", "cashflow"
    current_user: dict = Depends(get_current_user)
):
    try:
        # Map tier back to int if it's a digit
        req_tier = int(tier) if tier.isdigit() else tier
        url = create_checkout_session(current_user, req_tier, feature)
        return {"checkout_url": url}
    except Exception as e:
        # DANGER ZONE: never grant a subscription/credit for free when Dodo is
        # actually configured. Doing so on a transient Dodo error used to create
        # phantom "manual" subscriptions (e.g. a tier-2 plan the user never paid
        # for). The mock path is ONLY for local/dev where no Dodo key exists.
        if get_setting("DODO_PAYMENTS_API_KEY"):
            raise HTTPException(
                status_code=502,
                detail="Could not start checkout. Please try again in a moment.",
            )
        # --- Local/dev only (no Dodo key): mock checkout so tests can run ---
        user_id = current_user["id"]
        if tier == "addon":
            from utils.features import FEATURE_EXTRA_COL
            col = FEATURE_EXTRA_COL.get(feature, "extra_projects_allowance")
            safe_execute(f"UPDATE qto_users SET {col} = COALESCE({col}, 0) + 1 WHERE id=%s", (user_id,))
        elif str(tier).isdigit():
            safe_execute("INSERT INTO qto_subscriptions (user_id, feature, plan_tier, provider, provider_subscription_id, status) VALUES (%s, %s, %s, 'manual', 'mock_123', 'active')", (user_id, feature, int(tier)))

        return {"checkout_url": "/"}

@router.get("/portal")
async def get_portal_url(current_user: dict = Depends(get_current_user)):
    try:
        from utils.payments import create_portal_session
        url = create_portal_session(current_user["id"])
        return {"portal_url": url}
    except Exception as e:
        # Fallback to static URL if no subscription
        portal_url = get_setting("DODO_CUSTOMER_PORTAL_URL")
        if portal_url:
            return {"portal_url": portal_url}
        raise HTTPException(status_code=400, detail=str(e))



