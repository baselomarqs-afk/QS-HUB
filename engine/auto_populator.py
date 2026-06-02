"""
يدمج نتائج AI Vision + OpenCV + OCR ويملأ المحرك تلقائياً
الأولوية: AI Vision > OCR > OpenCV > يدوي
"""
from typing import Dict, Any, List, Optional


def merge_floor_data(
    ai_result:  Optional[Dict],
    ocr_dims:   Optional[List],
    cv_summary: Optional[Dict],
    floor_key:  str,
) -> Dict[str, Any]:
    """
    يدمج مصادر البيانات الثلاث لطابق واحد
    Returns: dict جاهز لمدخلات المحرك
    """
    merged = {
        "floor_area":       None,
        "wet_area":         None,
        "wet_perimeter":    None,
        "dry_area":         None,
        "dry_perimeter":    None,
        "ext_perimeter":    None,
        "int_walls_length": None,
        "balcony_area":     None,
        "floor_height":     4.0,
        "slab_thickness":   0.20,
        "columns":          [],
        "beams":            [],
        "source":           {},
    }

    # ── Layer 1: OpenCV (lowest priority) ──
    if cv_summary:
        if cv_summary.get("total_area_m2"):
            merged["floor_area"]             = cv_summary["total_area_m2"]
            merged["source"]["floor_area"]   = "opencv"
        if cv_summary.get("total_perim_m"):
            merged["ext_perimeter"]          = cv_summary["total_perim_m"]
            merged["source"]["ext_perimeter"]= "opencv"
        if cv_summary.get("column_schedule"):
            merged["columns"] = [
                {
                    "label":    size,
                    "length_m": float(size.split("x")[0]),
                    "width_m":  float(size.split("x")[1]),
                    "count":    count,
                }
                for size, count in cv_summary["column_schedule"].items()
                if "x" in size
            ]
            merged["source"]["columns"] = "opencv"

    # ── Layer 2: OCR (medium priority) ──
    if ocr_dims:
        sorted_dims = sorted(ocr_dims, key=lambda d: d["value_meters"], reverse=True)
        large_dims  = [d for d in sorted_dims if d["value_meters"] > 3.0]

        if len(large_dims) >= 2 and not merged["floor_area"]:
            l1 = large_dims[0]["value_meters"]
            l2 = large_dims[1]["value_meters"]
            merged["floor_area"]           = round(l1 * l2, 2)
            merged["source"]["floor_area"] = "ocr_estimated"

    # ── Layer 3: AI Vision (highest priority) ──
    if ai_result and ai_result.get("_api_success"):
        field_map = {
            "total_floor_area_m2":          "floor_area",
            "external_perimeter_m":         "ext_perimeter",
            "internal_walls_total_length_m":"int_walls_length",
            "dry_area_m2":                  "dry_area",
            "dry_area_perimeter_m":         "dry_perimeter",
            "balcony_area_m2":              "balcony_area",
            "floor_height_m":               "floor_height",
            "slab_thickness_m":             "slab_thickness",
        }

        for ai_key, merged_key in field_map.items():
            val = ai_result.get(ai_key)
            if val is not None:
                merged[merged_key]           = float(val)
                merged["source"][merged_key] = "ai_vision"

        # Wet areas
        wet = ai_result.get("wet_areas") or {}
        if wet.get("total_area_m2") is not None:
            merged["wet_area"]           = float(wet["total_area_m2"])
            merged["source"]["wet_area"] = "ai_vision"
        if wet.get("total_perimeter_m") is not None:
            merged["wet_perimeter"]           = float(wet["total_perimeter_m"])
            merged["source"]["wet_perimeter"] = "ai_vision"

        # Columns from AI (override OpenCV)
        if ai_result.get("columns"):
            merged["columns"]           = ai_result["columns"]
            merged["source"]["columns"] = "ai_vision"

        # Beams from AI
        if ai_result.get("beams"):
            merged["beams"]           = ai_result["beams"]
            merged["source"]["beams"] = "ai_vision"

    # Derive missing dry_area
    if merged["floor_area"] and merged["wet_area"] and not merged["dry_area"]:
        merged["dry_area"] = round(
            float(merged["floor_area"]) - float(merged["wet_area"]), 2
        )

    return merged


def merge_substructure_data(
    ai_foundation:    Optional[Dict],
    manual_overrides: Optional[Dict] = None,
) -> Dict:
    """يدمج بيانات الأساسات من AI"""
    result = {
        "foundations":  [],
        "neck_columns": [],
        "tb_width":     0.30,
        "tb_depth":     0.50,
        "tb_length":    0.0,
    }

    if ai_foundation and ai_foundation.get("_api_success"):
        if ai_foundation.get("foundations"):
            result["foundations"] = [
                {
                    "label":  f"F{i+1}",
                    "width":  float(f.get("width_m", 0)),
                    "length": float(f.get("length_m", 0)),
                    "depth":  float(f.get("depth_m", 0.5)),
                    "count":  int(f.get("count", 1)),
                }
                for i, f in enumerate(ai_foundation["foundations"])
            ]

        tb = ai_foundation.get("tie_beam") or {}
        if tb:
            result["tb_width"]  = float(tb.get("width_m",       0.30) or 0.30)
            result["tb_depth"]  = float(tb.get("depth_m",       0.50) or 0.50)
            result["tb_length"] = float(tb.get("total_length_m", 0.0) or 0.0)

        # Neck columns from foundation column schedule
        if ai_foundation.get("columns"):
            result["neck_columns"] = [
                {
                    "label":  f"NC{i+1}",
                    "width":  float(c.get("width_m",  0.30)),
                    "length": float(c.get("length_m", 0.40)),
                    "count":  int(c.get("count",      1)),
                }
                for i, c in enumerate(ai_foundation["columns"])
            ]

    if manual_overrides:
        result.update(manual_overrides)

    return result


def _find_by_type_keyword(ai_results: Dict[str, Dict], keywords: List[str]) -> Optional[Dict]:
    for key, val in ai_results.items():
        key_lower = key.lower()
        if any(kw.lower() in key_lower for kw in keywords):
            return val
    return None


def build_auto_populated_state(
    ai_results: Dict[str, Dict],
    cv_summary: Optional[Dict],
    ocr_dims:   Optional[List],
    num_floors: int,
) -> Dict:
    """
    الدالة الرئيسية — تبني حالة كاملة للـ session state
    Returns: dict with auto_{fk} per floor + auto_substructure
    """
    floor_map = {
        "Ground Floor": "gf",
        "First Floor":  "f1",
        "Second Floor": "f2",
        "Roof":         "roof",
        "Foundation":   "foundation",
    }

    floor_keywords = {
        "Ground Floor": ["ground_floor_plan", "ground_columns", "ground floor"],
        "First Floor":  ["first_floor_plan", "slab_1f", "slab_1st", "first floor"],
        "Second Floor": ["second_floor_plan", "slab_2f", "slab_2nd", "second floor"],
        "Roof":         ["roof_floor_plan", "roof_slab", "roof"],
        "Foundation":   ["foundation", "foundations"],
    }

    state      = {}
    floor_keys = ["gf", "f1", "f2"][:num_floors]

    for floor_name, floor_key in floor_map.items():
        if floor_key not in floor_keys and floor_key not in ["roof", "foundation"]:
            continue
        keywords = floor_keywords.get(floor_name, [])
        ai_floor = _find_by_type_keyword(ai_results, keywords)
        merged           = merge_floor_data(ai_floor, ocr_dims, cv_summary, floor_key)
        state[f"auto_{floor_key}"] = merged

    # Sub-Structure / Foundation
    ai_foundation          = _find_by_type_keyword(ai_results, floor_keywords["Foundation"])
    state["auto_substructure"] = merge_substructure_data(ai_foundation)

    return state
