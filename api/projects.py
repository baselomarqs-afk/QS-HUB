from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from utils.db import safe_query, safe_execute
from api.auth import get_current_user
from engine.project_history import save_project, load_all_projects

router = APIRouter()

class SaveProjectReq(BaseModel):
    project_id: Optional[int] = None
    project_name: str
    state_data: Optional[Dict[str, Any]] = None
    boq_data: Optional[Dict[str, Any]] = None
    current_step: int = 1

class ScaleCalibrationReq(BaseModel):
    pixel_distance: float
    real_distance: float

@router.get("")
@router.get("/")
async def list_projects(current_user: dict = Depends(get_current_user)):
    projects = load_all_projects(current_user["id"])
    return projects

@router.get("/active")
async def get_active_project(project_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    if project_id:
        df = safe_query("SELECT current_step, updated_at, state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
    else:
        df = safe_query("SELECT current_step, updated_at, state_data, project_id FROM qto_active_projects WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1", (current_user["id"],))
    if df.empty:
        return {"has_active": False}
    row = df.iloc[0]

    import json as _json
    from api.routers.data_review import reconstruct_project_inputs
    raw = row["state_data"]
    state_data = _json.loads(raw) if isinstance(raw, str) else (raw or {})
    if state_data.get("current_step", 0) >= 3:
        reconstruct_project_inputs(state_data)
        safe_execute(
            "UPDATE qto_active_projects SET state_data=%s WHERE user_id=%s AND project_id=%s",
            (_json.dumps(state_data, ensure_ascii=False, default=str), current_user["id"], row.get("project_id") or project_id)
        )

    res = {
        "has_active": True,
        "current_step": int(row["current_step"]),
        "updated_at": row["updated_at"],
        "state_data": state_data
    }
    if "project_id" in row:
        res["project_id"] = int(row["project_id"])
    return res

@router.delete("/active")
async def clear_active_project(project_id: Optional[int] = None, current_user: dict = Depends(get_current_user)):
    if project_id:
        success, err = safe_execute("DELETE FROM qto_active_projects WHERE user_id = %s AND project_id = %s", (current_user["id"], project_id))
    else:
        success, err = safe_execute("DELETE FROM qto_active_projects WHERE user_id = %s", (current_user["id"],))
    if not success:
        raise HTTPException(status_code=500, detail=f"Database clear failed: {err}")
    return {"message": "Active project state cleared."}

@router.post("")
@router.post("/")
async def save_project_route(req: SaveProjectReq, current_user: dict = Depends(get_current_user)):
    # Load existing state to merge
    existing_state = {}
    project_id = req.project_id
    is_new_project = False
    
    if project_id:
        df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
        if not df_state.empty and df_state.iloc[0]["state_data"]:
            try:
                import json as json_lib
                existing_state = json_lib.loads(df_state.iloc[0]["state_data"])
            except Exception as ex:
                print(f"Error parsing existing state: {ex}")
    else:
        is_new_project = True
        from utils.usage import check_limit, EVENT_PROJECT
        ok, msg = check_limit(current_user, EVENT_PROJECT)
        if not ok:
            raise HTTPException(status_code=403, detail=msg)
            
    # Merge states
    def merge_states(existing: dict, incoming: dict) -> dict:
        if not existing:
            return incoming
        if not incoming:
            return existing
        merged = existing.copy()
        for k, v in incoming.items():
            if k == "confirmed_auto_data" and isinstance(v, dict):
                existing_confirmed = merged.get("confirmed_auto_data") or {}
                new_confirmed = v.copy()
                # If structured keys are empty/falsy in incoming, preserve existing database ones
                for struct_key in ["floors", "walls", "schedules", "openings"]:
                    if not new_confirmed.get(struct_key) and existing_confirmed.get(struct_key):
                        new_confirmed[struct_key] = existing_confirmed[struct_key]
                merged["confirmed_auto_data"] = new_confirmed
            else:
                merged[k] = v
        return merged
        
    state_to_save = merge_states(existing_state, req.state_data or {})

    pid = save_project(
        project_name=req.project_name,
        boq_data=req.boq_data or {},
        user_id=current_user["id"],
        state_data=state_to_save,
        current_step=req.current_step,
        project_id=req.project_id
    )
    if pid is None:
        raise HTTPException(status_code=500, detail="Failed to save project.")
    
    # Update active project state table as well
    from utils.db import upsert_active_state
    upsert_active_state(current_user["id"], pid, req.current_step, state_to_save)
        
    if is_new_project:
        from utils.usage import settle_project_creation
        settle_project_creation(current_user, "qto", {"project_id": pid, "project_name": req.project_name})
    
    return {"message": "Project saved successfully.", "project_id": pid}

@router.get("/{project_id}")
async def get_project(project_id: int, current_user: dict = Depends(get_current_user)):
    df = safe_query(
        "SELECT id, name, date, boq_data, state_data, current_step FROM qto_projects WHERE id=%s AND user_id=%s",
        (project_id, current_user["id"])
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="Project not found.")
    row = df.iloc[0]
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "date": row["date"],
        "boq_data": row["boq_data"],
        "state_data": row["state_data"],
        "current_step": int(row["current_step"]) if row["current_step"] else 1
    }

@router.delete("/{project_id}")
async def delete_project(project_id: int, current_user: dict = Depends(get_current_user)):
    success, err = safe_execute(
        "DELETE FROM qto_projects WHERE id=%s AND user_id=%s",
        (project_id, current_user["id"])
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Database delete failed: {err}")
    return {"message": "Project deleted successfully."}

@router.post("/{project_id}/calibrate_scale")
async def calibrate_scale(project_id: int, req: ScaleCalibrationReq, current_user: dict = Depends(get_current_user)):
    if req.pixel_distance <= 0:
        raise HTTPException(status_code=400, detail="Pixel distance must be greater than zero.")
    
    scale_factor = req.real_distance / req.pixel_distance
    
    # Update qto_active_projects state_data
    df = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
    if not df.empty:
        import json
        raw = df.iloc[0]["state_data"]
        state_data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        state_data["scale_factor"] = scale_factor
        safe_execute(
            "UPDATE qto_active_projects SET state_data=%s WHERE user_id=%s AND project_id=%s",
            (json.dumps(state_data, ensure_ascii=False, default=str), current_user["id"], project_id)
        )
        
    # Also update qto_projects state_data
    df_proj = safe_query("SELECT state_data FROM qto_projects WHERE user_id=%s AND id=%s", (current_user["id"], project_id))
    if not df_proj.empty:
        import json
        raw = df_proj.iloc[0]["state_data"]
        state_data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        state_data["scale_factor"] = scale_factor
        safe_execute(
            "UPDATE qto_projects SET state_data=%s WHERE user_id=%s AND id=%s",
            (json.dumps(state_data, ensure_ascii=False, default=str), current_user["id"], project_id)
        )
        
    return {"message": "Scale calibrated successfully.", "scale_factor": scale_factor}
