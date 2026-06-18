import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query, safe_execute

df = safe_query("SELECT id, state_data FROM qto_active_projects WHERE id = 1260001")
if not df.empty:
    sd = json.loads(df.iloc[0]['state_data'])
    floors = sd.get('confirmed_auto_data', {}).get('floors', {})
    if 'gf' in floors:
        floors['gf']['area'] = 290.19
    if '1f' in floors:
        floors['1f']['area'] = 290.19
    if '2f' in floors:
        floors['2f']['area'] = 27.84
        floors['2f']['ext_perimeter'] = 21.1 # sqrt(27.84)*4 as a heuristic
        
    safe_execute("UPDATE qto_active_projects SET state_data = %s WHERE id = 1260001", (json.dumps(sd),))
    print("Fixed Adel DB!")
