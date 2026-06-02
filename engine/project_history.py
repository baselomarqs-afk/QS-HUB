"""
حفظ وتحميل المشاريع
"""
import json
import os
from datetime import datetime
from typing import List, Dict
from utils.db import get_connection


def save_project(project_name: str, boq_data: Dict, user_id: int | None = None, state_data: Dict | None = None, current_step: int = 1, project_id: int | None = None) -> int | None:
    """يحفظ مشروع في قاعدة البيانات ويعيد ID الخاص به"""
    try:
        boq_json = json.dumps(boq_data, ensure_ascii=False, default=str)
        state_json = json.dumps(state_data or {}, ensure_ascii=False, default=str)
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                if project_id:
                    cur.execute(
                        "UPDATE qto_projects SET name = %s, date = %s, boq_data = %s, state_data = %s, current_step = %s WHERE id = %s AND user_id = %s",
                        (project_name, date_str, boq_json, state_json, current_step, project_id, user_id or 0)
                    )
                    ret_id = project_id
                else:
                    cur.execute(
                        "SELECT id FROM qto_projects WHERE user_id = %s AND name = %s",
                        (user_id or 0, project_name),
                    )
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            "UPDATE qto_projects SET date = %s, boq_data = %s, state_data = %s, current_step = %s WHERE id = %s AND user_id = %s",
                            (date_str, boq_json, state_json, current_step, row['id'], user_id or 0)
                        )
                        ret_id = row['id']
                    else:
                        cur.execute(
                            "INSERT INTO qto_projects (user_id, name, date, boq_data, state_data, current_step) VALUES (%s, %s, %s, %s, %s, %s)",
                            (user_id or 0, project_name, date_str, boq_json, state_json, current_step)
                        )
                        ret_id = cur.lastrowid
            conn.commit()
        return ret_id
    except Exception as e:
        print(f"DB Save error: {e}")
        return None


def load_all_projects(user_id: int | None = None, include_data: bool = False) -> List[Dict]:
    """يحمل كل المشاريع المحفوظة من قاعدة البيانات"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if include_data:
                    query = "SELECT id, name, date, boq_data, state_data, current_step FROM qto_projects"
                else:
                    query = "SELECT id, name, date, current_step FROM qto_projects"
                
                if user_id is None:
                    cur.execute(f"{query} ORDER BY id ASC")
                else:
                    cur.execute(
                        f"{query} WHERE user_id=%s ORDER BY id ASC",
                        (user_id,),
                    )
                rows = cur.fetchall()
            
        projects = []
        for row in rows:
            p = {
                "id": row['id'],
                "name": row['name'],
                "date": row['date'],
                "current_step": row.get('current_step') or 1
            }
            if include_data:
                p["boq_data"] = row.get('boq_data')
                p["state_data"] = row.get('state_data')
            projects.append(p)
        return projects
    except Exception as e:
        print(f"DB Load error: {e}")
        return []


def get_project_names(user_id: int | None = None) -> List[str]:
    return [p["name"] for p in load_all_projects(user_id)]
