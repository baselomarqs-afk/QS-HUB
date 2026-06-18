import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query
df = safe_query("SELECT state_data FROM qto_active_projects WHERE id=1260013")
sd = json.loads(df.iloc[0]['state_data'])

for k, v in sd.get("extraction_results", {}).items():
    if "elevations" in k or "sections" in k:
        print(f"--- {k} ---")
        print(json.dumps(v, indent=2))
