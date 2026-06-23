import sqlite3
import json

db_path = 'qto_local.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT name, boq_data FROM qto_projects WHERE name LIKE '%OMAR%'")
rows = cur.fetchall()
for r in rows:
    print('Project:', r[0])
    try:
        boq = json.loads(r[1])
        if 'floors' in boq:
            for f, fdata in boq['floors'].items():
                print(f"  Floor: {f}, ext_perim: {fdata.get('ext_perimeter')}, int_wall: {fdata.get('wall_internal')}")
        if 'door_count' in boq:
            print('  door_count:', boq['door_count'])
        if 'window_count' in boq:
            print('  window_count:', boq['window_count'])
    except Exception as e:
        print('Error:', e)
