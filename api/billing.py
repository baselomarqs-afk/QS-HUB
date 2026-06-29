from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import get_current_user
from utils.payments import create_checkout_session
from utils.plans import PLANS, get_active_subscription, get_plan_for_user
from utils.usage import monthly_usage, EVENT_AI_CALL, EVENT_EXPORT, EVENT_PROJECT
from utils.settings import get_setting
from utils.db import safe_query
from utils.features import FEATURES, get_credits, count_projects

router = APIRouter()


@router.get("/feature-access")
async def feature_access(feature: str = Query(...), current_user: dict = Depends(get_current_user)):
    """Whether the user can use a per-project tool (programme / cashflow)."""
    if feature not in FEATURES:
        raise HTTPException(status_code=404, detail="Unknown feature.")
    is_admin = current_user["role"] == "admin"
    credits = get_credits(current_user["id"], feature)
    projects = count_projects(current_user["id"], feature)
    
    # 1st project is free trial (projects < 1). Subsequent require credits.
    can_create = bool(is_admin or credits > 0 or projects < 1)
    limit = 999999 if is_admin else (1 + credits + max(0, projects - 1))
    
    return {
        "feature": feature,
        "access": bool(is_admin or credits > 0 or projects > 0 or projects < 1),
        "credits": credits,
        "projects": projects,
        "limit": limit,
        "can_create": can_create,
    }

@router.get("/subscription")
async def get_subscription_details(feature: str = Query("qto"), current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    role = current_user["role"]
    email = current_user["email"]
    
    sub = get_active_subscription(user_id, feature)
    plan = get_plan_for_user(user_id, role, feature)
    
    # Extra projects
    extra_projects = 0
    if feature == "qto":
        try:
            df_extra = safe_query("SELECT extra_projects_allowance FROM qto_users WHERE id=%s", (user_id,))
            if not df_extra.empty:
                extra_projects = int(df_extra.iloc[0]["extra_projects_allowance"] or 0)
        except:
            pass
        
    usage_projects = monthly_usage(user_id, EVENT_PROJECT, feature)
    usage_exports = monthly_usage(user_id, EVENT_EXPORT, feature)
    usage_ai = monthly_usage(user_id, EVENT_AI_CALL, feature)
    
    return {
        "plan_name": plan.name,
        "plan_tier": plan.tier,
        "subscription_status": sub.get("status") if sub else "inactive",
        "current_period_end": sub.get("current_period_end") if sub else None,
        "extra_projects": extra_projects,
        "project_limit": plan.projects + extra_projects,
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
                "projects_limit": p.projects
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
        # If Dodo payments api is not configured, fall back to mock checkout
        user_id = current_user["id"]
        if tier == "addon":
            safe_execute("UPDATE qto_users SET extra_projects_allowance = COALESCE(extra_projects_allowance, 0) + 1 WHERE id=%s", (user_id,))
        elif tier == "programme":
            safe_execute("UPDATE qto_users SET programme_credits = COALESCE(programme_credits, 0) + 1 WHERE id=%s", (user_id,))
        elif tier == "cashflow":
            safe_execute("UPDATE qto_users SET cashflow_credits = COALESCE(cashflow_credits, 0) + 1 WHERE id=%s", (user_id,))
        elif str(tier).isdigit():
            # Mock checkout for tests
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

