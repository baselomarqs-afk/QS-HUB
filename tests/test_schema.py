import pathlib


def test_saas_schema_contains_required_tables():
    sql = pathlib.Path("migrations/001_saas_schema.sql").read_text(encoding="utf-8")

    for table in [
        "qto_users",
        "qto_subscriptions",
        "qto_projects",
        "qto_usage_logs",
        "qto_files",
        "qto_invoices",
        "qto_audit_logs",
        "qto_background_jobs",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
