from utils.db import get_connection

with get_connection() as conn:
    cur = conn.cursor()
    cur.execute('DELETE FROM qto_active_projects')
    conn.commit()
    print('All projects deleted successfully.')
