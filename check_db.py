import sys
import json
import pprint
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, state_data FROM qto_projects ORDER BY id DESC LIMIT 1')
            r = cur.fetchone()
            if r:
                data = r[1]
                if isinstance(data, str): data = json.loads(data)
                openings = data.get('confirmed_auto_data', {}).get('openings', {})
                print('Doors:', openings.get('totals', {}).get('door_count'))
                print('Windows:', openings.get('totals', {}).get('window_area'))
                
                sum_a = 0
                for w in openings.get('windows', []):
                    qty = int(w.get('count_in_plans') or w.get('count') or w.get('qty') or w.get('quantity') or 1)
                    width = float(w.get('width') or w.get('width_m') or 1.0)
                    height = float(w.get('height') or w.get('height_m') or 1.0)
                    if width > 10: width /= 1000.0
                    if height > 10: height /= 1000.0
                    a = qty * width * height
                    sum_a += a
                    print(f"W: mark={w.get('mark')} qty={qty} w={width} h={height} => area={a}")
                print(f"Total calculated area = {sum_a}")
                
                sum_d = 0
                for d in openings.get('doors', []):
                    qty = int(d.get('count_in_plans') or d.get('count') or d.get('qty') or d.get('quantity') or 1)
                    print(f"D: mark={d.get('mark')} qty={qty}")
                    sum_d += qty
                print(f"Total calculated doors = {sum_d}")

except Exception as e:
    print('Error:', e)
