import pathlib


def test_plan_for_admin_is_unlimited():
    from utils.plans import get_plan_for_user

    plan = get_plan_for_user(1, role="admin")

    assert plan.projects > 1000
    assert plan.max_file_mb == 500


def test_check_file_size_blocks_large_file(monkeypatch):
    import utils.usage as usage
    from utils.plans import PlanLimits

    monkeypatch.setattr(
        usage,
        "get_plan_for_user",
        lambda user_id, role=None: PlanLimits(1, "Starter", 50, 1, 40, 5, 1),
    )

    ok, msg = usage.check_file_size({"id": 1, "role": "user"}, 2 * 1024 * 1024)

    assert ok is False
    assert "File exceeds" in msg


def test_check_limit_blocks_when_monthly_usage_exceeded(monkeypatch):
    import utils.usage as usage
    import utils.features as features
    from utils.plans import PlanLimits

    monkeypatch.setattr(
        usage,
        "get_plan_for_user",
        lambda user_id, role=None, feature="qto": PlanLimits(1, "Starter", 50, 1, 40, 5, 25),
    )
    monkeypatch.setattr(usage, "monthly_usage", lambda user_id, event_type, feature="qto": 1)
    # No unused add-on credits, so hitting the monthly base must block.
    monkeypatch.setattr(features, "extra_projects_for", lambda user_id, feature: 0)

    ok, msg = usage.check_limit({"id": 1, "role": "user"}, usage.EVENT_PROJECT)

    assert ok is False
    assert "limit" in msg.lower()


def test_check_limit_allows_when_addon_credit_available(monkeypatch):
    """One-time add-on credit lets the user create beyond the monthly base."""
    import utils.usage as usage
    import utils.features as features
    from utils.plans import PlanLimits

    monkeypatch.setattr(
        usage,
        "get_plan_for_user",
        lambda user_id, role=None, feature="qto": PlanLimits(1, "Starter", 50, 1, 40, 5, 25),
    )
    monkeypatch.setattr(usage, "monthly_usage", lambda user_id, event_type, feature="qto": 1)
    monkeypatch.setattr(features, "extra_projects_for", lambda user_id, feature: 2)

    ok, _ = usage.check_limit({"id": 1, "role": "user"}, usage.EVENT_PROJECT)

    assert ok is True


def test_local_storage_writes_file(monkeypatch, tmp_path):
    import utils.storage as storage

    monkeypatch.setenv("STORAGE_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(storage, "safe_execute", lambda *args, **kwargs: (True, "OK"))

    stored = storage.save_file(3, "drawing.pdf", b"abc", "application/pdf")

    path = tmp_path / stored.key
    assert stored.provider == "local"
    assert path.exists()
    assert path.read_bytes() == b"abc"
