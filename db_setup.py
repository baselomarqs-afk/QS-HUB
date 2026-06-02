import os

from migrate_db import run_migrations
from utils.db import get_connection
from utils.security import password_hash

def setup_db():
    run_migrations()
    with get_connection() as conn:
        with conn.cursor() as cur:
            admin_email = os.environ.get("QTO_ADMIN_EMAIL")
            admin_password = os.environ.get("QTO_ADMIN_PASSWORD")
            force_reset = os.environ.get("QTO_ADMIN_FORCE_RESET") == "1"
            if not admin_email or not admin_password:
                print("Skipping admin seed. Set QTO_ADMIN_EMAIL and QTO_ADMIN_PASSWORD to seed an admin.")
                return
            cur.execute("SELECT id FROM qto_users WHERE email = %s", (admin_email,))
            existing = cur.fetchone()
            hashed_pw = password_hash(admin_password)
            if not existing:
                cur.execute(
                    "INSERT INTO qto_users (email, password_hash, role) VALUES (%s, %s, %s)",
                    (admin_email, hashed_pw, 'admin')
                )
                print(f"Admin user {admin_email} created successfully.")
            elif force_reset:
                cur.execute(
                    "UPDATE qto_users SET password_hash=%s, role='admin' WHERE email=%s",
                    (hashed_pw, admin_email),
                )
                print(f"Admin user {admin_email} password reset from environment.")
            else:
                print(f"Admin user {admin_email} already exists.")
        conn.commit()
    print("Database setup complete.")

if __name__ == '__main__':
    setup_db()
