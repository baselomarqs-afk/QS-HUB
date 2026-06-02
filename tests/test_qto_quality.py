import pandas as pd


def test_quality_report_scores_high_when_clean():
    from utils.qto_quality import score_boq_quality

    df = pd.DataFrame(
        [
            {"_is_header": False, "Description (English)": "Concrete", "Quantity": 10},
            {"_is_header": False, "Description (English)": "Block", "Quantity": 20},
        ]
    )

    quality = score_boq_quality(df, {})

    assert quality["score"] == 100
    assert quality["confidence"] == "high"


def test_quality_report_flags_missing_inputs():
    from utils.qto_quality import score_boq_quality

    df = pd.DataFrame([{"_is_header": False, "Description (English)": "Concrete", "Quantity": 0}])

    quality = score_boq_quality(df, {"needs_input": ["foundation schedule"]})

    assert quality["score"] < 80
    assert quality["confidence"] in {"low", "blocked"}
    assert any(f.severity == "critical" for f in quality["findings"])
