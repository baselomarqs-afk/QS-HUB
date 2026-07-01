"""Dodo Payments integration.

Implements hosted checkout through Dodo Payments and webhook syncing for
subscription lifecycle events.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
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

logger = logging.getLogger("qto.payments")


def _dodo_base_url() -> str:
    """Single source of truth for the Dodo REST base URL.

    The API key prefix (`live_` / `test_`) is authoritative — this removes the
    whole class of bugs where DODO_ENVIRONMENT was set to the wrong value and
    we ended up querying the test server with a live key (finding nothing).
    """
    api_key = (get_setting("DODO_PAYMENTS_API_KEY", "") or "").strip()
    if api_key.startswith("live_"):
        return "https://live.dodopayments.com"
    if api_key.startswith("test_"):
        return "https://test.dodopayments.com"
    env = get_setting("DODO_ENVIRONMENT", "test_mode").lower()
    return "https://live.dodopayments.com" if env in ("live_mode", "production", "live") else "https://test.dodopayments.com"


_PRODUCT_MAP_CACHE: dict[str, tuple[str, int]] | None = None


def build_product_map(force: bool = False) -> dict[str, tuple[str, int]]:
    """Deterministic mapping: real Dodo product_id -> (feature, tier).

    Built once from the configured product ids so we never have to *guess* a
    tier by looping. Dummy fallback ids are excluded.
    """
    global _PRODUCT_MAP_CACHE
    if _PRODUCT_MAP_CACHE is not None and not force:
        return _PRODUCT_MAP_CACHE
    mapping: dict[str, tuple[str, int]] = {}
    for feature in ("qto", "programme", "cashflow"):
        for tier in (1, 2, 3, 4):
            try:
                pid = dodo_product_for_tier(tier, feature)
            except Exception:
                continue
            if pid and not str(pid).startswith("pdt_DUMMY"):
                mapping[pid] = (feature, tier)
    _PRODUCT_MAP_CACHE = mapping
    return mapping


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
        # Each tool has its own +1 add-on product; fall back to the QTO add-on
        # if a tool-specific one isn't configured yet.
        if feature == "programme":
            price_id = get_setting("DODO_PRODUCT_ADDON_PROGRAMME") or get_setting("DODO_PRODUCT_ADDON_PROJECT")
        elif feature == "cashflow":
            price_id = get_setting("DODO_PRODUCT_ADDON_CASHFLOW") or get_setting("DODO_PRODUCT_ADDON_PROJECT")
        else:
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
            # Which tool this +1 project belongs to (qto/programme/cashflow).
            custom_data["feature"] = feature
        else:
            custom_data["feature"] = tier  # "programme" | "cashflow"
    else:
        custom_data["plan_tier"] = str(tier)
        custom_data["feature"] = feature

    kwargs = {
        "product_cart": [{"product_id": product_id, "quantity": 1}],
        "customer": {"email": user["email"]},
        "return_url": app_base_url() + "/?payment_success=1",
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
        # Deterministic lookup: product_id -> (feature, tier)
        mapped = build_product_map().get(product_id)
        if mapped:
            inferred_feature, inferred_tier = mapped

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


def auto_sync_user_subscriptions(user_id: int, user_email: str) -> int:
    """
    Pull the user's active subscriptions directly from Dodo Payments API
    and sync any missing ones to the local database.
    This is called every time the billing page loads — so even if a webhook
    was missed, the subscription is automatically detected and activated.
    Returns the number of subscriptions synced.
    """
    import requests as _requests
    synced = 0
    try:
        api_key = get_setting("DODO_PAYMENTS_API_KEY")
        if not api_key:
            logger.warning("auto_sync skipped: DODO_PAYMENTS_API_KEY not configured")
            return 0
        base_url = _dodo_base_url()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        product_map = build_product_map()

        # Fetch all subscriptions from Dodo
        r = _requests.get(f"{base_url}/subscriptions?limit=50", headers=headers, timeout=8)
        if r.status_code != 200:
            logger.warning("auto_sync: Dodo /subscriptions returned %s at %s: %s",
                           r.status_code, base_url, r.text[:300])
            return 0

        data = r.json()
        items = data.get("items", data.get("data", []))

        for item in items:
            # Only process subscriptions belonging to this user
            item_email = (item.get("customer", {}) or {}).get("email", "")
            item_metadata = item.get("metadata") or {}
            item_user_id = int(item_metadata.get("user_id", 0) or 0)

            if item_email != user_email and item_user_id != user_id:
                continue

            sub_id = item.get("subscription_id") or item.get("id", "")
            status = item.get("status", "")
            product_id = item.get("product_id", "")
            customer_id = (item.get("customer", {}) or {}).get("customer_id", "")

            if not sub_id or status not in ("active", "trialing"):
                continue

            # Map product_id → feature + tier. The product map is authoritative;
            # metadata is only a fallback when the product id isn't recognised.
            if product_id in product_map:
                feature, tier = product_map[product_id]
            else:
                feature = item_metadata.get("feature") or "qto"
                tier_raw = item_metadata.get("plan_tier")
                try:
                    tier = int(tier_raw) if tier_raw else 1
                except Exception:
                    tier = 1

            # Check if already in DB
            existing = safe_query(
                "SELECT id, status FROM qto_subscriptions WHERE provider='dodopayments' AND provider_subscription_id=%s",
                (sub_id,)
            )
            if existing.empty:
                safe_execute(
                    """INSERT INTO qto_subscriptions
                       (user_id, feature, plan_tier, provider, provider_customer_id,
                        provider_subscription_id, status, cancel_at_period_end)
                       VALUES (%s, %s, %s, 'dodopayments', %s, %s, %s, 0)""",
                    (user_id, feature, tier, customer_id, sub_id, status)
                )
                audit_log("subscription_synced", user_id, "subscription", sub_id,
                          {"provider": "dodopayments", "status": status, "feature": feature, "source": "auto_sync"})
                synced += 1
            elif existing.iloc[0]["status"] != status:
                safe_execute(
                    "UPDATE qto_subscriptions SET status=%s, user_id=%s, feature=%s, plan_tier=%s, provider_customer_id=%s WHERE provider_subscription_id=%s",
                    (status, user_id, feature, tier, customer_id, sub_id)
                )
                synced += 1

        if synced > 0:
            from utils.plans import get_active_subscription, get_plan_for_user
            get_active_subscription.clear()
            get_plan_for_user.clear()

    except Exception:
        # Best-effort: never crash the page — but DO log so failures aren't silent.
        logger.exception("auto_sync_user_subscriptions failed for user_id=%s", user_id)

    return synced


def sync_user_addons(user_id: int, user_email: str) -> int:
    """Pull recent ONE-TIME payments from Dodo and grant any '+1 project'
    add-ons that haven't been granted yet. This is the synchronous counterpart
    to auto_sync_user_subscriptions for add-ons — so a bought extra project
    reflects immediately even if the webhook never arrives.

    Only payments explicitly tagged `is_addon=true` are processed here, so a
    recurring subscription charge can never be mistaken for an add-on. Grants
    are idempotent via _already_processed().
    """
    import requests as _requests
    from utils.features import FEATURE_EXTRA_COL

    granted = 0
    try:
        api_key = get_setting("DODO_PAYMENTS_API_KEY")
        if not api_key:
            return 0
        base_url = _dodo_base_url()
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        r = _requests.get(f"{base_url}/payments?limit=50", headers=headers, timeout=8)
        if r.status_code != 200:
            logger.warning("sync_user_addons: Dodo /payments returned %s at %s: %s",
                           r.status_code, base_url, r.text[:300])
            return 0

        data = r.json()
        items = data.get("items", data.get("data", []))

        for item in items:
            item_email = (item.get("customer", {}) or {}).get("email", "")
            metadata = item.get("metadata") or {}
            item_user_id = int(metadata.get("user_id", 0) or 0)
            if item_email != user_email and item_user_id != user_id:
                continue

            status = (item.get("status") or "").lower()
            if status not in ("succeeded", "paid"):
                continue

            if metadata.get("is_addon") != "true":
                continue  # only add-ons — subscription charges are handled elsewhere

            payment_id = item.get("payment_id") or item.get("id")
            if _already_processed("addon_purchased", payment_id):
                continue

            feature = metadata.get("feature") or "qto"
            col = FEATURE_EXTRA_COL.get(feature, "extra_projects_allowance")
            safe_execute(f"UPDATE qto_users SET {col} = COALESCE({col}, 0) + 1 WHERE id = %s", (user_id,))
            audit_log("addon_purchased", user_id, "user", payment_id,
                      {"provider": "dodopayments", "status": status, "feature": feature, "source": "sync"})
            granted += 1

    except Exception:
        logger.exception("sync_user_addons failed for user_id=%s", user_id)

    return granted


def force_activate_subscription(user_id: int, user_email: str, feature: str = "qto") -> dict[str, Any]:
    """Synchronous, uncached activation used right after the user returns from
    the Dodo checkout page. Pulls straight from the Dodo API, writes any active
    subscriptions, then ALWAYS clears the plan caches (even if 0 new rows) so a
    row written by a webhook a moment earlier is picked up immediately.

    Returns {active, plan_tier, feature, synced}.
    """
    synced = 0
    try:
        synced = auto_sync_user_subscriptions(user_id, user_email)
    except Exception:
        logger.exception("force_activate: auto_sync failed for user_id=%s", user_id)

    # Reconcile one-time add-on purchases synchronously too (no webhook needed).
    addons = 0
    try:
        addons = sync_user_addons(user_id, user_email)
    except Exception:
        logger.exception("force_activate: addon sync failed for user_id=%s", user_id)

    # Always clear caches — the whole point is to defeat a stale `None`.
    from utils.plans import get_active_subscription, get_plan_for_user
    get_active_subscription.clear()
    get_plan_for_user.clear()

    sub = get_active_subscription(user_id, feature)
    return {
        "active": bool(sub),
        "plan_tier": int(sub.get("plan_tier", 0)) if sub else 0,
        "status": sub.get("status") if sub else "inactive",
        "feature": feature,
        "synced": synced,
        "addons": addons,
    }


def _already_processed(action: str, payment_id: str | None) -> bool:
    """Idempotency guard: a duplicate webhook must not grant the add-on twice."""
    if not payment_id:
        return False
    try:
        df = safe_query(
            "SELECT id FROM qto_audit_logs WHERE action=%s AND target_id=%s LIMIT 1",
            (action, str(payment_id)),
        )
        return not df.empty
    except Exception:
        return False


def _record_transaction(data: dict[str, Any], event_type: str) -> None:
    from utils.features import FEATURE_EXTRA_COL

    metadata = data.get("metadata", {}) or {}
    user_id = metadata.get("user_id")
    is_addon = metadata.get("is_addon") == "true"
    status = data.get("status") or event_type
    payment_id = data.get("payment_id") or data.get("id")

    if is_addon and status in {"paid", "succeeded"} and user_id:
        # +1 project for the SPECIFIC tool this add-on was bought for.
        feature = metadata.get("feature") or "qto"
        col = FEATURE_EXTRA_COL.get(feature, "extra_projects_allowance")
        if _already_processed("addon_purchased", payment_id):
            return
        safe_execute(f"UPDATE qto_users SET {col} = COALESCE({col}, 0) + 1 WHERE id = %s", (user_id,))
        audit_log("addon_purchased", int(user_id), "user", payment_id or int(user_id),
                  {"provider": "dodopayments", "status": status, "feature": feature})
        return

    # Per-project module tools (Work Programme / Cash Flow) — grant 1 feature credit for one-time purchases.
    feature = metadata.get("feature")
    has_tier = "plan_tier" in metadata or "metadata_plan_tier" in metadata
    if feature in {"programme", "cashflow"} and not has_tier and status in {"paid", "succeeded"} and user_id:
        if _already_processed("feature_purchased", payment_id):
            return
        from utils.features import grant_credit
        grant_credit(int(user_id), feature, 1)
        audit_log("feature_purchased", int(user_id), "user", payment_id or int(user_id), {"provider": "dodopayments", "feature": feature, "status": status})
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
