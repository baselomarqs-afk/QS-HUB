import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query
df = safe_query("SELECT id, state_data FROM qto_active_projects ORDER BY id DESC LIMIT 1")
for idx, row in df.iterrows():
    sd = json.loads(row['state_data'])
    ext = sd.get('extraction_results', {})
    for page_key, page in ext.items():
        if page.get('detected_type') in ['ground_floor_plan', 'first_floor_plan', 'second_floor_plan']:
            print(f"{page.get('detected_type')}: from_cache={page.get('_from_cache')}")
