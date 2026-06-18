import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, state_data FROM qto_projects ORDER BY id DESC LIMIT 1')
            r = cur.fetchone()
            pid = r['id'] if isinstance(r, dict) else r[0]
            data = r['state_data'] if isinstance(r, dict) else r[1]
            if isinstance(data, str): data = json.loads(data)
            
            c = data.get('confirmed_auto_data', {})
            openings = c.get('openings', {})
            if 'totals' not in openings: openings['totals'] = {}
            
            ext_res = data.get('extraction_results', {})
            for page_id, page in ext_res.items():
                if not isinstance(page, dict): continue
                if 'doors' in page:
                    d_count = 0
                    for d in page['doors']:
                        mark = str(d.get('mark') or d.get('type') or '').strip().upper()
                        if mark.startswith('A'): continue
                        qty = int(d.get('count_in_plans') or d.get('count') or d.get('qty') or 1)
                        d_count += qty
                    openings['totals']['door_count'] = d_count
                    openings['doors'] = page['doors']
                
                if 'windows' in page:
                    w_area = 0.0
                    for w in page['windows']:
                        qty = int(w.get('count_in_plans') or w.get('count') or w.get('qty') or 1)
                        width = float(w.get('width_m') or w.get('width') or (float(w.get('width_mm') or 0)/1000) or 1.0)
                        height = float(w.get('height_m') or w.get('height') or (float(w.get('height_mm') or 0)/1000) or 1.0)
                        if width > 10: width /= 1000.0
                        if height > 10: height /= 1000.0
                        w_area += (qty * width * height)
                    openings['totals']['window_area'] = w_area
                    openings['windows'] = page['windows']
                    
            print(f"Project {pid}: door_count updated to {openings['totals'].get('door_count')}, window_area updated to {openings['totals'].get('window_area')}")
            
            # Recalculate BOQ!
            from engine.project_boq_bridge import build_boq_dataframe_from_project
            try:
                df, meta = build_boq_dataframe_from_project(c)
                import math
                def clean_float(val):
                    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)): return 0.0
                    return val
                boq_items = []
                for _, row in df.iterrows():
                    item = row.to_dict()
                    boq_items.append({k: clean_float(v) for k, v in item.items()})
                data['boq_items'] = boq_items
                data['boq_meta'] = meta
                print('BOQ recalculated successfully!')
            except Exception as boq_e:
                print('Failed to recalculate BOQ:', boq_e)
            
            cur.execute('UPDATE qto_projects SET state_data = %s WHERE id = %s', (json.dumps(data), pid))
        conn.commit()
        print('DB updated successfully.')
except Exception as e:
    import traceback
    traceback.print_exc()
