import json
from engine.project_boq_bridge import build_boq_dataframe_from_project, compute_all_quantities
with open("_project_data.json", "r", encoding="utf-8") as f:
    project = json.load(f)

results, meta = compute_all_quantities(project)
print(f"col_roof = {results.get('col_roof')}")
print(f"col_1st_to_2nd = {results.get('col_1st_to_2nd')}")
