"""
Tests for engine/item_calculator.py — the calculation engine used by the
React + FastAPI PRODUCTION path (via engine/project_boq_bridge.py).

tests/test_engine.py covers the parallel substructure/superstructure engine
(the Streamlit path). Before this file, the API engine had no dedicated tests,
so the production calculation path was effectively unverified. These tests pin
calculate_item() against the same reference scenarios used in test_engine.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.item_calculator import calculate_item


def _approx(a, b, tol=0.01):
    return a is not None and abs(a - b) < tol


# ── Sub-structure ──────────────────────────────────────────────────
def test_excavation():
    q = calculate_item("excavation", {"longest_length": 22.0, "longest_width": 18.0, "excavation_depth": 1.25})
    assert _approx(q, 600.0), q  # (22+2)(18+2)(1.25)


def test_foundation_concrete():
    inp = {"foundations_schedule": [
        {"length_m": 1.5, "width_m": 1.5, "depth_m": 0.5, "count": 12},
        {"length_m": 1.2, "width_m": 1.2, "depth_m": 0.5, "count": 8},
    ]}
    assert _approx(calculate_item("foundation_concrete", inp), 19.26)


def test_foundation_pcc():
    inp = {"foundations_schedule": [
        {"length_m": 1.5, "width_m": 1.5, "depth_m": 0.5, "count": 12},
        {"length_m": 1.2, "width_m": 1.2, "depth_m": 0.5, "count": 8},
    ]}
    assert _approx(calculate_item("foundation_pcc", inp), 5.036)


def test_foundation_bitumen():
    inp = {"foundations_schedule": [{"length_m": 1.5, "width_m": 1.5, "depth_m": 0.5, "count": 12}]}
    assert _approx(calculate_item("foundation_bitumen", inp), 63.0)


def test_neck_column_concrete():
    inp = {"neck_columns_schedule": [{"length_m": 0.40, "width_m": 0.30, "count": 12}]}
    assert _approx(calculate_item("neck_column_concrete", inp), 1.44)


def test_tie_beam_concrete():
    inp = {"tb_width": 0.30, "tb_depth": 0.50, "tb_total_length": 200.0}
    assert _approx(calculate_item("tie_beam_concrete", inp), 30.0)


def test_tie_beam_pcc():
    assert _approx(calculate_item("tie_beam_pcc", {"tb_width": 0.30, "tb_total_length": 200.0}), 10.0)


def test_tie_beam_bitumen():
    assert _approx(calculate_item("tie_beam_bitumen", {"tb_total_length": 200.0, "tb_depth": 0.50}), 200.0)


def test_slab_on_grade():
    assert _approx(calculate_item("slab_on_grade", {"gf_area": 350.0}), 35.0)  # 350 × 0.10


def test_solid_block_work():
    assert _approx(calculate_item("solid_block_work", {"external_perimeter": 80.0, "block_thickness": 1.0}), 72.0)


def test_block_work_bitumen():
    assert _approx(calculate_item("block_work_bitumen", {"external_perimeter": 80.0}), 160.0)


def test_road_base():
    assert _approx(calculate_item("road_base", {"longest_length": 22.0, "longest_width": 18.0}), 99.0)


def test_anti_termite_found():
    assert _approx(calculate_item("anti_termite_found", {"longest_length": 22.0, "longest_width": 18.0}), 396.0)


# ── Super-structure ────────────────────────────────────────────────
def test_parapet_concrete():
    assert _approx(calculate_item("parapet_concrete", {"roof_perimeter": 80.0}), 3.2)


def test_slab_concrete_floor():
    assert _approx(calculate_item("slab_concrete_1st", {"slab_area": 300.0, "slab_thickness": 0.20}), 60.0)


def test_beam_concrete_floor():
    inp = {"beams_schedule": [
        {"length_m": 5.0, "width_m": 0.30, "depth_m": 0.50, "count": 1},
        {"length_m": 4.5, "width_m": 0.30, "depth_m": 0.50, "count": 1},
    ]}
    assert _approx(calculate_item("beam_concrete_1st", inp), 1.425)


def test_columns_floor():
    inp = {"columns_schedule": [{"length_m": 0.40, "width_m": 0.30, "count": 12}]}
    assert _approx(calculate_item("col_gf_to_1st", inp), 5.76)  # height 4.0


def test_staircase():
    assert _approx(calculate_item("staircase_1st", {"structural_levels": 2}), 10.4)


# ── Finishes (per-floor pattern) ───────────────────────────────────
def test_thermal_block():
    assert _approx(calculate_item("thermal_block_gf", {"ext_perimeter": 80.0, "floor_height": 4.0}), 320.0)


def test_internal_block():
    assert _approx(calculate_item("internal_block_gf", {"int_walls_length": 110.0, "floor_height": 4.0}), 440.0)


# ── Openings ───────────────────────────────────────────────────────
def test_doors():
    assert calculate_item("door_openings", {"doors_schedule": [{"count": 5}, {"count": 3}, {"count": 2}]}) == 10.0


def test_windows():
    inp = {"windows_schedule": [{"width_m": 1.2, "height_m": 1.5, "count": 4}]}
    assert _approx(calculate_item("window_openings", inp), 7.2)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
