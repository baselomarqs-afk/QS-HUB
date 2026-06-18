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
        windows = ext_res.get('architectural_p11_arch_windows', {}).get('windows', [])
        total_area = 0.0
        for w in windows:
            qty = int(w.get('count_in_plans') or w.get('count') or w.get('qty') or w.get('quantity') or 1)
            width = float(w.get('width_m') or w.get('width') or (float(w.get('width_mm') or 0)/1000) or 1.0)
            height = float(w.get('height_m') or w.get('height') or (float(w.get('height_mm') or 0)/1000) or 1.0)
            if width > 10: width /= 1000.0
            if height > 10: height /= 1000.0
            area = qty * width * height
            print(f"{w.get('mark')}: {qty} * {width} * {height} = {area}")
            total_area += area
        print('Total area calculated by data_review:', total_area)
