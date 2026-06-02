"""Production readiness checks for deployment gates."""
from __future__ import annotations

import os
import pathlib
import re
import sys


REQUIRED_ENV = [
    "TIDB_HOST",
    "TIDB_USER",
    "TIDB_PASSWORD",
    "TIDB_DATABASE",
    "APP_BASE_URL",
    "DODO_ENVIRONMENT",
    "DODO_PAYMENTS_API_KEY",
    "DODO_WEBHOOK_SECRET",
    "DODO_PRODUCT_TIER_1",
    "DODO_PRODUCT_TIER_2",
    "DODO_PRODUCT_TIER_3",
    "DODO_PRODUCT_TIER_4",
]


SECRET_PATTERNS = [
    re.compile(r"AIzaSy[A-Za-z0-9_-]{20,}"),
    re.compile(r"sk_live_[A-Za-z0-9_]+"),
    re.compile(r"pdl_live_[A-Za-z0-9_]+"),
    re.compile(r"SQUBg|Nodnod|gateway01"),
]

SKIP_DIRS = {".git", "scratch", "_dev_scripts", "__pycache__", ".pytest_cache", ".qto_cache", ".gemini_cache", "tmp"}
SKIP_FILES = {"production_readiness.py", "ci.yml"}


def check_env() -> list[str]:
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    return [f"Missing env: {name}" for name in missing]


def check_files() -> list[str]:
    errors = []
    required = [
        "Dockerfile",
        "docker-compose.yml",
        "migrations/001_saas_schema.sql",
        "payment_webhook_app.py",
        "worker.py",
        "PRODUCTION_CHECKLIST.md",
        "SECURITY.md",
        "LEGAL_DISCLAIMER.md",
    ]
    for path in required:
        if not pathlib.Path(path).exists():
            errors.append(f"Missing file: {path}")
    return errors


def check_secret_leaks() -> list[str]:
    errors = []
    for path in pathlib.Path(".").rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == ".env" or path.name in SKIP_FILES or not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".toml", ".yml", ".yaml", ".sql", ".example", ""}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"Potential secret leak in {path}")
                break
    return errors


def main() -> int:
    errors = []
    errors.extend(check_files())
    errors.extend(check_secret_leaks())
    if os.environ.get("QTO_STRICT_READINESS") == "1":
        errors.extend(check_env())

    if errors:
        print("Production readiness: FAILED")
        for err in errors:
            print(f"- {err}")
        return 1
    print("Production readiness: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
