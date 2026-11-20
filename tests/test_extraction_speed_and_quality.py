"""Tests for extraction performance improvements that preserve full QTO accuracy."""
import asyncio
import time
import fitz
import pytest

from utils.key_manager import KeyManager, ROTATION_MODELS
from pdf_engine.table_extractor import extract_tables_as_csv
from pdf_engine.vector_intelligence import calibrate_scale_from_dimensions
from workflow.step3_extract import _detect_image_mime, _ask_ai_with_retry


def test_key_manager_rotates_all_keys_on_top_accuracy_model_first():
    keys = [f"KEY_{i}" for i in range(1, 6)]
    mgr = KeyManager(keys)

    # First 5 calls must spread across all 5 keys on the #1 full Flash model
    first_round = [mgr.get_key_and_model() for _ in range(5)]
    assert [k for k, _ in first_round] == keys
    assert all(m == ROTATION_MODELS[0] for _, m in first_round)

    # Next 5 calls must spread across all 5 keys on the #2 full Flash model
    second_round = [mgr.get_key_and_model() for _ in range(5)]
    assert [k for k, _ in second_round] == keys
    assert all(m == ROTATION_MODELS[1] for _, m in second_round)

    # Top accuracy fast models come first; slow backup 3.6-flash stays last; 404 model excluded
    assert ROTATION_MODELS[0] == "gemini-2.5-flash"
    assert ROTATION_MODELS[1] == "gemini-3-flash-preview"
    assert ROTATION_MODELS[-1] == "gemini-3.6-flash"
    assert "gemini-2.5-flash-lite" not in ROTATION_MODELS


def test_key_manager_mark_model_unavailable_skips_404_model():
    mgr = KeyManager(["KEY_A", "KEY_B"])
    mgr.mark_model_unavailable("gemini-2.5-flash")
    k, m = mgr.get_key_and_model()
    assert m == "gemini-3-flash-preview"
    assert k == "KEY_A"


def test_table_extractor_extracts_table_fast_with_pymupdf(tmp_path):
    pdf_path = tmp_path / "door_schedule.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)

    # Draw a 3x3 grid table with door schedule values
    xs = [50, 150, 270, 400]
    ys = [50, 80, 110, 140]
    for x in xs:
        page.draw_line((x, ys[0]), (x, ys[-1]))
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))

    rows = [
        ["MARK", "SIZE", "QTY"],
        ["D1", "1000x2100", "4"],
        ["D2", "900x2100", "8"],
    ]
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            page.insert_text((xs[c_i] + 8, ys[r_i] + 20), val, fontsize=10)
    doc.save(str(pdf_path))
    doc.close()

    csv_out = extract_tables_as_csv(str(pdf_path), 0)
    assert "D1" in csv_out
    assert "1000x2100" in csv_out
    assert "D2" in csv_out


def test_table_extractor_does_not_hang_on_dense_cad_page(tmp_path):
    pdf_path = tmp_path / "dense_cad_schedule.pdf"
    doc = fitz.open()
    page = doc.new_page(width=800, height=600)

    # Simulate a dense CAD sheet with 2,500 short hatch/symbol lines (> 1500 threshold)
    shape = page.new_shape()
    for i in range(2500):
        x = 50 + (i % 100) * 6
        y = 50 + (i // 100) * 18
        shape.draw_line((x, y), (x + 4, y + 4))
    shape.finish(width=0.5)
    shape.commit()
    page.insert_text((100, 500), "D1 1000x2100 QTY 5", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()

    t0 = time.perf_counter()
    extract_tables_as_csv(str(pdf_path), 0)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0


def test_spatial_grid_scale_calibration_matches_expected_1_to_100(tmp_path):
    pdf_path = tmp_path / "scale_test.pdf"
    doc = fitz.open()
    page = doc.new_page(width=842, height=595)
    # At 1:100, 1 metre = 72 / 25.4 * 10 = 28.3465 pt; 5.0m = 141.73 pt
    # calibrate_scale_from_dimensions requires >= 8 vector segments
    pt_5m = 5.0 * (72.0 / 25.4) * 10.0
    for idx in range(8):
        y = 60 + idx * 60
        page.draw_line((100, y), (100 + pt_5m, y))
        page.insert_text((100 + pt_5m / 2 - 10, y - 6), "5000", fontsize=10)
    doc.save(str(pdf_path))

    cal = calibrate_scale_from_dimensions(doc[0])
    doc.close()
    assert cal is not None
    assert cal["ratio"] == 100


def test_detect_image_mime():
    assert _detect_image_mime(b"\xff\xd8\xff\xe0test") == "image/jpeg"
    assert _detect_image_mime(b"\x89PNG\r\n\x1a\ntest") == "image/png"


def test_ask_ai_with_retry_runs_truly_concurrently(monkeypatch, tmp_path):
    """Verify asyncio.gather actually overlaps Gemini network calls across worker threads."""
    import google.genai as genai_mod

    class _DummyResp:
        text = '{"ok": true}'

    class _DummyModels:
        def generate_content(self, model, contents):
            time.sleep(0.25)
            return _DummyResp()

    class _DummyClient:
        def __init__(self, **kwargs):
            self.models = _DummyModels()

    monkeypatch.setattr(genai_mod, "Client", _DummyClient)
    mgr = KeyManager(["K1", "K2", "K3"])

    async def _run():
        t0 = time.perf_counter()
        res = await asyncio.gather(
            _ask_ai_with_retry(b"\xff\xd8a", "p1", mgr, force_reextract=True),
            _ask_ai_with_retry(b"\xff\xd8b", "p2", mgr, force_reextract=True),
            _ask_ai_with_retry(b"\xff\xd8c", "p3", mgr, force_reextract=True),
        )
        return res, time.perf_counter() - t0

    res, elapsed = asyncio.run(_run())
    assert len(res) == 3
    # 3 × 0.25s sequentially would be >= 0.75s; concurrently it completes in ~0.25-0.45s
    assert elapsed < 0.65
