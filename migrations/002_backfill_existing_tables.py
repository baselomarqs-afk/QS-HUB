"""Idempotent schema backfill for databases created before SaaS hardening."""
from __future__ import annotations


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    return int(cur.fetchone()["count"]) > 0


def _index_exists(cur, table: str, index_name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) AS count
        FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND INDEX_NAME = %s
        """,
        (table, index_name),
    )
    return int(cur.fetchone()["count"]) > 0


def _add_column(cur, table: str, column: str, ddl: str) -> None:
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _add_index(cur, table: str, index_name: str, ddl: str) -> None:
    if not _index_exists(cur, table, index_name):
        cur.execute(f"ALTER TABLE {table} ADD {ddl}")


def apply(conn) -> None:
    with conn.cursor() as cur:
        _add_column(cur, "qto_users", "email_verified", "email_verified TINYINT(1) DEFAULT 0")
        _add_column(cur, "qto_users", "reset_token_hash", "reset_token_hash VARCHAR(255)")
        _add_column(cur, "qto_users", "reset_token_expires_at", "reset_token_expires_at DATETIME")
        _add_column(cur, "qto_users", "verification_token_hash", "verification_token_hash VARCHAR(255)")
        _add_column(cur, "qto_users", "last_login_at", "last_login_at DATETIME")
        _add_column(cur, "qto_users", "updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")

        _add_column(cur, "qto_subscriptions", "provider", "provider VARCHAR(50) DEFAULT 'manual'")
        _add_column(cur, "qto_subscriptions", "provider_customer_id", "provider_customer_id VARCHAR(255)")
        _add_column(cur, "qto_subscriptions", "provider_subscription_id", "provider_subscription_id VARCHAR(255)")
        _add_column(cur, "qto_subscriptions", "current_period_start", "current_period_start DATETIME")
        _add_column(cur, "qto_subscriptions", "current_period_end", "current_period_end DATETIME")
        _add_column(cur, "qto_subscriptions", "cancel_at_period_end", "cancel_at_period_end TINYINT(1) DEFAULT 0")
        _add_column(cur, "qto_subscriptions", "ai_calls_used", "ai_calls_used INT DEFAULT 0")
        _add_column(cur, "qto_subscriptions", "exports_used", "exports_used INT DEFAULT 0")
        _add_column(cur, "qto_subscriptions", "created_at", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column(cur, "qto_subscriptions", "updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        _add_index(cur, "qto_subscriptions", "idx_sub_user", "INDEX idx_sub_user (user_id)")
        _add_index(cur, "qto_subscriptions", "idx_sub_provider", "INDEX idx_sub_provider (provider, provider_subscription_id)")

        _add_column(cur, "qto_projects", "user_id", "user_id INT NOT NULL DEFAULT 0")
        _add_column(cur, "qto_projects", "status", "status VARCHAR(50) DEFAULT 'completed'")
        _add_column(cur, "qto_projects", "created_at", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column(cur, "qto_projects", "updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        _add_index(cur, "qto_projects", "idx_project_user", "INDEX idx_project_user (user_id)")

    conn.commit()
