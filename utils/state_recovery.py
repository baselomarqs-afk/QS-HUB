import json
import functools
from utils.db import safe_execute, safe_query

import threading

def _async_save_project(project_name, boq_data, user_id, state_to_save, current_step, project_id):
    try:
        from engine.project_history import save_project
        save_project(
            project_name=project_name,
            boq_data=boq_data,
            user_id=user_id,
            state_data=state_to_save,
            current_step=current_step,
            project_id=project_id
        )
    except Exception as e:
        print(f"Async DB Save error: {e}")

def save_project_state(state: dict, user_id: int):
    """Saves the current state (only JSON serializable data) to DB asynchronously."""
    if not user_id:
        return
        
    state_to_save = {}
    keys_to_save = [
        "current_step", "project_name", "num_floors", 
        "gf_height", "f1_height", "f2_height", "excavation_depth", "include_road_base",
        "classified_pages", "extraction_results", "confirmed_auto_data"
    ]
    
    for k in keys_to_save:
        if k in state:
            state_to_save[k] = state[k]
            
    # Also save boolean step markers
    for k in state.keys():
        if k.startswith("step_done_") or k.startswith("auto_") or k.startswith("manual_") or k.startswith("ci_") or k.startswith("fin_") or k.startswith("super_") or k.startswith("sub_") or k.startswith("conf_") or k.startswith("open_"):
            state_to_save[k] = state[k]

    from datetime import datetime
    
    project_name = state.get("project_name")
    if not project_name or str(project_name).strip() == "" or str(project_name).startswith("Project_"):
        if "project_id" not in state:
            project_name = f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            state["project_name"] = project_name
        else:
            project_name = state.get("project_name", f"Project_{user_id}_{state.get('current_step', 1)}")

    boq_data = {}
    if "boq_df" in state:
        df = state["boq_df"]
        boq_data = {"items": df[df["_is_header"] == False].to_dict("records")}
        
    project_id = state.get("project_id")
    current_step = state.get("current_step", 1)

    t = threading.Thread(
        target=_async_save_project,
        args=(project_name, boq_data, user_id, state_to_save, current_step, project_id),
        daemon=True
    )
    t.start()
    
    check_has_active_project.cache_clear()

@functools.lru_cache(maxsize=128)
def check_has_active_project(user_id: int):
    df_state = safe_query("SELECT current_step, updated_at FROM qto_active_projects WHERE user_id=%s", (user_id,))
    if not df_state.empty:
        return True, df_state.iloc[0]["current_step"], df_state.iloc[0]["updated_at"]
    return False, None, None

def load_project_state(user_id: int):
    """Loads state from DB and returns it. Returns (True, state_data) or (False, {})."""
    if not user_id:
        return False, {}
        
    df = safe_query("SELECT state_data FROM qto_active_projects WHERE user_id = %s", (user_id,))
    if df.empty:
        return False, {}
        
    try:
        raw_data = df.iloc[0]["state_data"]
        # Handle stringified JSON from db
        if isinstance(raw_data, str):
            state_data = json.loads(raw_data)
        else:
            state_data = raw_data
            
        return True, state_data
    except Exception as e:
        print(f"Failed to load state from DB: {e}")
        return False, {}

def clear_project_state(user_id: int):
    """Deletes the saved state when user starts a new project."""
    if not user_id:
        return
    safe_execute("DELETE FROM qto_active_projects WHERE user_id = %s", (user_id,))
    check_has_active_project.cache_clear()
