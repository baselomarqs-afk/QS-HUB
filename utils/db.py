"""
وحدة اتصال قاعدة البيانات المركزية — Centralized DB Connection
================================================================
استخدام موحّد لقاعدة البيانات عبر جميع الملفات.
يضمن إغلاق الاتصال بأمان حتى عند حدوث خطأ (Context Manager).

الاستخدام:
    from utils.db import get_connection, safe_query, safe_execute

    # طريقة 1: Context manager (مُوصى به)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM qto_users")
            rows = cur.fetchall()

    # طريقة 2: استعلام آمن مع إرجاع DataFrame
    df = safe_query("SELECT id, email FROM qto_users WHERE role=%s", ("admin",))

    # طريقة 3: تنفيذ أمر كتابة آمن
    success, msg = safe_execute(
        "INSERT INTO qto_market_prices (item_name, unit, rate_aed) VALUES (%s, %s, %s)",
        ("Rebar 8mm", "ton", 2668)
    )
"""
import pandas as pd
from contextlib import contextmanager
from utils.settings import DbSettings
import sqlite3
import logging
import re
import os

logger = logging.getLogger("qto.db")

def is_sqlite() -> bool:
    try:
        settings = DbSettings.from_env()
        return not settings.host
    except Exception:
        return True

def translate_sql(sql: str) -> str:
    # 1. Parameter markers: %s -> ?
    sql = sql.replace("%s", "?")
    
    # 2. DATE_SUB(NOW(), INTERVAL 15 MINUTE) -> datetime('now', 'localtime', '-15 minutes')
    sql = re.sub(
        r"DATE_SUB\(\s*NOW\(\)\s*,\s*INTERVAL\s+(\d+)\s+MINUTE\)",
        r"datetime('now', 'localtime', '-\1 minutes')",
        sql,
        flags=re.IGNORECASE
    )
    
    # 3. NOW() - INTERVAL 30 DAY -> datetime('now', 'localtime', '-30 days')
    sql = re.sub(
        r"NOW\(\)\s*-\s*INTERVAL\s+(\d+)\s+DAY",
        r"datetime('now', 'localtime', '-\1 days')",
        sql,
        flags=re.IGNORECASE
    )
    
    # 4. UTC_TIMESTAMP() -> datetime('now')
    sql = re.sub(r"\bUTC_TIMESTAMP\(\)", "datetime('now')", sql, flags=re.IGNORECASE)
    
    # 5. NOW() -> datetime('now', 'localtime')
    sql = re.sub(r"\bNOW\(\)", "datetime('now', 'localtime')", sql, flags=re.IGNORECASE)
    
    return sql


class SQLiteCursorWrapper:
    def __init__(self, sqlite_cursor):
        self.cursor = sqlite_cursor

    def execute(self, sql, params=None):
        translated_sql = translate_sql(sql)
        if params is None:
            return self.cursor.execute(translated_sql)
        else:
            return self.cursor.execute(translated_sql, params)

    def executemany(self, sql, data_list):
        translated_sql = translate_sql(sql)
        return self.cursor.executemany(translated_sql, data_list)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(r) for r in rows]

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def description(self):
        return self.cursor.description

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()


class SQLiteConnectionWrapper:
    def __init__(self, sqlite_conn):
        self.conn = sqlite_conn
        self.conn.row_factory = sqlite3.Row

    def cursor(self):
        return SQLiteCursorWrapper(self.conn.cursor())

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def initialize_sqlite_db(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qto_users'")
    if cur.fetchone():
        return
    
    # 1. qto_users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        role TEXT DEFAULT 'user',
        email_verified INTEGER DEFAULT 0,
        reset_token_hash TEXT,
        reset_token_expires_at TEXT,
        verification_token_hash TEXT,
        last_login_at TEXT,
        google_id TEXT,
        microsoft_id TEXT,
        extra_projects_allowance INTEGER DEFAULT 0,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. qto_subscriptions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        feature TEXT DEFAULT 'qto',
        plan_tier INTEGER DEFAULT 0,
        provider TEXT DEFAULT 'manual',
        provider_customer_id TEXT,
        provider_subscription_id TEXT,
        status TEXT DEFAULT 'inactive',

        current_period_start TEXT,
        current_period_end TEXT,
        cancel_at_period_end INTEGER DEFAULT 0,
        projects_used INTEGER DEFAULT 0,
        ai_calls_used INTEGER DEFAULT 0,
        exports_used INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 3. qto_projects
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        date TEXT,
        boq_data TEXT,
        status TEXT DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, name)
    );
    """)
    
    # 4. qto_usage_logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_usage_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        project_id INTEGER,
        event_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 5. qto_files
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        project_id INTEGER,
        original_name TEXT NOT NULL,
        storage_provider TEXT DEFAULT 'local',
        storage_key TEXT NOT NULL,
        content_type TEXT,
        size_bytes INTEGER DEFAULT 0,
        checksum_sha256 TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 6. qto_invoices
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subscription_id INTEGER,
        provider TEXT NOT NULL,
        provider_invoice_id TEXT,
        amount_aed REAL DEFAULT 0,
        currency TEXT DEFAULT 'AED',
        status TEXT DEFAULT 'draft',
        hosted_invoice_url TEXT,
        issued_at TEXT,
        paid_at TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 7. qto_audit_logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_user_id INTEGER,
        action TEXT NOT NULL,
        target_type TEXT,
        target_id TEXT,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 8. qto_deleted_accounts
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_deleted_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 8. qto_background_jobs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_background_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        project_id INTEGER,
        job_type TEXT NOT NULL,
        status TEXT DEFAULT 'queued',
        payload TEXT,
        result TEXT,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TEXT,
        finished_at TEXT
    );
    """)
    
    # 9. qto_market_prices
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_market_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        unit TEXT,
        rate_aed REAL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 10. qto_memory_rules
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_memory_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NULL,
        original_text TEXT NOT NULL,
        mapped_category TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. qto_agent_conversations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_agent_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        agent_role TEXT NOT NULL,
        sender TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 12. qto_customer_complaints
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_customer_complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        complaint_text TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 13. qto_project_feedback
    cur.execute("""
    CREATE TABLE IF NOT EXISTS qto_project_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tool_name TEXT NOT NULL,
        project_name TEXT NOT NULL,
        rating INTEGER NOT NULL,
        reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Seed admin user if none exists
    cur.execute("SELECT COUNT(*) FROM qto_users")
    count = cur.fetchone()[0]
    if count == 0:
        import bcrypt
        admin_emails = ["basel00omar.92@gmail.com", "basel.omar.qs@gmail.com", "admin@qto.com"]
        admin_password = os.environ.get("QTO_ADMIN_PASSWORD") or "Nodnod1606"
        hashed = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        for em in admin_emails:
            cur.execute(
                "INSERT INTO qto_users (email, password_hash, role) VALUES (?, ?, ?)",
                (em, hashed, "admin")
            )
        conn.commit()
        print("Local SQLite database seeded with admin users.")
        
        # Seed default prices
        try:
            from utils.market_prices_logic import DEFAULT_MATERIALS
            for m in DEFAULT_MATERIALS:
                for em in ["dubai", "abudhabi", "sharjah", "ajman"]:
                    rate = m[em]
                    em_name = "Abu Dhabi" if em == "abudhabi" else em.capitalize()
                    item_name = f"{m['name_en']} ({em_name})"
                    cur.execute(
                        "INSERT INTO qto_market_prices (item_name, unit, rate_aed) VALUES (?, ?, ?)",
                        (item_name, m["unit"], rate)
                    )
            conn.commit()
            print("Local SQLite database seeded with default market prices.")
        except Exception as ex:
            print(f"Could not seed market prices: {ex}")


_POOL = None

def get_pool():
    global _POOL
    if _POOL is None:
        import pymysql
        from dbutils.pooled_db import PooledDB
        kwargs = DbSettings.from_env().pymysql_kwargs()
        _POOL = PooledDB(
            creator=pymysql,
            maxconnections=15,
            mincached=2,
            maxcached=5,
            blocking=True,
            ping=1,
            **kwargs
        )
    return _POOL

_SQLITE_INITIALIZED = False

@contextmanager
def get_connection():
    """
    Context manager for safe database connections.
    Guarantees connection is closed even if an error occurs.

    Usage:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
    """
    global _SQLITE_INITIALIZED
    # SQLite Fallback check
    try:
        settings = DbSettings.from_env()
        use_sqlite = not settings.host
    except Exception:
        use_sqlite = True

    if use_sqlite:
        import sqlite3
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qto_local.db")
        conn = sqlite3.connect(db_path, timeout=60.0, check_same_thread=False)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        if not _SQLITE_INITIALIZED:
            initialize_sqlite_db(conn)
            _SQLITE_INITIALIZED = True
        wrapper = SQLiteConnectionWrapper(conn)
        try:
            yield wrapper
        finally:
            try:
                conn.close()
            except Exception:
                pass
    else:
        pool = get_pool()
        conn = pool.connection()
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass


def safe_query(sql: str, params=None) -> pd.DataFrame:
    """
    Executes a SELECT query safely and returns results as a pandas DataFrame.
    Always uses parameterized queries to prevent SQL injection.

    Args:
        sql: SQL query string with %s placeholders
        params: tuple of parameters to bind

    Returns:
        pd.DataFrame of results, or empty DataFrame on error
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall()
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except Exception as e:
        # Log the real error instead of silently returning "no rows" — an empty
        # DataFrame from a transient failure has caused bugs where users looked
        # unsubscribed / access was wrongly denied.
        logger.error("safe_query failed: %s | sql=%s", e, sql.strip().split("\n")[0][:200])
        return pd.DataFrame()


def safe_execute(sql: str, params=None, many=False, data_list=None) -> tuple:
    """
    Executes an INSERT/UPDATE/DELETE query safely with auto-commit.
    Always uses parameterized queries to prevent SQL injection.

    Args:
        sql: SQL statement with %s placeholders
        params: tuple of parameters (for single execution)
        many: if True, uses executemany with data_list
        data_list: list of tuples for batch execution

    Returns:
        (True, "OK") on success, (False, error_message) on failure
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if many and data_list:
                    cur.executemany(sql, data_list)
                else:
                    cur.execute(sql, params or ())
            conn.commit()
        return True, "OK"
    except Exception as e:
        logger.error("safe_execute failed: %s | sql=%s", e, sql.strip().split("\n")[0][:200])
        return False, str(e)


@contextmanager
def transaction():
    """Run several writes atomically — commits on success, rolls back on error.

    Usage:
        with transaction() as cur:
            cur.execute("UPDATE ...", (...))
            cur.execute("INSERT ...", (...))
    Either all statements land or none do.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            logger.exception("transaction rolled back")
            raise
        finally:
            try:
                cur.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Centralised active-project state writer
# ---------------------------------------------------------------------------
# Every endpoint that touches qto_active_projects.state_data MUST go through
# this helper so that:
#   1. state_json is always truncated to fit DB limits
#   2. INSERT vs UPDATE is handled universally (no dialect SQL)
#   3. Errors are logged with full context
# ---------------------------------------------------------------------------

_MAX_STATE_BYTES = 15 * 1024 * 1024  # 15 MB hard cap (TiDB JSON limit ~16 MB)


def _trim_state(state_data: dict) -> dict:
    """Aggressively trim heavy fields so state_json fits in the DB column."""
    import copy
    sd = copy.copy(state_data)  # shallow copy — mutate top-level keys only

    # Truncate per-page text arrays (only needed for classification, not extraction)
    for key in ("str_texts", "arch_texts"):
        if key in sd and isinstance(sd[key], list):
            sd[key] = [(t[:300] if isinstance(t, str) else t) for t in sd[key]]

    # Strip heavy fields from classified_pages
    if "classified_pages" in sd and isinstance(sd["classified_pages"], list):
        clean = []
        for p in sd["classified_pages"]:
            clean.append({
                "pdf": p.get("pdf", "structural"),
                "page_index": p.get("page_index", 0),
                "page_num": p.get("page_num", 1),
                "detected_type": p.get("detected_type", "unknown"),
                "confidence": p.get("confidence", "low"),
                "items": p.get("items", []),
            })
        sd["classified_pages"] = clean

    return sd


def upsert_active_state(user_id: int, project_id: int, step: int,
                         state_data: dict) -> tuple:
    """
    Single entry-point for writing to qto_active_projects.

    Returns (True, "OK") on success, (False, error_msg) on failure.
    """
    import json as _json

    trimmed = _trim_state(state_data)
    state_json = _json.dumps(trimmed, ensure_ascii=False, default=str)

    # Safety: if still too large, drop the heaviest key progressively
    for drop_key in ("str_texts", "arch_texts", "classified_pages",
                     "extraction_results", "confirmed_auto_data"):
        if len(state_json.encode("utf-8")) <= _MAX_STATE_BYTES:
            break
        if drop_key in trimmed:
            logger.warning("upsert_active_state: dropping '%s' (state too large)", drop_key)
            trimmed[drop_key] = [] if isinstance(trimmed.get(drop_key), list) else {}
            state_json = _json.dumps(trimmed, ensure_ascii=False, default=str)

    byte_size = len(state_json.encode("utf-8"))
    logger.info("upsert_active_state: project=%s step=%s size=%d bytes", project_id, step, byte_size)

    try:
        df = safe_query(
            "SELECT id FROM qto_active_projects WHERE user_id=%s AND project_id=%s",
            (user_id, project_id),
        )
        if df.empty:
            return safe_execute(
                "INSERT INTO qto_active_projects (user_id, project_id, current_step, state_data) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, project_id, step, state_json),
            )
        else:
            return safe_execute(
                "UPDATE qto_active_projects SET current_step=%s, state_data=%s "
                "WHERE user_id=%s AND project_id=%s",
                (step, state_json, user_id, project_id),
            )
    except Exception as e:
        logger.error("upsert_active_state FAILED: %s", e)
        return False, str(e)
