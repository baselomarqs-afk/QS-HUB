"""Regression tests for:
1. Accurate general-purpose architectural & structural page classification
   (rejecting notes/regulations/boundary-wall/typical-details, separating tie-beam
   vs column layouts, floor plans vs elevations/sections).
2. Strict opening mark extraction (zero false English words like AND/BED/NEW/REV/WWW,
   accurate schedule detection, multi-floor double-height panel deduplication).
3. QS Golden Rule for Internal Plaster:
   Internal Plaster = max(Thermal Block + 2 * (Internal Block 20cm + 10cm), Internal Paint + Wall Tiles).
"""
import fitz

from engine.item_calculator import calculate_item
from workflow.step2_classify import _classify_single
from workflow.openings_counter import extract_openings, _MARK_RE, _is_window_mark


# ── 1. Classification tests ──────────────────────────────────────────────────

def test_classify_rejects_regulations_notes_and_boundary_wall():
    dense_notes = "DUBAI GREEN BUILDING REGULATIONS AND SPECIFICATIONS. " * 200
    assert _classify_single(dense_notes, "architectural")["detected_type"] == "unknown"

    area_sheet = "AREA CALCULATION PROPOSED VILLA GROUND FLOOR 203.00 SQ.M2 FIRST FLOOR 203.00 SQ.M2"
    assert _classify_single(area_sheet, "architectural")["detected_type"] == "unknown"

    bw_str = "BOUNDARY WALL LAYOUT SCHEDULE OF FOOTINGS SCHEDULE OF BEAMS/TIE BEAMS TYPICAL IN BOUNDARY WALL"
    assert _classify_single(bw_str, "structural")["detected_type"] == "unknown"

    rebar_detail = "TYPICAL ARRANGEMENT OF CONTINUOUS BEAM CANTILEVER SLAB BEAM REINF AS/SCHD"
    assert _classify_single(rebar_detail, "structural")["detected_type"] == "unknown"

    stair_str = "STAIR CASE LAYOUT B1 WITH STAIR SECTION 1-1 FROM TIE BEAM TO LANDING LVL"
    assert _classify_single(stair_str, "structural")["detected_type"] == "unknown"


def test_classify_structural_distinguishes_columns_tie_beam_footings_slabs():
    assert _classify_single("%%UCOLUMN AXIS LAYOUT UPTO TIE BEAM COLUMN LAYOUT", "structural")["detected_type"] == "neck_columns"
    assert _classify_single("%%UCOLUMN AXIS LAYOUT TIE BEAM TO F.FLOOR COLUMN LAYOUT", "structural")["detected_type"] == "columns_1f"
    assert _classify_single("%%UCOLUMN AXIS LAYOUT F.FLOOR TO ROOF SLAB COLUMN LAYOUT", "structural")["detected_type"] == "columns_roof"
    assert _classify_single("%%UFOOTING AXIS LAYOUT FOOTING AS PER SCHEDULE COLUMN", "structural")["detected_type"] == "foundations"
    assert _classify_single("TIE BEAM COLUMN LAYOUT %%UTIE BEAM LAYOUT FOOTING AS PER SCHEDULE", "structural")["detected_type"] == "tie_beam"
    assert _classify_single("F.FLOOR SLAB LAYOUT SCHEDULE FOR SLAB SCHEDULE FOR SIMPLE AND CONTIONOUS BEAMS", "structural")["detected_type"] == "slab_1st"
    assert _classify_single("ROOF SLAB LAYOUT SCHEDULE FOR SLAB", "structural")["detected_type"] == "roof_slab"


def test_classify_architectural_floor_plans_vs_elevations_and_schedules():
    # Floor plan with exterior elevation arrows MUST NOT be misclassified as elevations
    gf_plan = "GROUND FLOOR PLAN FRONT ELEVATION REAR ELEVATION LEFT ELEVATION RIGHT ELEVATION LIVING MAJLIS KITCHEN BATH D2 D3 W1 W2"
    res_gf = _classify_single(gf_plan, "architectural")
    assert res_gf["detected_type"] == "ground_floor_plan"
    assert res_gf["confidence"] == "high"

    # Section with 4 stacked vertical levels + room names inside section MUST be elevations
    section = "01 GROUND FLOOR F.F.L +0.60 02 FIRST FLOOR F.F.L +5.08 03 TOP ROOF F.F.L +9.56 PARPET LEVE +10.76 LIVING AREA BEDROOM MAJLIS BATH KITCHEN"
    res_sec = _classify_single(section, "architectural")
    assert res_sec["detected_type"] == "elevations"
    assert res_sec["confidence"] == "high"

    # Elevation-style schedule without 'W x H' strings
    sched = "MAIN DOOR - 01 DOOR - 02 DOOR - 03 PANEL - 01 PANEL - 02 WINDOW - 01 WINDOW - 02"
    res_sch = _classify_single(sched, "architectural")
    assert res_sch["detected_type"] == "schedules"
    assert res_sch["confidence"] == "high"


# ── 2. Openings counter tests ────────────────────────────────────────────────

def test_openings_mark_regex_rejects_english_words_and_matches_real_marks():
    garbage = "AND AND4 BED CAD CBD CTV DCV GOV MW NEW PAD REV ROD TLV UV VOW WWW D W V 1.50 A107"
    assert _MARK_RE.findall(garbage) == []

    real = "MD1 D2 D-03 W1 W-06 CW1 SW2 V1"
    found = [(a.upper(), b) for a, b in _MARK_RE.findall(real)]
    assert found == [
        ("MD", "1"), ("D", "2"), ("D", "3"),
        ("W", "1"), ("W", "6"), ("CW", "1"), ("SW", "2"), ("V", "1"),
    ]
    assert _is_window_mark("W1") is True
    assert _is_window_mark("CW1") is True
    assert _is_window_mark("SW2") is True
    assert _is_window_mark("P1") is True
    assert _is_window_mark("D2") is False
    assert _is_window_mark("MD1") is False


def test_openings_counter_excludes_notes_and_deduplicates_double_height_panels(tmp_path):
    pdf_path = tmp_path / "villa_arch.pdf"
    doc = fitz.open()

    # Page 0: Dense Dubai Green Building Regulations full of "AND", "BED", "REV"
    p0 = doc.new_page()
    p0.insert_text((40, 40), ("AND BED NEW REV WWW D W V " * 400), fontsize=6)

    # Page 1: Ground Floor Plan (MD1, 2x D2, 2x W1, 2x P2)
    p1 = doc.new_page()
    p1.insert_text((40, 40), "GROUND FLOOR PLAN LIVING MAJLIS KITCHEN BATH MD1 D2 D2 W1 W1 P2 P2", fontsize=10)

    # Page 2: First Floor Plan (3x D2, 2x W1, same 2x double-height P2)
    p2 = doc.new_page()
    p2.insert_text((40, 40), "FIRST FLOOR PLAN MASTER BEDROOM BATH DRESSING D2 D2 D2 W1 W1 P2 P2", fontsize=10)

    # Page 3: Schedule with explicit sizes including double-height P2 (2.50 x 7.77)
    p3 = doc.new_page()
    p3.insert_text((40, 40), "DOOR & WINDOW SCHEDULE\nW1 1.50 X 2.00\nP2 PANEL - 02 2.50 X 7.77\nD2 1.00 X 2.20\nMD1 1.80 X 2.40", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()

    res = extract_openings(str(pdf_path), use_vision=False)
    assert res is not None
    # Notes page 0 must be excluded
    assert 0 not in res["_pages"]["count_pages"]
    assert res["_pages"]["schedule_pages"] == [3]

    doors = {d["mark"]: d["count"] for d in res["doors"]}
    assert doors == {"D2": 5, "MD1": 1}
    assert res["totals"]["door_count"] == 6

    wins = {w["mark"]: w for w in res["windows"]}
    assert wins["W1"]["count"] == 4
    # Double-height P2 (7.77m > 5.0m) appeared 2x on GF and 2x on 1F -> deduplicated to 2 (NOT 4!)
    assert wins["P2"]["count"] == 2
    assert wins["P2"]["count_source"] == "plan_label_count_multifloor"
    expected_area = round(4 * 1.5 * 2.0 + 2 * 2.5 * 7.77, 2)
    assert res["totals"]["window_area"] == expected_area


# ── 3. Internal Plaster QS Golden Rule tests ─────────────────────────────────

def test_internal_plaster_equals_thermal_plus_2x_internal_block_and_never_below_paint_plus_tiles():
    # Case A: Normal well-balanced villa floor
    inp_normal = {
        "ext_perimeter": 60.0,
        "floor_height": 4.48,
        "int_walls_20cm": 50.0,
        "int_walls_10cm": 15.0,
        "dry_perimeter": 128.0,
        "wet_perimeter": 44.0,
        "windows_deduction": 40.0,
        "doors_deduction_count": 9.0,  # 9 real doors -> 18 m2
    }
    thermal = calculate_item("thermal_block_gf", inp_normal)
    blk20 = calculate_item("internal_block_gf", inp_normal)
    blk10 = calculate_item("internal_block_10_gf", inp_normal)
    paint = calculate_item("int_paint_gf", inp_normal)
    tiles = calculate_item("wall_tiles_gf", inp_normal)
    plaster = calculate_item("int_plaster_gf", inp_normal)

    assert abs(plaster - round(thermal + 2.0 * (blk20 + blk10), 2)) < 0.05
    assert plaster >= round(paint + tiles, 2)

    # Case B: Even if internal wall length is under-measured, plaster NEVER falls below paint + wall_tiles
    inp_under_walls = {
        "ext_perimeter": 50.0,
        "floor_height": 4.0,
        "int_walls_20cm": 10.0,
        "int_walls_10cm": 0.0,
        "dry_perimeter": 120.0,
        "wet_perimeter": 40.0,
        "windows_deduction": 10.0,
        "doors_deduction_count": 8.0,
    }
    paint_b = calculate_item("int_paint_gf", inp_under_walls)
    tiles_b = calculate_item("wall_tiles_gf", inp_under_walls)
    plaster_b = calculate_item("int_plaster_gf", inp_under_walls)
    assert plaster_b >= round(paint_b + tiles_b, 2)
