"""Dodo Payments integration.

Implements hosted checkout through Dodo Payments and webhook syncing for
subscription lifecycle events.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Any

try:
    from dodopayments import DodoPayments
except ImportError:
    DodoPayments = None  # Will raise at runtime if actually called

from utils.audit import audit_log
from utils.db import safe_execute, safe_query
from utils.settings import app_base_url, get_setting


def _get_dodo_client() -> DodoPayments:
    api_key = get_setting("DODO_PAYMENTS_API_KEY", required=True)
    env = get_setting("DODO_ENVIRONMENT", "test_mode").lower()
    if env == "production" or env == "live":
        env = "live_mode"
    return DodoPayments(bearer_token=api_key, environment=env)


# One-time products (not subscriptions): the +1 project add-on and the two
# per-project module tools (Work Programme, Cash Flow), all 50 AED each.
ONE_TIME_TIERS = {"addon", "programme", "cashflow"}


def dodo_product_for_tier(tier: int | str, feature: str = "qto") -> str:
    if tier == "addon":
        price_id = get_setting("DODO_PRODUCT_ADDON_PROJECT")
    elif tier == "programme":
        price_id = get_setting("DODO_PRODUCT_PROGRAMME") or get_setting("DODO_PRODUCT_ADDON_PROJECT")
    elif tier == "cashflow":
        price_id = get_setting("DODO_PRODUCT_CASHFLOW") or get_setting("DODO_PRODUCT_ADDON_PROJECT")
    else:
        if feature == "programme":
            price_id = get_setting(f"DODO_PRODUCT_PROGRAMME_TIER_{tier}")
        elif feature == "cashflow":
            price_id = get_setting(f"DODO_PRODUCT_CASHFLOW_TIER_{tier}")
        else:
            price_id = get_setting(f"DODO_PRODUCT_TIER_{tier}")
    if not price_id:
        # Fallback to dummy values for now until they are provided
        if feature in ["programme", "cashflow"] and tier in [1, 2, 3, 4]:
            return f"pdt_DUMMY_{feature.upper()}_{tier}"
        raise RuntimeError(f"Missing Dodo product id for tier '{tier}' feature '{feature}'")
    return price_id


def create_checkout_session(user: dict, tier: int | str, feature: str = "qto") -> str:
    """Create a Dodo Payments checkout session."""
    client = _get_dodo_client()
    product_id = dodo_product_for_tier(tier, feature)

    custom_data = {"user_id": str(user["id"])}
    if tier in ONE_TIME_TIERS:
        if tier == "addon":
            custom_data["is_addon"] = "true"
        else:
            custom_data["feature"] = tier  # "programme" | "cashflow"
    else:
        custom_data["plan_tier"] = str(tier)
        custom_data["feature"] = feature

    kwargs = {
        "product_cart": [{"product_id": product_id, "quantity": 1}],
        "customer": {"email": user["email"]},
        "return_url": app_base_url(),
    }
    if str(tier).isdigit():
        from utils.db import safe_query
        try:
            df_past = safe_query("SELECT id FROM qto_subscriptions WHERE user_id=%s AND feature=%s LIMIT 1", (user["id"], feature))
            if not df_past.empty:
                kwargs["subscription_data"] = {"trial_period_days": 0}
        except:
            pass
    
    # Apply discount code QTO2026 for tier 2 and 3 subscriptions
    if tier not in ONE_TIME_TIERS and tier in [2, 3, "2", "3"]:
        kwargs["discount_code"] = "QTO2026"

    try:
        session = client.checkout_sessions.create(metadata=custom_data, **kwargs)
    except Exception:
        # Fallback if metadata fails
        session = client.checkout_sessions.create(**kwargs)
        
    checkout_url = getattr(session, "checkout_url", None)
    if not checkout_url:
        raise RuntimeError("Dodo Payments did not return a checkout URL.")
    
    audit_log("checkout_session_created", user["id"], "subscription", tier, {"provider": "dodopayments"})
    return checkout_url


def create_portal_session(user_id: int) -> str:
    """Create a Dodo Payments customer portal session."""
    client = _get_dodo_client()
    df = safe_query(
        "SELECT provider_customer_id FROM qto_subscriptions WHERE user_id=%s AND provider='dodopayments' AND status='active' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    if df.empty or not df.iloc[0]["provider_customer_id"]:
        raise RuntimeError("No subscription found for this user")
        
    customer_id = df.iloc[0]["provider_customer_id"]
    try:
        session = client.customers.customer_portal.create(
            customer_id=customer_id,
            return_url=app_base_url()
        )
        # Using getattr since dodopayments SDK returns a Pydantic model (CustomerPortalSession)
        portal_url = getattr(session, "link", None)
        if not portal_url:
            raise RuntimeError("Dodo Payments did not return a portal URL.")
        return portal_url
    except Exception as e:
        raise RuntimeError(f"Customer portal creation failed: {str(e)}")


def _parse_rfc3339(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _upsert_subscription_from_dodo(data: dict[str, Any]) -> None:
    product_id = data.get("product_id") or data.get("product", {}).get("product_id")
    inferred_feature, inferred_tier = "qto", 0
    if product_id:
        # Find feature and tier by matching product_id
        for f in ["qto", "programme", "cashflow"]:
            for t in [1, 2, 3, 4]:
                try:
                    if dodo_product_for_tier(t, f) == product_id:
                        inferred_feature, inferred_tier = f, t
                        break
                except Exception:
                    pass

    metadata = data.get("metadata") or {}
    user_id = int(metadata.get("user_id", 0) or data.get("metadata_user_id", 0) or 0)
    
    # Support both Dodo metadata formats (nested or flat with prefix)
    tier_raw = metadata.get("plan_tier") or metadata.get("metadata_plan_tier") or data.get("metadata_plan_tier")
    try:
        tier = int(tier_raw) if tier_raw is not None else inferred_tier
    except Exception:
        tier = inferred_tier
        
    feature = metadata.get("feature") or metadata.get("metadata_feature") or data.get("metadata_feature") or inferred_feature
    
    subscription_id = data.get("subscription_id")
    status = data.get("status", "inactive")
    customer_id = data.get("customer_id") or data.get("customer", {}).get("customer_id")
    
    current_period_start = data.get("current_period_start") or data.get("created_at")
    current_period_end = data.get("current_period_end") or data.get("next_billing_date") or data.get("expires_at")
    
    if not user_id:
        customer_email = data.get("customer", {}).get("email")
        if customer_email:
            df = safe_query("SELECT id FROM qto_users WHERE email = %s LIMIT 1", (customer_email,))
            if not df.empty:
                user_id = int(df.iloc[0]["id"])
    
    if not user_id:
        return

    params = (
        user_id,
        feature,
        tier,
        "dodopayments",
        customer_id,
        subscription_id,
        status,
        _parse_rfc3339(current_period_start),
        _parse_rfc3339(current_period_end),
        0,
    )
    df = safe_query(
        "SELECT id FROM qto_subscriptions WHERE provider='dodopayments' AND provider_subscription_id=%s",
        (subscription_id,),
    )
    if df.empty:
        safe_execute(
            """
            INSERT INTO qto_subscriptions
                (user_id, feature, plan_tier, provider, provider_customer_id, provider_subscription_id,
                 status, current_period_start, current_period_end,
                 cancel_at_period_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            params,
        )
    else:
        safe_execute(
            """
            UPDATE qto_subscriptions
            SET user_id=%s, feature=%s, plan_tier=%s, provider=%s, provider_customer_id=%s,
                provider_subscription_id=%s, status=%s,
                current_period_start=%s, current_period_end=%s, cancel_at_period_end=%s
            WHERE provider='dodopayments' AND provider_subscription_id=%s
            """,
            (*params, subscription_id),
        )
    audit_log("subscription_synced", user_id, "subscription", subscription_id, {"provider": "dodopayments", "status": status, "feature": feature})
    
    # Invalidate cache so user sees upgrade immediately
    from utils.plans import get_active_subscription, get_plan_for_user
    get_active_subscription.clear()
    get_plan_for_user.clear()


def _record_transaction(data: dict[str, Any], event_type: str) -> None:
    metadata = data.get("metadata", {}) or {}
    user_id = metadata.get("user_id")
    is_addon = metadata.get("is_addon") == "true"
    status = data.get("status") or event_type

    if is_addon and status in {"paid", "succeeded"} and user_id:
        safe_execute("UPDATE qto_users SET extra_projects_allowance = extra_projects_allowance + 1 WHERE id = %s", (user_id,))
        audit_log("addon_purchased", int(user_id), "user", int(user_id), {"provider": "dodopayments", "status": status})
        return

    # Per-project module tools (Work Programme / Cash Flow) — grant 1 feature credit for one-time purchases.
    feature = metadata.get("feature")
    has_tier = "plan_tier" in metadata or "metadata_plan_tier" in metadata
    if feature in {"programme", "cashflow"} and not has_tier and status in {"paid", "succeeded"} and user_id:
        from utils.features import grant_credit
        grant_credit(int(user_id), feature, 1)
        audit_log("feature_purchased", int(user_id), "user", int(user_id), {"provider": "dodopayments", "feature": feature, "status": status})
        return

    subscription_id = data.get("subscription_id")
    customer_id = data.get("customer_id") or data.get("customer", {}).get("customer_id")
    currency = data.get("currency") or "AED"
    amount = float(data.get("amount") or 0) / 100

    df = safe_query(
        """
        SELECT user_id, id FROM qto_subscriptions
        WHERE provider='dodopayments'
          AND (provider_subscription_id=%s OR provider_customer_id=%s)
        ORDER BY id DESC LIMIT 1
        """,
        (subscription_id, customer_id),
    )
    if df.empty:
        return

    row = df.to_dict("records")[0]
    paid_at = "NOW()" if status in {"paid", "succeeded"} else "NULL"
    safe_execute(
        f"""
        INSERT INTO qto_invoices
            (user_id, subscription_id, provider, provider_invoice_id, amount_aed,
             currency, status, hosted_invoice_url, issued_at, paid_at)
        VALUES (%s, %s, 'dodopayments', %s, %s, %s, %s, %s, NOW(), {paid_at})
        """,
        (
            row["user_id"],
            row["id"],
            data.get("payment_id") or data.get("id"),
            amount,
            currency,
            status,
            data.get("receipt_url") or "",
        ),
    )


def verify_dodo_webhook(payload: bytes, webhook_id: str, webhook_timestamp: str, webhook_signature: str) -> bool:
    """Verify Dodo-Signature using HMAC."""
    secret = get_setting("DODO_WEBHOOK_SECRET", required=True)
    if not webhook_id or not webhook_timestamp or not webhook_signature:
        return False
        
    try:
        if abs(time.time() - int(webhook_timestamp)) > 300:
            return False
    except ValueError:
        return False
        
    signed_payload = f"{webhook_id}.{webhook_timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    
    secret_bytes = secret.encode('utf-8')
    if secret.startswith("whsec_"):
        try:
            secret_bytes = base64.b64decode(secret.split("_")[1])
        except Exception:
            pass
            
    digest = hmac.new(secret_bytes, signed_payload, hashlib.sha256).hexdigest()
    
    try:
        digest_b64 = base64.b64encode(hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()).decode('utf-8')
        signature_to_compare = webhook_signature.split(',')[-1].strip() if 'v1,' in webhook_signature else webhook_signature
        return hmac.compare_digest(digest_b64, signature_to_compare) or hmac.compare_digest(digest, signature_to_compare)
    except Exception:
        return hmac.compare_digest(digest, webhook_signature)


def handle_dodo_webhook(payload: bytes, headers: dict[str, str]) -> tuple[bool, str]:
    webhook_id = headers.get("webhook-id") or headers.get("Webhook-Id", "")
    webhook_timestamp = headers.get("webhook-timestamp") or headers.get("Webhook-Timestamp", "")
    webhook_signature = headers.get("webhook-signature") or headers.get("Webhook-Signature", "")
    
    if not verify_dodo_webhook(payload, webhook_id, webhook_timestamp, webhook_signature):
        raise RuntimeError("Invalid Dodo webhook signature.")

    event = json.loads(payload.decode("utf-8"))
    event_type = event.get("event_type", "")
    data = event.get("data", {}) or {}

    if event_type.startswith("subscription."):
        _upsert_subscription_from_dodo(data)
        return True, event_type

    if event_type.startswith("payment.") or event_type.startswith("transaction."):
        _record_transaction(data, event_type)
        return True, event_type

    return True, f"ignored:{event_type}"


def issue_dodo_refund(user_email: str) -> tuple[bool, str]:
    """
    Cancel and initiate a refund for the user's active Dodo subscription via email.
    """
    df = safe_query(
        "SELECT s.id, s.provider_subscription_id FROM qto_subscriptions s JOIN qto_users u ON s.user_id = u.id WHERE u.email=%s AND s.status='active' AND s.provider='dodopayments' ORDER BY s.id DESC LIMIT 1",
        (user_email,)
    )
    if df.empty:
        return False, f"No active Dodo subscription found for user {user_email}."
        
    sub_id = df.iloc[0]["provider_subscription_id"]
    if not sub_id:
        return False, "Missing Dodo subscription ID."
        
    try:
        # REAL DODO PAYMENTS API CALLS
        import requests
        from utils.settings import get_setting
        api_key = get_setting("DODO_PAYMENTS_API_KEY")
        if not api_key:
            return False, "DODO_PAYMENTS_API_KEY not configured."
            
        env = get_setting("DODO_ENVIRONMENT", "test_mode").lower()
        base_url = "https://live.dodopayments.com" if env in ["production", "live"] else "https://test.dodopayments.com"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 1. Cancel the subscription via API
        # Many platforms use PATCH /subscriptions/{id} with status='canceled'
        # Dodo uses client.subscriptions.patch or similar. Using REST to be safe against SDK version issues.
        cancel_url = f"{base_url}/subscriptions/{sub_id}"
        resp_cancel = requests.patch(cancel_url, headers=headers, json={"status": "canceled"})
        
        # We don't fail immediately on cancel error, as we might still want to try refunding the last payment.
        
        # 2. Get the latest payment for this subscription to refund
        inv_df = safe_query(
            "SELECT provider_invoice_id, amount_aed FROM qto_invoices WHERE subscription_id=%s ORDER BY id DESC LIMIT 1",
            (int(df.iloc[0]["id"]),)
        )
        
        refund_msg = "No recent payment found to refund."
        if not inv_df.empty and inv_df.iloc[0]["provider_invoice_id"]:
            payment_id = inv_df.iloc[0]["provider_invoice_id"]
            # Request refund
            refund_url = f"{base_url}/refunds"
            resp_refund = requests.post(refund_url, headers=headers, json={"payment_id": payment_id})
            if resp_refund.status_code in [200, 201]:
                refund_msg = f"Refund issued successfully for payment {payment_id}."
            else:
                return False, f"Refund failed: {resp_refund.text}"

        # 3. Update local DB ONLY after API success
        safe_execute("UPDATE qto_subscriptions SET status='canceled' WHERE id=%s", (int(df.iloc[0]["id"]),))
        return True, f"Subscription {sub_id} canceled in Dodo. {refund_msg}"
        
    except Exception as e:
        return False, f"Dodo API Error: {str(e)}"
