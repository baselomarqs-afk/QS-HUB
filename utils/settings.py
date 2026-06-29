"""
Production settings loader.

Secrets must come from environment variables (or .env file via python-dotenv).
This module keeps the rest of the codebase away from hard-coded credentials.
"""
from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass
from typing import Any


def _st_secret(name: str, default: str | None = None) -> str | None:
    """Legacy fallback — now all secrets come from environment variables / .env file."""
    return os.environ.get(name, default)


def get_setting(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return str(value).strip().strip("'").strip('"') if value is not None else ""


def get_int_setting(name: str, default: int) -> int:
    raw = get_setting(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class DbSettings:
    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DbSettings":
        host = get_setting("TIDB_HOST", get_setting("DB_HOST", ""), required=False)
        if not host:
            return cls(host="", port=4000, user="", password="", database="local")
        return cls(
            host=host,
            port=get_int_setting("TIDB_PORT", get_int_setting("DB_PORT", 4000)),
            user=get_setting("TIDB_USER", get_setting("DB_USER", ""), required=True),
            password=get_setting("TIDB_PASSWORD", get_setting("DB_PASSWORD", ""), required=True),
            database=get_setting("TIDB_DATABASE", get_setting("DB_NAME", "test"), required=True),
        )

    def pymysql_kwargs(self) -> dict[str, Any]:
        import pymysql

        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
            "cursorclass": pymysql.cursors.DictCursor,
        }


def app_base_url() -> str:
    return get_setting("APP_BASE_URL", "http://localhost:8501").rstrip("/")
