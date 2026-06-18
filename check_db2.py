import sys
import json
import traceback
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, state_data FROM qto_projects ORDER BY id DESC LIMIT 1')
            r = cur.fetchone()
            if r:
                data = r['state_data'] if isinstance(r, dict) else r[1]
                if isinstance(data, str): data = json.loads(data)
                openings = data.get('confirmed_auto_data', {}).get('openings', {})
                print('Doors totals:', openings.get('totals', {}).get('door_count'))
                print('Windows area:', openings.get('totals', {}).get('window_area'))
                
                sum_a = 0
                for w in openings.get('windows', []):
                    qty = w.get('count_in_plans') or w.get('count') or w.get('qty') or w.get('quantity') or 1
                    if isinstance(qty, str):
                        try:
                            qty = int(qty.strip())
                        except:
                            qty = 1
                    qty = int(qty)
                    width = float(w.get('width') or w.get('width_m') or w.get('width_mm') or 1.0)
                    height = float(w.get('height') or w.get('height_m') or w.get('height_mm') or 1.0)
                    if width > 10: width /= 1000.0
                    if height > 10: height /= 1000.0
                    a = qty * width * height
                    sum_a += a
                    print(f"W: mark={w.get('mark')} qty={qty} w={width} h={height} => area={a}")
                print(f"Total calculated window area = {sum_a}")
                
                sum_d = 0
                for d in openings.get('doors', []):
                    qty = d.get('count_in_plans') or d.get('count') or d.get('qty') or d.get('quantity') or 1
                    if isinstance(qty, str):
                        try:
                            qty = int(qty.strip())
                        except:
                            qty = 1
                    qty = int(qty)
                    print(f"D: mark={d.get('mark')} qty={qty}")
                    sum_d += qty
                print(f"Total calculated doors = {sum_d}")

except Exception as e:
    traceback.print_exc()
