import pandas as pd


def test_login_rate_limit_counts_matching_email(monkeypatch):
    import utils.security as security

    monkeypatch.setattr(
        security,
        "safe_query",
        lambda *args, **kwargs: pd.DataFrame(
            [
                {"metadata": '{"email":"a@example.com"}'},
                {"metadata": '{"email":"A@example.com"}'},
                {"metadata": '{"email":"b@example.com"}'},
            ]
        ),
    )

    assert security.login_rate_limited("a@example.com", max_attempts=2) is True
    assert security.login_rate_limited("b@example.com", max_attempts=2) is False


def test_enqueue_job_returns_lastrowid(monkeypatch):
    import utils.jobs as jobs

    class Cursor:
        lastrowid = 42

        def execute(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class Conn:
        def cursor(self):
            return Cursor()

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(jobs, "get_connection", lambda: Conn())

    assert jobs.enqueue_job("pdf_extraction", {"file": "x.pdf"}, user_id=1) == 42
