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
        for page_id, page in ext_res.items():
            if not isinstance(page, dict): continue
            if 'doors' in page:
                for d in page['doors']: print(f"Door: {d.get('mark')} - count: {d.get('count_in_plans') or d.get('count') or d.get('qty')}")
            if 'windows' in page:
                for w in page['windows']: print(f"Window: {w.get('mark')} - {w.get('width_m') or w.get('width_mm')} x {w.get('height_m') or w.get('height_mm')} - count: {w.get('count_in_plans') or w.get('count')}")
