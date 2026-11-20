"""Comprehensive tests for security hardening, windows mm->m fix, email verification,
BOQ revisions, background worker extraction, and step3_extract coverage."""
from __future__ import annotations

import json
import sqlite3
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_db_app(monkeypatch, tmp_path):
    """Provide a FastAPI TestClient wired to an isolated temporary SQLite database."""
    monkeypatch.setenv("TIDB_HOST", "")
    monkeypatch.setenv("QTO_ADMIN_PASSWORD", "test-admin-secret-pw")
    monkeypatch.delenv("QTO_DEBUG", raising=False)

    db_file = str(tmp_path / "test_hardening.db")
    from utils import db as db_mod
    monkeypatch.setattr(db_mod, "_SQLITE_INITIALIZED", False)

    orig_connect = sqlite3.connect

    def _patched_connect(path, *args, **kwargs):
        if str(path).endswith("qto_local.db"):
            return orig_connect(db_file, *args, **kwargs)
        return orig_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _patched_connect)
    with db_mod.get_connection() as conn:
        assert conn is not None

    from api.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, db_mod, app


# ── 1. Windows mm -> m auto-normalization (Fixes 3,600,000 m² bug!) ──────────

def test_windows_mm_inputs_convert_to_metres_in_calculator_and_bridge():
    """1500 x 2400 mm window must yield 3.60 m², NOT 3,600,000 m², while preserving area overrides."""
    from engine.item_calculator import calculate_item
    from engine.project_boq_bridge import _windows, build_boq_dataframe_from_project

    area_plain = calculate_item("window_openings", {
        "windows_schedule": [{"width": 1500, "height": 2400, "count": 1}]
    })
    assert area_plain == pytest.approx(3.6, abs=0.01)

    area_mislabelled = calculate_item("window_openings", {
        "windows_schedule": [{"width_m": 1500, "height_m": 2400, "count": 2}]
    })
    assert area_mislabelled == pytest.approx(7.2, abs=0.01)

    area_metres = calculate_item("window_openings", {
        "windows_schedule": [{"width_m": 1.5, "height_m": 2.4, "count": 1}]
    })
    assert area_metres == pytest.approx(3.6, abs=0.01)

    # Explicit total-area override (e.g. 75.0 m²) must NOT be divided by 1000!
    area_override = calculate_item("window_openings", {
        "windows_schedule": [{"width_m": 1.0, "height_m": 75.0, "count": 1, "_is_area_override": True}]
    })
    assert area_override == pytest.approx(75.0, abs=0.01)

    project = {
        "longest_length": 15.0,
        "longest_width": 12.0,
        "plot_area": 400.0,
        "gf_area": 180.0,
        "ext_perimeter": 54.0,
        "roof_perimeter": 54.0,
        "roof_slab_area": 180.0,
        "compound_length": 70.0,
        "total_villa_height": 8.0,
        "structural_levels": 2,
        "gf_height": 4.0,
        "f1_height": 4.0,
        "schedules": {},
        "floors": {"gf": {"area": 180.0, "ext_perimeter": 54.0, "height": 4.0}},
        "walls": {"gf": {"internal_total_m": 40.0}},
        "openings": {
            "windows": [
                {"mark": "W1", "width": 1500, "height": 2400, "count": 4},
                {"mark": "W2", "width_m": 1200, "height_m": 1500, "count": 2},
            ]
        },
    }
    wins = _windows(project)
    assert wins[0]["width_m"] == pytest.approx(1.5, abs=0.001)
    assert wins[0]["height_m"] == pytest.approx(2.4, abs=0.001)
    assert wins[1]["width_m"] == pytest.approx(1.2, abs=0.001)
    assert wins[1]["height_m"] == pytest.approx(1.5, abs=0.001)

    df, _meta = build_boq_dataframe_from_project(project)
    non_hdr = df[~df["_is_header"].fillna(False).astype(bool)]
    win_rows = non_hdr[non_hdr["Description (English)"].str.contains("Window Openings", case=False, na=False)]
    assert not win_rows.empty
    win_qty = float(win_rows.iloc[0]["Quantity"])
    assert win_qty == pytest.approx(4 * 3.6 + 2 * 1.8, abs=0.05)  # 18.0 m², NOT 18,000,000!

    tb_rows = non_hdr[non_hdr["Description (English)"].str.contains(r"Thermal Block External \(GF\)", case=False, na=False)]
    assert not tb_rows.empty
    assert float(tb_rows.iloc[0]["Quantity"]) > 100.0


# ── 2. Security: X-Forwarded-For Anti-Spoofing + No Query-Param Token ────────

def test_rate_client_ip_blocks_xff_spoofing(monkeypatch):
    """Attacker-supplied leftmost X-Forwarded-For must NEVER bypass rate limiting."""
    from api.main import _rate_client_ip

    def _make_req(peer: str, headers: dict):
        return SimpleNamespace(
            client=SimpleNamespace(host=peer),
            headers={k.lower(): v for k, v in headers.items()},
        )

    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("SPACE_ID", raising=False)
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    req_direct = _make_req("203.0.113.50", {"x-forwarded-for": "1.1.1.1, 2.2.2.2"})
    assert _rate_client_ip(req_direct) == "203.0.113.50"

    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "1")
    req_spoofed = _make_req("10.0.0.5", {"x-forwarded-for": "9.9.9.9, 198.51.100.77"})
    assert _rate_client_ip(req_spoofed) == "198.51.100.77"

    req_spoofed_2 = _make_req("10.0.0.5", {"x-forwarded-for": "8.8.8.8, 198.51.100.77"})
    assert _rate_client_ip(req_spoofed_2) == "198.51.100.77"


def test_query_param_tokens_rejected_on_api_and_cache(isolated_db_app):
    """JWT tokens in ?Authorization= or ?token= query strings must be rejected (401)."""
    client, _db_mod, _app = isolated_db_app
    from api.auth import generate_session_token

    tok = generate_session_token(1, "admin", 0)
    r_api = client.get(f"/api/auth/profile?Authorization=Bearer%20{tok}")
    assert r_api.status_code == 401

    r_cache = client.get(f"/cache/999/test.png?token={tok}")
    assert r_cache.status_code == 401


# ── 3. Email Verification Lifecycle (New Accounts Only; Existing Unaffected) ─

def test_email_verification_new_account_and_existing_account_compatibility(isolated_db_app):
    """New accounts require 6-digit email verification; pre-existing accounts log in directly."""
    client, db_mod, _app = isolated_db_app
    from utils.security import password_hash

    # Pre-existing legacy user (email_verified=0, verification_token_hash=NULL) MUST STILL LOG IN!
    db_mod.safe_execute(
        "INSERT INTO qto_users (email, password_hash, role, email_verified, verification_token_hash) VALUES (%s, %s, 'user', 0, NULL)",
        ("legacy@example.com", password_hash("secret123")),
    )

    captured_codes: list[str] = []

    def _fake_send_verif(to_email: str, code: str, name=None) -> bool:
        captured_codes.append(code)
        return True

    with patch("utils.mailer.send_verification_email", side_effect=_fake_send_verif):
        # Legacy user logs in seamlessly
        r_leg = client.post("/api/auth/login", json={"email": "legacy@example.com", "password": "secret123"})
        assert r_leg.status_code == 200
        assert "token" in r_leg.json()

        # New user registers -> receives 6-digit code & requires_verification=True
        r_reg = client.post("/api/auth/register", json={
            "email": "newqs@example.com",
            "password": "password123",
            "name": "Eng. New",
        })
        assert r_reg.status_code == 200
        assert r_reg.json().get("requires_verification") is True
        assert len(captured_codes) == 1
        code = captured_codes[0]
        assert len(code) == 6 and code.isdigit()

        # Unverified new user CANNOT log in yet -> 403 EMAIL_NOT_VERIFIED
        r_blk = client.post("/api/auth/login", json={"email": "newqs@example.com", "password": "password123"})
        assert r_blk.status_code == 403
        assert "EMAIL_NOT_VERIFIED" in r_blk.json()["detail"]

        # Wrong code is rejected
        r_bad = client.post("/api/auth/verify-email", json={"email": "newqs@example.com", "code": "000000"})
        assert r_bad.status_code == 400

        # Correct 6-digit code verifies & logs in immediately!
        r_ok = client.post("/api/auth/verify-email", json={"email": "newqs@example.com", "code": code})
        assert r_ok.status_code == 200, r_ok.text
        assert "token" in r_ok.json()

        # Subsequent normal login succeeds
        r_in = client.post("/api/auth/login", json={"email": "newqs@example.com", "password": "password123"})
        assert r_in.status_code == 200


# ── 4. BOQ Versioning (Rev 0 -> Rev 1 -> Restore -> Rev 2) ───────────────────

def test_boq_revisions_save_list_and_restore(isolated_db_app):
    """BOQ calculations & reviews create Rev 0 / Rev 1 and restoring creates Rev 2."""
    client, db_mod, app = isolated_db_app
    from api.auth import get_current_user

    init_state = {
        "project_id": 42,
        "project_name": "Villa Rev Test",
        "confirmed_auto_data": {
            "longest_length": 15.0,
            "longest_width": 12.0,
            "plot_area": 400.0,
            "gf_area": 180.0,
            "ext_perimeter": 54.0,
            "roof_perimeter": 54.0,
            "roof_slab_area": 180.0,
            "compound_length": 60.0,
            "total_villa_height": 8.0,
            "schedules": {},
            "floors": {},
            "walls": {},
            "openings": {},
        },
    }
    db_mod.safe_execute(
        "INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data) VALUES (1, 42, 5, %s)",
        (json.dumps(init_state),),
    )

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "qs@example.com", "role": "user"}
    try:
        r1 = client.post("/api/workflow/calculate", json={"project_id": 42, "num_floors": 2})
        assert r1.status_code == 200, r1.text
        assert r1.json()["rev_no"] == 0
        rev0_items = r1.json()["boq_items"]

        edited_items = [
            {"#": "1.1", "Description (English)": "Excavation", "Unit": "m³", "Quantity": 500.0, "Unit Price": 25.0, "Total": 12500.0}
        ]
        r2 = client.post("/api/workflow/review/save", json={"project_id": 42, "boq_items": edited_items})
        assert r2.status_code == 200
        assert r2.json()["rev_no"] == 1

        r_list = client.get("/api/workflow/boq/revisions?project_id=42")
        assert r_list.status_code == 200
        revs = r_list.json()
        assert len(revs) == 2
        assert revs[0]["rev_no"] == 1
        assert revs[1]["rev_no"] == 0
        rev0_id = revs[1]["id"]

        r_rest = client.post(f"/api/workflow/boq/revisions/{rev0_id}/restore?project_id=42")
        assert r_rest.status_code == 200
        assert r_rest.json()["rev_no"] == 2
        assert len(r_rest.json()["boq_items"]) == len(rev0_items)
    finally:
        app.dependency_overrides.clear()


# ── 5. Non-Blocking Background Extraction Worker (worker.py + /extract/start) ─

def test_background_extraction_worker_non_blocking_polling(isolated_db_app):
    """POST /extract/start queues in qto_background_jobs, runs in worker.py, and completes via polling."""
    client, db_mod, app = isolated_db_app
    from api.auth import get_current_user

    state = {
        "project_id": 77,
        "project_name": "Async Villa",
        "classified_pages": [
            {"pdf": "architectural", "page_index": 0, "page_num": 1, "detected_type": "ground_floor_plan"}
        ],
    }
    db_mod.safe_execute(
        "INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data) VALUES (1, 77, 3, %s)",
        (json.dumps(state),),
    )

    def _fake_exec(project_id: int, user_id: int, progress_cb=None):
        if progress_cb:
            progress_cb(45, "Extracting AI Data (1/1)...")
        time.sleep(0.05)
        if progress_cb:
            progress_cb(99, "Saving extraction results...")
        return {
            "done": True,
            "extraction_results": {"arch_p1_ground_floor_plan": {"_ok": True, "total_floor_area": 210.0}},
            "confirmed_auto_data": {"gf_area": 210.0, "longest_length": 15.0, "longest_width": 14.0},
            "sanity_warnings": [],
            "next_step": 4,
        }

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "email": "qs@example.com", "role": "user"}
    try:
        with patch("api.routers.extraction.execute_project_extraction", side_effect=_fake_exec):
            t0 = time.time()
            r_start = client.post("/api/workflow/extract/start", json={"project_id": 77})
            elapsed = time.time() - t0
            assert r_start.status_code == 200, r_start.text
            assert elapsed < 2.0
            job_id = r_start.json()["job_id"]
            assert isinstance(job_id, int)

            final_info = None
            for _ in range(40):
                r_st = client.get(f"/api/workflow/extract/status/{job_id}")
                assert r_st.status_code == 200
                info = r_st.json()
                if info["status"] == "done":
                    final_info = info
                    break
                time.sleep(0.05)

            assert final_info is not None
            assert final_info["progress"] == 100
            assert final_info["result"]["done"] is True
            assert final_info["result"]["confirmed_auto_data"]["gf_area"] == 210.0
    finally:
        app.dependency_overrides.clear()


# ── 6. step3_extract.py Unit & End-to-End Extraction Coverage Boost ──────────

def test_step3_extract_unit_normalizers_and_room_finishes():
    """Verify unit coercion (m/cm/mm/mis-divided), JSON parser, and room-based finishes geometry."""
    from workflow.step3_extract import (
        _to_m,
        _to_section_m,
        _to_slab_thk_m,
        _to_footing_plan_m,
        _to_footing_depth_m,
        _finishes_from_rooms,
        _normalize_units,
        parse_json,
    )

    assert _to_m(1500, 25) == 1.5
    assert _to_m(2.4, 25) == 2.4
    assert _to_m("bad", 25) == "bad"

    assert _to_section_m(0.20) == 0.20
    assert _to_section_m(20) == 0.20
    assert _to_section_m(600) == 0.60
    assert _to_section_m(0.02) == 0.20

    assert _to_slab_thk_m(0.22) == 0.22
    assert _to_slab_thk_m(24) == 0.24
    assert _to_slab_thk_m(250) == 0.25
    assert _to_slab_thk_m(0.024) == 0.24

    assert _to_footing_plan_m(1.8) == 1.8
    assert _to_footing_plan_m(200) == 2.0
    assert _to_footing_plan_m(1600) == 1.6
    assert _to_footing_plan_m(0.20) == 2.0
    assert _to_footing_depth_m(0.50) == 0.5
    assert _to_footing_depth_m(45) == 0.45
    assert _to_footing_depth_m(500) == 0.5
    assert _to_footing_depth_m(0.04) == 0.4

    assert parse_json('```json\n{"gf_area": 220}\n```') == {"gf_area": 220}
    assert parse_json('Here is the JSON: {"a": 1, "b": [2]} done.') == {"a": 1, "b": [2]}
    assert parse_json("") == {}

    raw = {
        "tb_width": 250,
        "tb_depth": 60,
        "slab_thickness": 220,
        "longest_length": 15000,
        "longest_width": 12000,
        "footings": [{"mark": "F1", "width": 1500, "length": 1800, "depth": 500, "count": 6}],
        "beams": [{"mark": "B1", "width": 200, "depth": 600, "length": 8000}],
        "columns": [{"mark": "C1", "width_m": 20, "length_m": 60}],
        "windows": [
            {"mark": "W1", "width_mm": 1500, "height_mm": 2400, "count": 3},
            {"mark": "W2", "width_m": 1800, "height_m": 2100, "count": 2},
        ],
    }
    norm = _normalize_units(raw)
    assert norm["tb_width"] == 0.25
    assert norm["tb_depth"] == 0.60
    assert norm["slab_thickness"] == 0.22
    assert norm["longest_length"] == 15.0
    assert norm["longest_width"] == 12.0
    assert norm["footings"][0]["width"] == 1.5
    assert norm["footings"][0]["depth"] == 0.5
    assert norm["columns"][0]["width_m"] == 0.2
    assert norm["columns"][0]["length_m"] == 0.6
    assert norm["windows"][0]["width_m"] == 1.5
    assert norm["windows"][0]["height_m"] == 2.4
    assert norm["windows"][1]["width_m"] == 1.8
    assert norm["windows"][1]["height_m"] == 2.1

    plan_data = {
        "overall_length_m": 12.0,
        "overall_width_m": 10.0,
        "floor_height_m": 3800,
        "rooms": [
            {"name": "Majlis", "length_m": 6.0, "width_m": 5.0, "doors_count": 2, "windows_count": 2},
            {"name": "Kitchen", "length_m": 4.0, "width_m": 3.0, "doors_count": 1, "windows_count": 1},
            {"name": "حمام رئيسي", "length_m": 3.0, "width_m": 2.0, "doors_count": 1, "windows_count": 1},
            {"name": "Master Bedroom", "length_m": 5000, "width_m": 4000, "doors_count": 1, "windows_count": 2},
        ],
    }
    fin = _finishes_from_rooms(plan_data)
    assert fin["wet_area"] == pytest.approx(18.0, abs=0.01)
    assert fin["wet_perimeter"] == pytest.approx(24.0, abs=0.01)
    assert fin["dry_perimeter"] == pytest.approx(40.0, abs=0.01)
    assert fin["ext_perimeter"] == pytest.approx(44.0, abs=0.01)
    assert fin["floor_height"] == pytest.approx(3.8, abs=0.01)
    assert fin["total_windows_area"] == pytest.approx(12.0, abs=0.01)
    assert fin["total_doors_count"] >= 2


def test_step3_extract_page_foundations_and_schedules(monkeypatch, tmp_path):
    """Exercise extract_page end-to-end for foundations, schedules, and tie_beam with mocked Vision calls."""
    from PIL import Image
    import google.genai as _genai
    import workflow.step3_extract as s3

    monkeypatch.setenv("TIDB_HOST", "")
    img_file = tmp_path / "page.png"
    Image.new("RGB", (200, 200), color="white").save(img_file)

    # 1. Foundations dual-call async path
    fnd_dims = json.dumps({"longest_length": 16000, "longest_width": 12000, "confidence": "high"})
    fnd_sched = json.dumps({
        "footings": [{"mark": "F1", "width": 1500, "length": 1800, "depth": 500, "count": 8}],
        "confidence": "high",
    })
    with patch.object(s3, "_ask_ai_with_retry", new=AsyncMock(side_effect=[fnd_dims, fnd_sched])):
        res_fnd = s3.extract_page(
            None,
            "foundations",
            "FOUNDATION SCHEDULE F1 1500x1800x500",
            user_id=1,
            image_path=str(img_file),
            force_reextract=True,
        )
        assert res_fnd.get("_ok") is True
        assert res_fnd["longest_length"] == pytest.approx(16.0, abs=0.01)
        assert res_fnd["longest_width"] == pytest.approx(12.0, abs=0.01)
        assert res_fnd["footings"][0]["width"] == pytest.approx(1.5, abs=0.01)
        assert res_fnd["footings"][0]["depth"] == pytest.approx(0.5, abs=0.01)

    # 2. Synchronous Vision path: window_schedule
    sched_text = json.dumps({
        "windows": [{"mark": "W1", "width_mm": 1500, "height_mm": 2400, "count": 4}],
        "doors": [{"mark": "D1", "width_mm": 1000, "height_mm": 2200, "count": 6}],
        "confidence": "high",
        "notes": "schedule ok",
    })

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.models = SimpleNamespace(
                generate_content=lambda **kw: SimpleNamespace(text=sched_text)
            )

    class _FakeMgr:
        def get_key_and_model(self):
            return ("fake-test-key", "gemini-2.5-flash")
        def key_count(self):
            return 1
        def mark_rate_limited(self, *a, **kw):
            pass

    with patch.object(_genai, "Client", _FakeClient), \
         patch("utils.key_manager.get_key_manager", return_value=_FakeMgr()):
        res_sch = s3.extract_page(
            None,
            "window_schedule",
            "WINDOW SCHEDULE W1 1500x2400",
            user_id=1,
            image_path=str(img_file),
            force_reextract=True,
        )
        assert res_sch.get("_ok") is True
        assert res_sch["windows"][0]["width_m"] == pytest.approx(1.5, abs=0.01)
        assert res_sch["windows"][0]["height_m"] == pytest.approx(2.4, abs=0.01)
        assert res_sch["doors"][0]["width_m"] == pytest.approx(1.0, abs=0.01)

    # 3. Tie beam async dual-call path
    tb_json = json.dumps({
        "tb_width": 250,
        "tb_depth": 600,
        "tb_total_length": 95000,
        "ext_perimeter": 54,
        "gf_area": 180,
        "confidence": "high",
    })
    with patch.object(s3, "_ask_ai_with_retry", new=AsyncMock(return_value=tb_json)):
        res_tb = s3.extract_page(
            None,
            "tie_beam",
            "TIE BEAM PLAN TB1 250x600",
            user_id=1,
            image_path=str(img_file),
            force_reextract=True,
        )
        assert res_tb.get("_ok") is True
        assert res_tb["tb_width"] == pytest.approx(0.25, abs=0.01)
        assert res_tb["tb_depth"] == pytest.approx(0.60, abs=0.01)
        assert res_tb["tb_total_length"] == pytest.approx(95.0, abs=0.1)
