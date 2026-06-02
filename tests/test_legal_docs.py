import pathlib


def test_legal_docs_exist_and_are_not_empty():
    legal_dir = pathlib.Path("legal")
    required = [
        "TERMS_OF_USE_AR.md",
        "PRIVACY_POLICY_AR.md",
        "REFUND_POLICY_AR.md",
        "DATA_RETENTION_AR.md",
        "ENGINEERING_DISCLAIMER_AR.md",
        "TERMS_OF_USE_EN.md",
        "PRIVACY_POLICY_EN.md",
        "REFUND_POLICY_EN.md",
        "DATA_RETENTION_EN.md",
        "ENGINEERING_DISCLAIMER_EN.md",
    ]
    for name in required:
        text = (legal_dir / name).read_text(encoding="utf-8")
        assert len(text.strip()) > 200
