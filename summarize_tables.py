import json
import re

with open('st_tables.json', encoding='utf-8') as f:
    st_tables = json.load(f)

summary = []
for t in st_tables:
    data = t['data']
    # If the first row contains columns like 'COL', 'MARK', 'BREADTH', 'WIDTH'
    header = " ".join(data[0]).lower()
    if 'column' in header or 'col' in header or 'slab' in header or 'foundation' in header or 'beam' in header or 'schedule' in header:
        summary.append(f"Table on Page {t['page']}:")
        for row in data[:4]:
            summary.append(" | ".join([str(c).replace('\n', ' ') for c in row]))
        summary.append("-" * 40)

with open('summary.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(summary))
