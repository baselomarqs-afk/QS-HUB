"""Recreate qto_active_projects table to support multiple active projects per user."""
from __future__ import annotations
from utils.db import is_sqlite


def apply(conn) -> None:
    with conn.cursor() as cur:
        # Drop old single-project active state table
        cur.execute("DROP TABLE IF EXISTS qto_active_projects")
        
        if is_sqlite():
            cur.execute(
                """
                CREATE TABLE qto_active_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    current_step INTEGER DEFAULT 1,
                    state_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES qto_users(id) ON DELETE CASCADE,
                    UNIQUE (user_id, project_id)
                );
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE qto_active_projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    project_id INT NOT NULL,
                    current_step INT DEFAULT 1,
                    state_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES qto_users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_project (user_id, project_id)
                );
                """
            )
    conn.commit()
