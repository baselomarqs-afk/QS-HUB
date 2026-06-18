import sys
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from engine.item_calculator import _calc_ext_plaster
from utils.db import safe_query
import json

df = safe_query("SELECT state_data FROM qto_active_projects WHERE id=1260013")
sd = json.loads(df.iloc[0]['state_data'])
auto = sd.get("confirmed_auto_data", {})

project_payload = {
    "longest_length": auto.get("longest_length"),
    "longest_width": auto.get("longest_width"),
    "plot_area": auto.get("plot_area"),
    "gf_area": auto.get("gf_area"),
    "ext_perimeter": auto.get("ext_perimeter"),
    "total_villa_height": auto.get("total_villa_height") if auto.get("total_villa_height") else (4.0 + 4.0),
    "total_windows_area": (auto.get("openings") or {}).get("totals", {}).get("window_area") or 0.0,
}

plaster = _calc_ext_plaster(project_payload)
print(f"total_villa_height: {project_payload['total_villa_height']}")
print(f"ext_perimeter: {project_payload['ext_perimeter']}")
print(f"total_windows_area: {project_payload['total_windows_area']}")
print(f"Calc plaster: {plaster}")
