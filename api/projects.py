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
    res = {
        "has_active": True,
        "current_step": int(row["current_step"]),
        "updated_at": row["updated_at"],
        "state_data": row["state_data"]
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
    if project_id:
        df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s AND project_id=%s", (current_user["id"], project_id))
    else:
        df_state = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id=%s ORDER BY updated_at DESC LIMIT 1", (current_user["id"],))
    if not df_state.empty and df_state.iloc[0]["state_data"]:
        try:
            import json as json_lib
            existing_state = json_lib.loads(df_state.iloc[0]["state_data"])
        except Exception as ex:
            print(f"Error parsing existing state: {ex}")
            
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
    import json
    state_json = json.dumps(state_to_save, ensure_ascii=False, default=str)
    from utils.db import is_sqlite
    if is_sqlite():
        safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(user_id, project_id) DO UPDATE SET 
                current_step=excluded.current_step, 
                state_data=excluded.state_data, 
                updated_at=datetime('now', 'localtime')
            """,
            (current_user["id"], pid, req.current_step, state_json)
        )
    else:
        safe_execute(
            """
            INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE current_step=%s, state_data=%s, updated_at=CURRENT_TIMESTAMP
            """,
            (current_user["id"], pid, req.current_step, state_json, req.current_step, state_json)
        )
    
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
