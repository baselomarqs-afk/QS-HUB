def test_authenticate_user_uses_connection_context(monkeypatch):
    import sys
    import types

    streamlit_stub = types.SimpleNamespace(error=lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_stub)

    import ui.page_auth as auth

    class Cursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchone(self):
            return {"id": 1, "email": "admin@example.com", "password_hash": "hash", "role": "admin"}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class Conn:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(auth, "login_rate_limited", lambda email: False)
    monkeypatch.setattr(auth, "get_connection", lambda: Conn())
    monkeypatch.setattr(auth, "password_ok", lambda password, hashed: True)
    monkeypatch.setattr(auth, "touch_login", lambda user_id: None)
    monkeypatch.setattr(auth, "audit_log", lambda *args, **kwargs: None)

    user = auth.authenticate_user("admin@example.com", "password")

    assert user["role"] == "admin"
