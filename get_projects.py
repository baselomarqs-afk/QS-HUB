import sys, json
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute('SELECT id, created_at, pdf_name FROM qto_projects ORDER BY id DESC LIMIT 5')
        for r in cur.fetchall():
            if isinstance(r, dict): print(f"{r['id']} - {r['created_at']} - {r['pdf_name']}")
            else: print(f"{r[0]} - {r[1]} - {r[2]}")
