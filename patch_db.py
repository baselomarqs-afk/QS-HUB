import json
from utils.db import safe_query, safe_execute
from api.routers.data_review import reconstruct_project_inputs

df = safe_query("SELECT user_id, project_id, state_data FROM qto_active_projects")
for idx, row in df.iterrows():
    try:
        state_data = json.loads(row["state_data"])
        # Only patch if extraction_results exists
        if "extraction_results" in state_data:
            # We clear out the cached flat keys to force re-computation
            if "confirmed_auto_data" in state_data:
                confirmed = state_data["confirmed_auto_data"]
                confirmed.pop("int_walls_10cm_m", None)
                confirmed.pop("int_walls_20cm_m", None)
                if "openings" in confirmed and "totals" in confirmed["openings"]:
                    confirmed["openings"]["totals"]["door_count"] = 0
                    confirmed["openings"]["totals"]["window_area"] = 0.0
            
            reconstruct_project_inputs(state_data)
            
            new_state_str = json.dumps(state_data, ensure_ascii=False, default=str)
            safe_execute(
                "UPDATE qto_active_projects SET state_data=%s WHERE user_id=%s AND project_id=%s",
                (new_state_str, row["user_id"], row["project_id"])
            )
            print(f"Patched project {row['project_id']} for user {row['user_id']}")
    except Exception as e:
        print(f"Failed project {row['project_id']}: {e}")
print("Done patching active projects.")
