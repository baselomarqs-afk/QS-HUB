import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import safe_query, safe_execute

df = safe_query("SELECT id, state_data FROM qto_active_projects WHERE id = 1260001")
if not df.empty:
    sd = json.loads(df.iloc[0]['state_data'])
    
    if "confirmed_auto_data" not in sd:
        sd["confirmed_auto_data"] = {}
    
    sd["confirmed_auto_data"]["total_villa_height"] = 14.25
        
    safe_execute("UPDATE qto_active_projects SET state_data = %s WHERE id = 1260001", (json.dumps(sd),))
    print("Fixed Adel DB total_villa_height!")
