"""Run database migrations for THE QS HUB."""
from __future__ import annotations

import pathlib
import importlib.util

from utils.db import get_connection


ROOT = pathlib.Path(__file__).resolve().parent
MIGRATIONS = ROOT / "migrations"


def _split_sql(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).rstrip(";"))
            current = []
    if current:
        statements.append("\n".join(current))
    return statements


def run_migrations() -> None:
    files = sorted(list(MIGRATIONS.glob("*.sql")) + list(MIGRATIONS.glob("*.py")))
    if not files:
        print("No migrations found.")
        return

    with get_connection() as conn:
        for path in files:
            if path.suffix == ".py":
                spec = importlib.util.spec_from_file_location(path.stem, path)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"Could not load migration {path.name}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.apply(conn)
                print(f"Applied {path.name}")
                continue
            with conn.cursor() as cur:
                sql = path.read_text(encoding="utf-8")
                for statement in _split_sql(sql):
                    cur.execute(statement)
                print(f"Applied {path.name}")
            conn.commit()


if __name__ == "__main__":
    run_migrations()
