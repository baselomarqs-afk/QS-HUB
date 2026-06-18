import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query
df = safe_query("SELECT state_data FROM qto_active_projects WHERE id = 1260001")
sd = json.loads(df.iloc[0]['state_data'])
floors = sd.get('confirmed_auto_data', {}).get('floors', {})
for fk, f in floors.items():
    print(f"{fk}: area={f.get('area')}, perim={f.get('ext_perimeter')}, h={f.get('height')}")
