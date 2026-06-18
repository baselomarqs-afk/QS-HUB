import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT state_data FROM qto_projects WHERE id = 810001')
        r = cur.fetchone()
        data = r['state_data'] if isinstance(r, dict) else r[0]
        if isinstance(data, str): data = json.loads(data)
        
        ext_res = data.get('extraction_results', {})
        for p_id, page in ext_res.items():
            if isinstance(page, dict) and 'windows' in page:
                print(f"Page {p_id} has windows: {len(page['windows'])} items")
