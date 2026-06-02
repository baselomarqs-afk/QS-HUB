"""Production observability setup."""
from __future__ import annotations

from utils.settings import get_setting


def init_observability() -> None:
    dsn = get_setting("SENTRY_DSN")
    if not dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
    except Exception:
        pass
