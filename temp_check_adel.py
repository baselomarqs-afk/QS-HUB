import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query
df = safe_query("SELECT id, state_data FROM qto_active_projects WHERE id=1260013")
sd = json.loads(df.iloc[0]['state_data'])
auto = sd.get("confirmed_auto_data", {})
print(json.dumps(auto, indent=2))
