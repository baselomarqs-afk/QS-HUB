import os
import json
import io
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth import get_current_user
from utils.db import safe_query, safe_execute
from engine.project_boq_bridge import build_boq_dataframe_from_project, compute_all_quantities
from utils.exporter import export_boq_to_excel
from utils.boq_pdf_generator import create_boq_pdf
from api.routers.data_review import reconstruct_project_inputs

router = APIRouter()


def _ensure_boq_revisions_table() -> None:
    """Ensure qto_boq_revisions exists on both SQLite and MySQL."""
    try:
        from utils.db import is_sqlite
        if is_sqlite():
            safe_execute(
                """
                CREATE TABLE IF NOT EXISTS qto_boq_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    rev_no INTEGER NOT NULL DEFAULT 0,
                    label TEXT DEFAULT 'Calculation',
                    item_count INTEGER DEFAULT 0,
                    grand_total REAL DEFAULT 0,
                    boq_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        else:
            safe_execute(
                """
                CREATE TABLE IF NOT EXISTS qto_boq_revisions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    user_id INT NOT NULL,
                    rev_no INT NOT NULL DEFAULT 0,
                    label VARCHAR(160) DEFAULT 'Calculation',
                    item_count INT DEFAULT 0,
                    grand_total DOUBLE DEFAULT 0,
                    boq_json LONGTEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
    except Exception:
        pass


def _compute_boq_stats(boq_items: List[Dict[str, Any]]) -> tuple[int, float]:
    count = 0
    grand = 0.0
    for it in boq_items or []:
        if not isinstance(it, dict) or it.get("_is_header"):
            continue
        count += 1
        try:
            tot = it.get("Total")
            if tot is None:
                tot = float(it.get("Quantity") or 0) * float(it.get("Unit Price") or 0)
            grand += float(tot or 0)
        except (TypeError, ValueError):
            pass
    return count, round(grand, 2)


def _save_boq_revision(project_id: int, user_id: int, boq_items: List[Dict[str, Any]], label: str) -> int:
    """Snapshot the current BOQ as the next revision (Rev 0, Rev 1, Rev 2...)."""
    try:
        _ensure_boq_revisions_table()
        df_max = safe_query(
            "SELECT MAX(rev_no) as max_rev FROM qto_boq_revisions WHERE project_id=%s AND user_id=%s",
            (project_id, user_id),
        )
        next_rev = 0
        if not df_max.empty and "max_rev" in df_max.columns:
            raw_max = df_max.iloc[0]["max_rev"]
            if raw_max is not None and str(raw_max).lower() != "nan":
                next_rev = int(raw_max) + 1
        item_count, grand_total = _compute_boq_stats(boq_items)
        safe_execute(
            """
            INSERT INTO qto_boq_revisions (project_id, user_id, rev_no, label, item_count, grand_total, boq_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                project_id,
                user_id,
                next_rev,
                label[:150],
                item_count,
                grand_total,
                json.dumps(boq_items or [], ensure_ascii=False, default=str),
            ),
        )
        return next_rev
    except Exception:
        return 0

class RunCalculationReq(BaseModel):
    project_id: int
    num_floors: int = 2
    gf_height: float = 4.0
    f1_height: float = 4.0
    f2_height: float = 4.0
    excavation_depth: float = 1.25
    include_road_base: bool = True
    concrete_grade: str = "C30/37"
    solid_block_thickness: str = "200mm"
    thermal_block_thickness: str = "200mm"
    hollow_block_thickness: str = "100mm"
    # Roof stair-room handling for the top floor (overrides auto-detection)
    top_floor_is_stair_room: Optional[bool] = None
    stair_room_area: Optional[float] = None
    stair_room_perimeter: Optional[float] = None

class SaveReviewReq(BaseModel):
    project_id: int
    boq_items: List[Dict[str, Any]]

@router.post("/calculate")
async def calculate_boq(req: RunCalculationReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")
        
    state_data = json.loads(df_state.iloc[0]["state_data"])

    # Apply the user's roof stair-room choice BEFORE reconstruct so the
    # correction uses it (else the auto-detected floor_types value is used).
    _cad = state_data.get("confirmed_auto_data") or {}
    if req.top_floor_is_stair_room is not None:
        _cad["top_floor_is_stair_room"] = req.top_floor_is_stair_room
    if req.stair_room_area is not None:
        _cad["stair_room_area"] = req.stair_room_area
    if req.stair_room_perimeter is not None:
        _cad["stair_room_perimeter"] = req.stair_room_perimeter
    state_data["confirmed_auto_data"] = _cad

    # Heal and reconstruct missing fields from extraction_results
    reconstruct_project_inputs(state_data)
    
    # Store settings from the user
    state_data["num_floors"] = req.num_floors
    state_data["gf_height"] = req.gf_height
    state_data["f1_height"] = req.f1_height
    state_data["f2_height"] = req.f2_height
    state_data["concrete_grade"] = req.concrete_grade
    state_data["solid_block_thickness"] = req.solid_block_thickness
    state_data["thermal_block_thickness"] = req.thermal_block_thickness
    state_data["hollow_block_thickness"] = req.hollow_block_thickness
    
    excavation_depth = state_data["confirmed_auto_data"].get("excavation_depth") or req.excavation_depth or 1.25
    state_data["excavation_depth"] = excavation_depth
    state_data["include_road_base"] = req.include_road_base
    
    # Prepare mock inputs from active schedules/confirm data
    # (In project_boq_bridge, the single source of truth is a synthetic project dict)
    
    # Safe fallback for height
    h_db = state_data["confirmed_auto_data"].get("total_villa_height")
    if h_db and float(h_db) > 0:
        total_h = float(h_db)
    else:
        gfh = req.gf_height if req.gf_height > 0 else 4.0
        f1h = req.f1_height if req.f1_height > 0 else 4.0
        f2h = req.f2_height if req.f2_height > 0 else 4.0
        total_h = gfh + (f1h if req.num_floors >= 2 else 0) + (f2h if req.num_floors >= 3 else 0)
        if total_h == 0:
            total_h = 4.0 * max(1, req.num_floors)

    project_payload = {
        "longest_length": state_data["confirmed_auto_data"].get("longest_length"),
        "longest_width": state_data["confirmed_auto_data"].get("longest_width"),
        "plot_area": state_data["confirmed_auto_data"].get("plot_area"),
        "gf_area": state_data["confirmed_auto_data"].get("gf_area"),
        "external_perimeter": state_data["confirmed_auto_data"].get("external_perimeter"),
        "ext_perimeter": state_data["confirmed_auto_data"].get("ext_perimeter"),
        "roof_perimeter": state_data["confirmed_auto_data"].get("roof_perimeter"),
        "roof_slab_area": state_data["confirmed_auto_data"].get("roof_slab_area"),
        "compound_length": state_data["confirmed_auto_data"].get("compound_length"),
        "total_villa_height": total_h,
        "parapet_height": state_data["confirmed_auto_data"].get("parapet_height", 1.0),
        "excavation_depth": excavation_depth,
        "neck_column_height": state_data["confirmed_auto_data"].get("neck_column_height") or 1.0,
        "solid_block_height": state_data["confirmed_auto_data"].get("solid_block_height") or 1.0,
        "staircase_volume_per_level": state_data["confirmed_auto_data"].get("staircase_volume_per_level") or 5.2,
        "sog_thickness": state_data["confirmed_auto_data"].get("sog_thickness") if state_data["confirmed_auto_data"].get("sog_thickness") is not None else 0.10,
        "default_col_length": state_data["confirmed_auto_data"].get("default_col_length") if state_data["confirmed_auto_data"].get("default_col_length") is not None else 0.60,
        "default_col_width": state_data["confirmed_auto_data"].get("default_col_width") if state_data["confirmed_auto_data"].get("default_col_width") is not None else 0.20,
        "walls_user_verified": bool(state_data["confirmed_auto_data"].get("walls_user_verified", False)),
        "structural_levels": req.num_floors,
        "road_base_included": req.include_road_base,
        "concrete_grade": req.concrete_grade,
        "solid_block_thickness": req.solid_block_thickness,
        "thermal_block_thickness": req.thermal_block_thickness,
        "hollow_block_thickness": req.hollow_block_thickness,
        "gf_height": req.gf_height,
        "f1_height": req.f1_height,
        "f2_height": req.f2_height,
        "schedules": state_data["confirmed_auto_data"].get("schedules") or {},
        "floors": state_data["confirmed_auto_data"].get("floors") or {},
        "walls": state_data["confirmed_auto_data"].get("walls") or {},
        "openings": state_data["confirmed_auto_data"].get("openings") or {},
        "total_windows_area": (
            state_data["confirmed_auto_data"].get("total_windows_area")
            if state_data["confirmed_auto_data"].get("total_windows_area") is not None
            else ((state_data["confirmed_auto_data"].get("openings") or {}).get("totals", {}).get("window_area") or 0.0)
        ),
        "total_doors_count": (
            state_data["confirmed_auto_data"].get("total_doors_count")
            if state_data["confirmed_auto_data"].get("total_doors_count") is not None
            else ((state_data["confirmed_auto_data"].get("openings") or {}).get("totals", {}).get("door_count") or 0.0)
        )
    }
    
    df, meta = build_boq_dataframe_from_project(project_payload)
    
    # Convert dataframe to list of items
    boq_items = df.to_dict("records")
    
    import math
    for item in boq_items:
        for k, v in item.items():
            if isinstance(v, float) and math.isnan(v):
                item[k] = None
                
    state_data["boq_items"] = boq_items
    state_data["boq_meta"] = meta
    state_data["current_step"] = 6
    
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET current_step=6, state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, current_user["id"], req.project_id)
    )
    
    # Save project to user's history
    from engine.project_history import save_project
    p_name = state_data.get("project_name", "Villa Project")
    boq_payload = {"items": [item for item in boq_items if not item.get("_is_header")]}
    pid = save_project(p_name, boq_payload, current_user["id"], state_data, 6, state_data.get("project_id"))
    state_data["project_id"] = pid
    
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, current_user["id"], req.project_id)
    )

    rev_no = _save_boq_revision(req.project_id, current_user["id"], boq_items, "Engineering Calculation")
    
    return {
        "boq_items": boq_items,
        "boq_meta": meta,
        "project_id": pid,
        "rev_no": rev_no,
        "next_step": 6
    }

@router.post("/review/save")
async def save_review(req: SaveReviewReq, current_user: dict = Depends(get_current_user)):
    df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], req.project_id))
    if df_state.empty:
        raise HTTPException(status_code=400, detail="No active project.")
        
    state_data = json.loads(df_state.iloc[0]["state_data"])
    state_data["boq_items"] = req.boq_items
    state_data["current_step"] = 8
    
    # Save back to database
    state_json = json.dumps(state_data, ensure_ascii=False, default=str)
    safe_execute(
        "UPDATE qto_active_projects SET current_step=8, state_data=%s WHERE user_id=%s AND project_id=%s",
        (state_json, current_user["id"], req.project_id)
    )
    
    from engine.project_history import save_project
    p_name = state_data.get("project_name", "Villa Project")
    boq_payload = {"items": [item for item in req.boq_items if not item.get("_is_header")]}
    save_project(p_name, boq_payload, current_user["id"], state_data, 8, state_data.get("project_id"))

    rev_no = _save_boq_revision(req.project_id, current_user["id"], req.boq_items, "Reviewed & Confirmed")
    
    return {"message": "Review quantities saved successfully.", "rev_no": rev_no}


@router.get("/boq/revisions")
async def list_boq_revisions(project_id: int, current_user: dict = Depends(get_current_user)):
    """List saved BOQ revisions (Rev 0, Rev 1, Rev 2...) for a user's project."""
    _ensure_boq_revisions_table()
    df = safe_query(
        """
        SELECT id, rev_no, label, item_count, grand_total, created_at
        FROM qto_boq_revisions
        WHERE project_id=%s AND user_id=%s
        ORDER BY rev_no DESC, id DESC
        """,
        (project_id, current_user["id"]),
    )
    if df.empty:
        return []
    out = []
    for row in df.to_dict("records"):
        out.append({
            "id": int(row["id"]),
            "rev_no": int(row["rev_no"]),
            "label": str(row.get("label") or f"Rev {row['rev_no']}"),
            "item_count": int(row.get("item_count") or 0),
            "grand_total": round(float(row.get("grand_total") or 0.0), 2),
            "created_at": str(row.get("created_at") or ""),
        })
    return out


@router.post("/boq/revisions/{rev_id}/restore")
async def restore_boq_revision(rev_id: int, project_id: int, current_user: dict = Depends(get_current_user)):
    """Restore a saved BOQ revision into the active project and record it as the next Rev."""
    _ensure_boq_revisions_table()
    df_rev = safe_query(
        "SELECT id, rev_no, boq_json FROM qto_boq_revisions WHERE id=%s AND project_id=%s AND user_id=%s",
        (rev_id, project_id, current_user["id"]),
    )
    if df_rev.empty:
        raise HTTPException(status_code=404, detail="BOQ revision not found.")

    row = df_rev.iloc[0]
    src_rev_no = int(row["rev_no"])
    restored_items = json.loads(row["boq_json"] or "[]")

    df_state = safe_query(
        "SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s",
        (current_user["id"], project_id),
    )
    if not df_state.empty:
        state_data = json.loads(df_state.iloc[0]["state_data"] or "{}")
        state_data["boq_items"] = restored_items
        safe_execute(
            "UPDATE qto_active_projects SET state_data=%s WHERE user_id=%s AND project_id=%s",
            (json.dumps(state_data, ensure_ascii=False, default=str), current_user["id"], project_id),
        )
        try:
            from engine.project_history import save_project
            boq_payload = {"items": [it for it in restored_items if not it.get("_is_header")]}
            save_project(
                state_data.get("project_name", "Villa Project"),
                boq_payload,
                current_user["id"],
                state_data,
                int(state_data.get("current_step") or 6),
                state_data.get("project_id"),
            )
        except Exception:
            pass

    new_rev = _save_boq_revision(project_id, current_user["id"], restored_items, f"Restored from Rev {src_rev_no}")
    return {
        "message": f"Restored Rev {src_rev_no} as Rev {new_rev}.",
        "boq_items": restored_items,
        "rev_no": new_rev,
    }

def validate_critical_inputs_for_export(state_data: dict):
    confirmed = state_data.get("confirmed_auto_data") or {}
    critical_keys = ["longest_length", "longest_width", "gf_area", "ext_perimeter"]
    missing = [k for k in critical_keys if not confirmed.get(k)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Export blocked: Critical parameters ({', '.join(missing)}) are missing or set to zero. Please configure these in step 4 first."
        )

@router.get("/export/excel")
async def export_excel(project_id: int, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    df_project = safe_query("SELECT name, boq_data, state_data FROM qto_projects WHERE id=%s AND user_id=%s", (project_id, current_user["id"]))
    if df_project.empty:
        raise HTTPException(status_code=404, detail="Project not found.")

    from utils.usage import check_limit, EVENT_EXPORT
    ok, msg = check_limit(current_user, EVENT_EXPORT)
    if not ok:
        raise HTTPException(status_code=403, detail=msg)
        
    proj = df_project.iloc[0]
    p_name = proj["name"]
    
    # Load boq_items from state_data
    state_data = json.loads(proj["state_data"]) if proj["state_data"] else {}
    validate_critical_inputs_for_export(state_data)
    
    items = state_data.get("boq_items") or []
    
    if not items:
        # Generate from scratch
        raise HTTPException(status_code=400, detail="No BOQ items calculated yet for this project.")
        
    import pandas as pd
    df = pd.DataFrame(items)
    excel_bytes = export_boq_to_excel(df, p_name, project_meta=state_data)
    
    # Log export
    from utils.usage import EVENT_EXPORT, log_usage
    log_usage(current_user["id"], EVENT_EXPORT, project_id=project_id)
    
    # Check if this is the user's FIRST export and they are on a free plan, and trigger follow-up email
    try:
        from utils.plans import get_plan_for_user
        plan = get_plan_for_user(current_user["id"], current_user.get("role", "user"))
        if plan.tier == 0:
            df_exports = safe_query("SELECT COUNT(*) as c FROM qto_usage_logs WHERE user_id=%s AND event_type=%s", (current_user["id"], EVENT_EXPORT))
            export_count = df_exports.iloc[0]["c"]
            # Since we just logged the export, it should be 1 if it's the very first time
            if export_count == 1:
                from utils.emailer import send_project_followup_email
                background_tasks.add_task(send_project_followup_email, current_user["email"])
    except Exception as e:
        print(f"Error scheduling followup email: {e}")
    
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={p_name.replace(' ', '_')}_BOQ.xlsx"}
    )

@router.get("/export/pdf")
async def export_pdf(project_id: int, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    df_project = safe_query("SELECT name, boq_data, state_data FROM qto_projects WHERE id=%s AND user_id=%s", (project_id, current_user["id"]))
    if df_project.empty:
        raise HTTPException(status_code=404, detail="Project not found.")

    from utils.usage import check_limit, EVENT_EXPORT
    ok, msg = check_limit(current_user, EVENT_EXPORT)
    if not ok:
        raise HTTPException(status_code=403, detail=msg)
        
    proj = df_project.iloc[0]
    p_name = proj["name"]
    state_data = json.loads(proj["state_data"]) if proj["state_data"] else {}
    validate_critical_inputs_for_export(state_data)
    
    items = state_data.get("boq_items") or []
    if not items:
        raise HTTPException(status_code=400, detail="No BOQ items calculated yet for this project. Please calculate first.")
    
    # Map items to PDF builder expectations
    boq_items = []
    for idx, item in enumerate(items):
        if item.get("_is_header"):
            continue
        boq_items.append({
            "code": item.get("#") or f"ITEM-{idx+1}",
            "name": item.get("Description (English)"),
            "desc_en": item.get("Description (English)"),
            "unit": item.get("Unit"),
            "qty": float(item.get("Quantity") or 0.0),
            "rate_aed": float(item.get("Unit Price") or 0.0),
            "total_aed": float(item.get("Total") or 0.0),
            "category": "Excavation" if "excavation" in str(item.get("Description (English)")).lower() else "foundation"
        })
        
    # Generate pdf file
    pdf_temp_path = f"tmp/boq_export_{project_id}.pdf"
    os.makedirs("tmp", exist_ok=True)
    
    # Load info
    confirmed = state_data.get("confirmed_auto_data") or {}
    project_info = {
        "plot_area": confirmed.get("plot_area"),
        "gf_area": confirmed.get("gf_area"),
        "ext_perimeter": confirmed.get("ext_perimeter")
    }
    
    create_boq_pdf(p_name, boq_items, pdf_temp_path, project_info)
    
    with open(pdf_temp_path, "rb") as f:
        pdf_bytes = f.read()
        
    # Cleanup temp file
    try: os.remove(pdf_temp_path)
    except: pass
    
    # Log export
    from utils.usage import EVENT_EXPORT, log_usage
    log_usage(current_user["id"], EVENT_EXPORT, project_id=project_id)
    
    # Check if this is the user's FIRST export and they are on a free plan, and trigger follow-up email
    try:
        from utils.plans import get_plan_for_user
        plan = get_plan_for_user(current_user["id"], current_user.get("role", "user"))
        if plan.tier == 0:
            df_exports = safe_query("SELECT COUNT(*) as c FROM qto_usage_logs WHERE user_id=%s AND event_type=%s", (current_user["id"], EVENT_EXPORT))
            export_count = df_exports.iloc[0]["c"]
            # Since we just logged the export, it should be 1 if it's the very first time
            if export_count == 1:
                from utils.emailer import send_project_followup_email
                background_tasks.add_task(send_project_followup_email, current_user["email"])
    except Exception as e:
        print(f"Error scheduling followup email: {e}")
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={p_name.replace(' ', '_')}_BOQ.pdf"}
    )

@router.post("/compare")
async def compare_drawings(
    pdf_1: UploadFile = File(...),
    pdf_2: UploadFile = File(...),
    page_num: int = Form(1),
    dpi: int = Form(150),
    current_user: dict = Depends(get_current_user)
):
    import tempfile
    import fitz
    from utils.plan_comparer import compare_plans
    
    # Read bytes
    try:
        pdf_1_bytes = await pdf_1.read()
        pdf_2_bytes = await pdf_2.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail="فشل في قراءة ملفات المخططات المرفوعة.")

    # Validate PDF and page count
    try:
        doc1 = fitz.open(stream=pdf_1_bytes, filetype="pdf")
        len1 = len(doc1)
        doc1.close()
    except Exception:
        raise HTTPException(status_code=400, detail="المخطط الأول ليس ملف PDF صالح.")

    try:
        doc2 = fitz.open(stream=pdf_2_bytes, filetype="pdf")
        len2 = len(doc2)
        doc2.close()
    except Exception:
        raise HTTPException(status_code=400, detail="المخطط الثاني ليس ملف PDF صالح.")

    if page_num < 1 or page_num > len1 or page_num > len2:
        raise HTTPException(
            status_code=400,
            detail=f"رقم الصفحة ({page_num}) غير صالح. المخطط الأول يحتوي على {len1} صفحات والمخطط الثاني يحتوي على {len2} صفحات."
        )

    # Save to temp files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
        tmp1.write(pdf_1_bytes)
        path1 = tmp1.name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
        tmp2.write(pdf_2_bytes)
        path2 = tmp2.name
        
    import uuid
    safe_dpi = max(72, min(220, int(dpi or 150)))
    output_path = os.path.join(tempfile.gettempdir(), f"api_plan_comparison_diff_{page_num}_{uuid.uuid4().hex[:8]}.png")
    
    # Run comparison
    success = compare_plans(path1, path2, page_num=page_num - 1, output_path=output_path, dpi=safe_dpi)
    
    # Cleanup PDFs
    try:
        os.remove(path1)
        os.remove(path2)
    except:
        pass
        
    if not success or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="فشل في توليد صورة الفروقات وتراكب المخططات.")
        
    # Read diff image
    with open(output_path, "rb") as f:
        img_bytes = f.read()
        
    # Cleanup output image
    try:
        os.remove(output_path)
    except:
        pass
        
    return StreamingResponse(io.BytesIO(img_bytes), media_type="image/png")
