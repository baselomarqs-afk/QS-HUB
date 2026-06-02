import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import pandas as pd

from api.main import app
from api.auth import get_current_user


@pytest.fixture
def client():
    # Setup test client with dependency overrides
    mock_user = {"id": 1, "email": "test@example.com", "role": "user", "plan_tier": 2}
    app.dependency_overrides[get_current_user] = lambda: mock_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert "fully operational" in response.json()["message"]


def test_cors_headers(client):
    # Check that CORS headers are present on preflight or standard requests
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Requested-With",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_calculate_endpoint(client, monkeypatch):
    # Mock database queries for calculation state
    mock_state_data = {
        "project_id": 1,
        "project_name": "Test Villa",
        "confirmed_auto_data": {
            "longest_length": 15.0,
            "longest_width": 12.0,
            "plot_area": 300.0,
            "gf_area": 150.0,
            "ext_perimeter": 54.0,
            "roof_perimeter": 54.0,
            "roof_slab_area": 150.0,
            "compound_length": 60.0,
            "total_villa_height": 8.0,
            "excavation_depth": 1.25,
            "schedules": {},
            "floors": {},
            "walls": {},
            "openings": {}
        }
    }
    
    # Mock database query
    mock_df = pd.DataFrame([{"state_data": json.dumps(mock_state_data)}])
    monkeypatch.setattr("api.workflow.safe_query", lambda sql, params=None: mock_df)
    monkeypatch.setattr("api.workflow.safe_execute", lambda sql, params=None: (1, None))
    
    # Run calculation request
    payload = {
        "project_id": 1,
        "num_floors": 2,
        "gf_height": 4.0,
        "f1_height": 4.0,
        "f2_height": 4.0,
        "excavation_depth": 1.25,
        "include_road_base": True,
        "concrete_grade": "C35/45",
        "block_thickness": "250mm"
    }
    
    response = client.post("/api/workflow/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "boq_items" in data
    assert "boq_meta" in data
    
    # Verify concrete grade and block thickness details were appended
    boq_items = data["boq_items"]
    # Check structural concrete description contains the custom grade
    found_grade = False
    for item in boq_items:
        desc = item.get("Description (English)", "")
        if "Foundation Concrete" in desc and "Grade C35/45" in desc:
            found_grade = True
            break
    assert found_grade is True


def test_export_blocked_by_critical_validation(client, monkeypatch):
    # Mock state data with missing/zero critical fields (e.g. longest_length is 0)
    mock_state_data = {
        "project_id": 1,
        "project_name": "Invalid Villa",
        "confirmed_auto_data": {
            "longest_length": 0.0,  # Zero
            "longest_width": 12.0,
            "plot_area": 300.0,
            "gf_area": 150.0,
            "ext_perimeter": 54.0,
        },
        "boq_items": [{"#": "D.3", "Description (English)": "Concrete", "Quantity": 10.0}]
    }
    mock_df = pd.DataFrame([{"name": "Invalid Villa", "boq_data": "{}", "state_data": json.dumps(mock_state_data)}])
    monkeypatch.setattr("api.workflow.safe_query", lambda sql, params=None: mock_df)
    
    # Request excel export, should be blocked by validation with 400 Bad Request
    response = client.get("/api/workflow/export/excel?project_id=1")
    assert response.status_code == 400
    assert "Export blocked: Critical parameters" in response.json()["detail"]


def test_export_excel_success(client, monkeypatch):
    # Mock state data with valid parameters
    mock_state_data = {
        "project_id": 1,
        "project_name": "Valid Villa",
        "concrete_grade": "C30/37",
        "block_thickness": "200mm",
        "confirmed_auto_data": {
            "longest_length": 15.0,
            "longest_width": 12.0,
            "plot_area": 300.0,
            "gf_area": 150.0,
            "ext_perimeter": 54.0,
        },
        "boq_items": [
            {"#": "D.3", "Description (English)": "Foundation Concrete (Grade C30/37)", "البيان": "خرسانة", "Unit": "m³", "Quantity": 15.0, "Unit Price": 350.0, "Total": 5250.0},
            {"#": "E.2.1", "Description (English)": "Thermal Block External (GF) (200mm Thickness)", "البيان": "طابوق", "Unit": "m²", "Quantity": 120.0, "Unit Price": 42.5, "Total": 5100.0}
        ],
        "boq_meta": {"needs_input": [], "estimates": []}
    }
    mock_df = pd.DataFrame([{"name": "Valid Villa", "boq_data": "{}", "state_data": json.dumps(mock_state_data)}])
    monkeypatch.setattr("api.workflow.safe_query", lambda sql, params=None: mock_df)
    
    # Request excel export, should succeed
    response = client.get("/api/workflow/export/excel?project_id=1")
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers.get("content-disposition")
    # Verify we got non-empty excel bytes back
    assert len(response.content) > 1000


def test_rate_limiting_middleware(monkeypatch):
    # Set rate limit directly in main module to bypass import-time configuration
    import api.main
    monkeypatch.setattr(api.main, "_RATE_LIMIT", 2)
    api.main._rate_hits.clear()
    
    with TestClient(app) as client:
        # Request 1: OK
        res1 = client.get("/api/health")
        assert res1.status_code == 200
        
        # Request 2: OK (health endpoint is ignored by design in middleware, but let's test a rate-limited path)
        # Let's request a non-existing endpoint under /api/ to trigger rate limiting (returns 404 or 401)
        res2 = client.get("/api/non-existing-path")
        assert res2.status_code in (404, 401)  # returns auth required or not found, but it consumes a rate-limit token
        
        res3 = client.get("/api/non-existing-path")
        assert res3.status_code in (404, 401)
        
        # Request 4: Rate limited!
        res4 = client.get("/api/non-existing-path")
        assert res4.status_code == 429
        assert "Too many requests" in res4.json()["detail"]


def test_dodo_webhook_endpoint(client, monkeypatch):
    # Mock verify_dodo_webhook to return True for our test
    monkeypatch.setattr("utils.payments.verify_dodo_webhook", lambda p, i, t, s: True)
    # Mock handle_dodo_webhook
    monkeypatch.setattr("utils.payments.handle_dodo_webhook", lambda p, h: (True, "mocked_event"))
    
    response = client.post(
        "/webhooks/dodopayments",
        json={"event_type": "subscription.activated"},
        headers={
            "webhook-id": "evt_123",
            "webhook-timestamp": "12345678",
            "webhook-signature": "sig"
        }
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "mocked_event"}

