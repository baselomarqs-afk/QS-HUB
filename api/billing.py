from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import get_current_user
from utils.payments import create_checkout_session
from utils.plans import PLANS, get_active_subscription, get_plan_for_user
from utils.usage import monthly_usage, EVENT_AI_CALL, EVENT_EXPORT, EVENT_PROJECT
from utils.settings import get_setting
from utils.db import safe_query

router = APIRouter()

@router.get("/subscription")
async def get_subscription_details(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    role = current_user["role"]
    email = current_user["email"]
    
    sub = get_active_subscription(user_id)
    plan = get_plan_for_user(user_id, role)
    
    # Extra projects
    extra_projects = 0
    try:
        df_extra = safe_query("SELECT extra_projects_allowance FROM qto_users WHERE id=%s", (user_id,))
        if not df_extra.empty:
            extra_projects = int(df_extra.iloc[0]["extra_projects_allowance"] or 0)
    except:
        pass
        
    usage_projects = monthly_usage(user_id, EVENT_PROJECT)
    usage_exports = monthly_usage(user_id, EVENT_EXPORT)
    usage_ai = monthly_usage(user_id, EVENT_AI_CALL)
    
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
    current_user: dict = Depends(get_current_user)
):
    try:
        # Map tier back to int if it's a digit
        req_tier = int(tier) if tier.isdigit() else tier
        url = create_checkout_session(current_user, req_tier)
        return {"checkout_url": url}
    except Exception as e:
        # If Dodo payments api is not configured, fall back to mock checkout
        raise HTTPException(
            status_code=500,
            detail=f"Dodo Payments Checkout Error: {str(e)}"
        )

@router.get("/portal")
async def get_portal_url(current_user: dict = Depends(get_current_user)):
    portal_url = get_setting("DODO_CUSTOMER_PORTAL_URL")
    return {"portal_url": portal_url}

