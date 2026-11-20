"""Verification tests for Priority 1 security hardening and Priority 2 review/BOQ wiring fixes."""

import json
import os
import sqlite3
import tempfile
import pandas as pd
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def isolated_app(monkeypatch, tmp_path):
    """Provide a FastAPI TestClient wired to a temporary SQLite database."""
    monkeypatch.setenv("TIDB_HOST", "")
    monkeypatch.setenv("QTO_ADMIN_PASSWORD", "test-admin-secret-pw")
    monkeypatch.delenv("QTO_DEBUG", raising=False)

    db_file = str(tmp_path / "test_qto.db")

    from utils import db as db_mod
    monkeypatch.setattr(db_mod, "_SQLITE_INITIALIZED", False)

    # Point get_connection sqlite path to temp file
    orig_connect = sqlite3.connect

    def _patched_connect(path, *args, **kwargs):
        if str(path).endswith("qto_local.db"):
            return orig_connect(db_file, *args, **kwargs)
        return orig_connect(path, *args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", _patched_connect)

    # Initialize schema cleanly
    with db_mod.get_connection() as conn:
        assert conn is not None

    from api.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, db_mod


def test_logs_endpoint_requires_admin(isolated_app):
    client, db_mod = isolated_app
    from api.auth import generate_session_token

    # Unauthenticated -> 401
    r_anon = client.get("/api/logs")
    assert r_anon.status_code == 401

    # Regular user -> 403
    db_mod.safe_execute(
        "INSERT INTO qto_users (email, password_hash, name, role, token_version) VALUES (%s, %s, %s, %s, %s)",
        ("user@example.com", "hash", "Regular", "user", 0),
    )
    uid = int(db_mod.safe_query("SELECT id FROM qto_users WHERE email=%s", ("user@example.com",)).iloc[0]["id"])
    user_tok = generate_session_token(uid, "user", 0)
    r_user = client.get("/api/logs", headers={"Authorization": f"Bearer {user_tok}"})
    assert r_user.status_code == 403

    # Admin user -> 200
    admin_row = db_mod.safe_query("SELECT id FROM qto_users WHERE role='admin' LIMIT 1")
    admin_id = int(admin_row.iloc[0]["id"])
    admin_tok = generate_session_token(admin_id, "admin", 0)
    r_admin = client.get("/api/logs", headers={"Authorization": f"Bearer {admin_tok}"})
    assert r_admin.status_code == 200


def test_global_exception_handler_hides_traceback_by_default(isolated_app, monkeypatch):
    client, _ = isolated_app
    from api.main import app

    @app.get("/api/_test_boom_p1")
    def _boom():
        raise RuntimeError("sensitive internal trace marker")

    monkeypatch.delenv("QTO_DEBUG", raising=False)
    resp = client.get("/api/_test_boom_p1")
    assert resp.status_code == 500
    body = resp.json()
    assert body == {"detail": "Internal server error."}
    assert "traceback" not in body
    assert "sensitive internal trace marker" not in resp.text


def test_reset_password_bumps_token_version_and_revokes_old_jwt(isolated_app):
    client, db_mod = isolated_app
    from api.auth import generate_session_token, verify_session_token
    from utils.security import password_hash, issue_reset_token, reset_password
    from fastapi import HTTPException

    db_mod.safe_execute(
        "INSERT INTO qto_users (email, password_hash, name, role, token_version) VALUES (%s, %s, %s, %s, %s)",
        ("resetme@example.com", password_hash("oldpass123"), "Reset User", "user", 0),
    )
    uid = int(db_mod.safe_query("SELECT id FROM qto_users WHERE email=%s", ("resetme@example.com",)).iloc[0]["id"])
    old_tok = generate_session_token(uid, "user", 0)
    assert verify_session_token(old_tok)["id"] == uid

    raw_reset = issue_reset_token("resetme@example.com")
    assert raw_reset
    assert reset_password(raw_reset, "newpass456") is True

    with pytest.raises(HTTPException) as exc_info:
        verify_session_token(old_tok)
    assert exc_info.value.status_code == 401
    assert "revoked" in exc_info.value.detail.lower()


def test_reconstruct_idempotent_and_preserves_user_edits():
    from api.routers.data_review import reconstruct_project_inputs

    state_data = {
        "extraction_results": {
            "arch_p1_ground_floor_plan": {
                "_ok": True,
                "drawing_type": "ground_floor_plan",
                "detected_type": "ground_floor_plan",
                "total_floor_area": 200.0,
                "ext_perimeter": 60.0,
                "int_walls_10cm_m": 25.0,
                "int_walls_20cm_m": 45.0,
            },
            "arch_p2_first_floor_plan": {
                "_ok": True,
                "drawing_type": "first_floor_plan",
                "detected_type": "first_floor_plan",
                "total_floor_area": 180.0,
                "ext_perimeter": 56.0,
                "int_walls_10cm_m": 0.0,
                "int_walls_20cm_m": 0.0,
            },
        },
        "_vector_openings": {
            "_ok": True,
            "doors": [{"mark": "D1", "count": 10}],
            "windows": [{"mark": "W1", "width_m": 2.0, "height_m": 1.5, "count": 6}],
            "totals": {"door_count": 10, "window_area": 18.0, "window_count": 6},
        },
        "confirmed_auto_data": {},
    }

    reconstruct_project_inputs(state_data)
    first_10 = state_data["confirmed_auto_data"]["int_walls_10cm_m"]
    first_20 = state_data["confirmed_auto_data"]["int_walls_20cm_m"]
    assert first_10 == 25.0
    # 45.0 from GF + round(180 * 1.5, 2) = 270.0 fallback from 1F -> 315.0 total
    assert first_20 == 315.0
    assert state_data["confirmed_auto_data"]["sources"]["int_walls_20cm_m"] == "Geometric Fallback"
    assert state_data["confirmed_auto_data"]["openings"]["totals"]["door_count"] == 10
    assert state_data["confirmed_auto_data"]["openings"]["totals"]["window_area"] == 18.0

    # Calling reconstruct twice must NOT += double the walls
    reconstruct_project_inputs(state_data)
    assert state_data["confirmed_auto_data"]["int_walls_10cm_m"] == first_10
    assert state_data["confirmed_auto_data"]["int_walls_20cm_m"] == first_20

    # Now simulate user editing openings and running reconstruct again
    c = state_data["confirmed_auto_data"]
    c["openings"]["totals"]["door_count"] = 22
    c["openings"]["totals"]["user_edited_door_count"] = True
    c["openings"]["totals"]["window_area"] = 44.5
    c["openings"]["totals"]["user_edited_window_area"] = True
    c["sources"]["door_count"] = "User Verified"
    c["sources"]["window_area"] = "User Verified"

    reconstruct_project_inputs(state_data)
    assert c["openings"]["totals"]["door_count"] == 22
    assert c["openings"]["user_override_door_count"] == 22
    assert c["openings"]["totals"]["window_area"] == 44.5
    assert c["openings"]["user_override_window_area"] == 44.5


def test_confirm_and_calculate_apply_all_step4_user_overrides(isolated_app):
    client, db_mod = isolated_app
    from api.auth import generate_session_token
    from engine.project_boq_bridge import build_inputs, compute_all_quantities

    db_mod.safe_execute(
        "INSERT INTO qto_users (email, password_hash, name, role, token_version) VALUES (%s, %s, %s, %s, %s)",
        ("qs@example.com", "hash", "QS Engineer", "user", 0),
    )
    uid = int(db_mod.safe_query("SELECT id FROM qto_users WHERE email=%s", ("qs@example.com",)).iloc[0]["id"])
    tok = generate_session_token(uid, "user", 0)
    headers = {"Authorization": f"Bearer {tok}"}

    base_state = {
        "extraction_results": {
            "arch_p1_ground_floor_plan": {
                "_ok": True,
                "drawing_type": "ground_floor_plan",
                "detected_type": "ground_floor_plan",
                "total_floor_area": 220.0,
                "ext_perimeter": 62.0,
                "int_walls_10cm_m": 20.0,
                "int_walls_20cm_m": 40.0,
            },
            "arch_p2_first_floor_plan": {
                "_ok": True,
                "drawing_type": "first_floor_plan",
                "detected_type": "first_floor_plan",
                "total_floor_area": 200.0,
                "ext_perimeter": 58.0,
                "int_walls_10cm_m": 15.0,
                "int_walls_20cm_m": 30.0,
            },
        },
        "confirmed_auto_data": {
            "longest_length": 20.0,
            "longest_width": 12.0,
            "plot_area": 400.0,
            "gf_area": 220.0,
            "ext_perimeter": 62.0,
            "roof_perimeter": 62.0,
            "roof_slab_area": 200.0,
            "compound_length": 80.0,
            "total_villa_height": 8.0,
            "excavation_depth": 1.25,
            "neck_column_height": 1.0,
            "solid_block_height": 1.0,
            "staircase_volume_per_level": 5.2,
            "sog_thickness": 0.10,
            "default_col_length": 0.60,
            "default_col_width": 0.20,
            "int_walls_10cm_m": 35.0,
            "int_walls_20cm_m": 70.0,
            "floors": {
                "gf": {"area": 220.0, "ext_perimeter": 62.0, "wet_area": 20.0, "wet_perimeter": 18.0, "dry_perimeter": 44.0, "balcony_area": 0.0, "height": 4.0},
                "1f": {"area": 200.0, "ext_perimeter": 58.0, "wet_area": 18.0, "wet_perimeter": 16.0, "dry_perimeter": 42.0, "balcony_area": 0.0, "height": 4.0},
            },
            "walls": {
                "gf": {"internal_total_m": 60.0, "internal_10cm_m": 20.0, "internal_20cm_m": 40.0},
                "1f": {"internal_total_m": 45.0, "internal_10cm_m": 15.0, "internal_20cm_m": 30.0},
            },
            "schedules": {
                "foundation": {"footings": [{"type": "F1", "length": 2.0, "width": 2.0, "depth": 0.5, "count": 10}]},
                "column_schedule": {"columns": [{"mark": "C1", "length_m": 0.6, "width_m": 0.2, "count": 10}]},
            },
            "openings": {
                "doors": [{"mark": "D1", "count": 12}],
                "windows": [{"mark": "W1", "width_m": 2.0, "height_m": 1.5, "count": 10}],
                "totals": {"door_count": 12, "window_area": 30.0},
            },
            "sources": {
                "door_count": "AI OCR",
                "window_area": "AI OCR",
                "int_walls_10cm_m": "AI OCR",
                "int_walls_20cm_m": "AI OCR",
            },
        },
    }

    db_mod.safe_execute(
        "INSERT INTO qto_projects (id, user_id, name, boq_data) VALUES (%s, %s, %s, %s)",
        (101, uid, "Override Test Villa", "{}"),
    )
    db_mod.safe_execute(
        "INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data) VALUES (%s, %s, %s, %s)",
        (uid, 101, 4, json.dumps(base_state)),
    )

    # First calculate baseline without overrides
    calc_req = {
        "project_id": 101,
        "num_floors": 2,
        "gf_height": 4.0,
        "f1_height": 4.0,
        "f2_height": 4.0,
        "excavation_depth": 1.25,
        "include_road_base": False,
        "concrete_grade": "C30/37",
        "block_thickness": "200mm",
    }
    res_base = client.post("/api/workflow/calculate", json=calc_req, headers=headers)
    assert res_base.status_code == 200, res_base.text
    items_base = {r.get("#"): r for r in res_base.json()["boq_items"] if not r.get("_is_header")}

    # Now modify all Step 4 fields via /confirm: door_count, window_area, sog_thickness, walls, columns
    edited = json.loads(json.dumps(base_state["confirmed_auto_data"]))
    edited["sog_thickness"] = 0.25  # 2.5x default 0.10
    edited["openings"]["totals"]["door_count"] = 25
    edited["openings"]["totals"]["user_edited_door_count"] = True
    edited["openings"]["totals"]["window_area"] = 75.0
    edited["openings"]["totals"]["user_edited_window_area"] = True
    edited["sources"]["door_count"] = "User Verified"
    edited["sources"]["window_area"] = "User Verified"
    edited["int_walls_10cm_m"] = 90.0
    edited["int_walls_20cm_m"] = 180.0
    edited["sources"]["int_walls_10cm_m"] = "User Verified"
    edited["sources"]["int_walls_20cm_m"] = "User Verified"
    edited["schedules"]["column_schedule"]["columns"] = [
        {"mark": "C1", "type": "C1", "length": 0.8, "length_m": 0.8, "width": 0.4, "width_m": 0.4, "count": 10}
    ]
    edited["schedules"]["superstructure"] = {"columns": edited["schedules"]["column_schedule"]["columns"]}

    res_conf = client.post(
        "/api/workflow/confirm",
        json={"project_id": 101, "confirmed_data": edited},
        headers=headers,
    )
    assert res_conf.status_code == 200, res_conf.text

    res_edit = client.post("/api/workflow/calculate", json=calc_req, headers=headers)
    assert res_edit.status_code == 200, res_edit.text

    def _sum_qty(resp_json, needle: str) -> float:
        return sum(
            float(r.get("Quantity") or 0.0)
            for r in resp_json["boq_items"]
            if not r.get("_is_header") and needle.lower() in str(r.get("Description (English)", "")).lower()
        )

    # Slab on grade must scale 2.5x with sog_thickness (0.10 -> 0.25)
    sog_base = _sum_qty(res_base.json(), "slab on grade concrete")
    sog_edit = _sum_qty(res_edit.json(), "slab on grade concrete")
    assert sog_edit > sog_base * 2.0

    # Internal walls 10cm & 20cm blockwork must increase substantially after user edit
    blk10_base = _sum_qty(res_base.json(), "100mm")
    blk10_edit = _sum_qty(res_edit.json(), "100mm")
    assert blk10_edit > blk10_base * 1.5

    # Columns concrete must increase with larger edited columns (0.6x0.2 -> 0.8x0.4)
    col_base = _sum_qty(res_base.json(), "column concrete (")
    col_edit = _sum_qty(res_edit.json(), "column concrete (")
    assert col_edit > col_base * 1.5

    # Doors and windows must honor user overrides even though schedule arrays exist
    door_base = _sum_qty(res_base.json(), "door openings")
    door_edit = _sum_qty(res_edit.json(), "door openings")
    assert door_edit > door_base

    win_base = _sum_qty(res_base.json(), "window openings")
    win_edit = _sum_qty(res_edit.json(), "window openings")
    assert win_edit > win_base

    # Verify default_col_length / width also apply when schedule is empty
    _, flrs, _ = build_inputs({
        "gf_area": 200.0,
        "default_col_length": 0.90,
        "default_col_width": 0.45,
        "schedules": {},
        "floors": {"gf": {"area": 200.0}},
    })
    assert flrs["gf"]["columns_schedule"][0]["length_m"] == 0.90
    assert flrs["gf"]["columns_schedule"][0]["width_m"] == 0.45


def test_step3_vision_failure_no_fabricated_dimensions():
    from workflow.step3_extract import _vision_failure_fallback

    fb = _vision_failure_fallback("foundation", "429 quota")
    assert fb["_ok"] is False
    assert fb["_fallback"] is True
    assert "429" in fb["_error"]
    for forbidden in ("longest_length", "longest_width", "gf_area", "slab_area", "tb_total_length", "total_floor_area"):
        assert forbidden not in fb


def test_classification_memory_only_records_corrections(monkeypatch):
    from api.routers.classification import _background_record_memory
    recorded = []
    monkeypatch.setattr("engine.qto_memory.record_mapping", lambda uid, clue, cat: recorded.append((uid, clue, cat)) or True)

    _background_record_memory(7, [
        {"detected_type": "ground_floor_plan", "auto_detected_type": "ground_floor_plan", "text_preview": "GROUND FLOOR PLAN"},
        {"detected_type": "roof_slab", "auto_detected_type": "first_floor_plan", "text_preview": "UPPER ROOF SLAB PLAN"},
        {"detected_type": "unknown", "auto_detected_type": "other", "text_preview": "NOTES"},
    ])
    assert recorded == [(7, "UPPER ROOF SLAB PLAN", "roof_slab")]
