import base64
import hashlib
import hmac
import json
import time

import pytest


def test_verify_dodo_webhook_valid(monkeypatch):
    from utils.payments import verify_dodo_webhook

    # Use a dummy secret (base64 encoded as if whsec_XXX)
    secret_raw = b"my_secret_key"
    secret_b64 = base64.b64encode(secret_raw).decode("utf-8")
    monkeypatch.setenv("DODO_WEBHOOK_SECRET", f"whsec_{secret_b64}")
    
    payload = b'{"event_type":"subscription.activated","data":{}}'
    ts = str(int(time.time()))
    wh_id = "evt_123"
    
    signed_payload = f"{wh_id}.{ts}.{payload.decode('utf-8')}".encode("utf-8")
    digest = base64.b64encode(hmac.new(secret_raw, signed_payload, hashlib.sha256).digest()).decode("utf-8")
    signature = f"v1,{digest}"

    assert verify_dodo_webhook(payload, wh_id, ts, signature) is True


def test_verify_dodo_webhook_rejects_bad_signature(monkeypatch):
    from utils.payments import verify_dodo_webhook

    monkeypatch.setenv("DODO_WEBHOOK_SECRET", "secret")
    payload = b'{"event_type":"subscription.activated","data":{}}'
    ts = str(int(time.time()))
    wh_id = "evt_123"

    assert verify_dodo_webhook(payload, wh_id, ts, "v1,bad") is False


def test_create_checkout_session_uses_dodo_product(monkeypatch):
    import utils.payments as payments
    from unittest.mock import MagicMock

    captured = {}
    
    mock_client = MagicMock()
    mock_session = MagicMock()
    mock_session.checkout_url = "https://checkout.dodo.test/abc"
    
    def fake_create(**kwargs):
        captured.update(kwargs)
        return mock_session
        
    mock_client.checkout_sessions.create = fake_create

    monkeypatch.setenv("DODO_PRODUCT_TIER_2", "pdt_123")
    monkeypatch.setenv("APP_BASE_URL", "https://qto.example")
    monkeypatch.setattr(payments, "_get_dodo_client", lambda: mock_client)
    monkeypatch.setattr(payments, "audit_log", lambda *args, **kwargs: None)

    url = payments.create_checkout_session({"id": 7, "email": "u@example.com"}, 2)

    assert url == "https://checkout.dodo.test/abc"
    assert captured["product_cart"][0]["product_id"] == "pdt_123"
    assert captured["metadata"] == {"user_id": "7", "plan_tier": "2"}


def test_handle_dodo_webhook_routes_subscription(monkeypatch):
    import utils.payments as payments

    called = {}
    event = {
        "event_type": "subscription.activated",
        "data": {"subscription_id": "sub_123", "metadata": {"user_id": "1", "plan_tier": "2"}},
    }
    payload = json.dumps(event).encode()

    monkeypatch.setattr(payments, "verify_dodo_webhook", lambda p, i, t, s: True)
    monkeypatch.setattr(payments, "_upsert_subscription_from_dodo", lambda data: called.setdefault("data", data))

    headers = {"webhook-id": "1", "webhook-timestamp": str(int(time.time())), "webhook-signature": "1"}
    ok, msg = payments.handle_dodo_webhook(payload, headers)

    assert ok is True
    assert msg == "subscription.activated"
    assert called["data"]["subscription_id"] == "sub_123"
