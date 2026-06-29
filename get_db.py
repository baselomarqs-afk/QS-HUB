import sys, os, json
sys.path.append(os.getcwd())
from utils.db import safe_query
df = safe_query("SELECT id, name, state_data FROM qto_projects WHERE name LIKE %s ORDER BY created_at DESC LIMIT 1", ('%Adel%',))
res = df.iloc[0] if not df.empty else None
if res is not None:
    open('adel_state.json', 'w').write(res['state_data'])
    print(f"ID: {res['id']}, Name: {res['name']}")
else:
    print('No state')
