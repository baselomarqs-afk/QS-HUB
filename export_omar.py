import sqlite3, json
conn = sqlite3.connect('qto_local.db')
c = conn.cursor()
c.execute("SELECT boq_data FROM qto_projects WHERE name LIKE '%OMAR%' ORDER BY id DESC LIMIT 1")
row = c.fetchone()
if row and row[0]:
    with open('latest_project.json', 'w', encoding='utf-8') as f:
        json.dump(json.loads(row[0]), f, indent=2, ensure_ascii=False)
    print('Saved to latest_project.json')
else:
    print('Not found')
