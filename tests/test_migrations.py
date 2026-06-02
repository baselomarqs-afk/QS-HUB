def test_python_backfill_migration_has_apply():
    import importlib.util
    import pathlib

    path = pathlib.Path("migrations/002_backfill_existing_tables.py")
    spec = importlib.util.spec_from_file_location("migration_002", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert callable(module.apply)
