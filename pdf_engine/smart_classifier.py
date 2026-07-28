"""
التصنيف الذكي للصفحات بناءً على محتواها
"""
from typing import Dict, List

PAGE_ITEMS_MAP = {
    "foundations": {
        "drawing_keywords": [
            "foundation", "footing", "أساس", "FOUNDATION", "SUB-STRUCTURE", "SUB STRUCTURE",
            "SCHEDULE OF FOOTINGS", "FOOTING DETAILS", "FOOTING SCHEDULE", "FOUNDATION PLAN",
            "FOUNDATION & TIE BEAM", "SCHEDULE OF FOUNDATION", "FOOTINGS PLAN", "F.1", "CF.1"
        ],
        "pdf_type": "structural",
        "extract_items": [
            "excavation", "foundation_concrete", "foundation_pcc",
            "foundation_bitumen", "anti_termite", "road_base",
            "polyethylene_sheet", "neck_column", "neck_column_bitumen",
        ],
        "ai_prompt_focus": "Extract all foundation dimensions: length, width, depth for each footing type and count. Also extract tie beam dimensions.",
    },
    "tie_beam": {
        "drawing_keywords": [
            "tie beam", "الميدة", "TIE BEAM", "T.B", "GRADE BEAM", "PLINTH BEAM",
            "SCHEDULE OF TIE BEAM", "TIE BEAM PLAN", "TIE BEAMS", "T.B. SCHEDULE",
            "GROUND BEAM PLAN", "TIE BEAM DETAILS"
        ],
        "pdf_type": "structural",
        "extract_items": [
            "tie_beam_concrete", "tie_beam_pcc", "slab_on_grade_concrete",
            "solid_block_work", "tie_beam_bitumen", "block_work_bitumen",
            "anti_termite_tie_beam", "polyethylene_sheet_tie_beam",
        ],
        "ai_prompt_focus": "Extract tie beam width, depth, and total length. Extract external perimeter and ground floor area.",
    },
    "column_layout": {
        "drawing_keywords": [
            "column layout", "axes", "مخطط الأعمدة", "محاور", "COLUMN LAYOUT",
            "COLUMN LOCATION", "COLUMNS LAYOUT", "COLUMNS PLAN", "GRID AXES"
        ],
        "pdf_type": "structural",
        "extract_items": [],
        "ai_prompt_focus": "Column layout plan showing grid axes and column locations.",
    },
    "upper_columns": {
        "drawing_keywords": [
            "column schedule", "جدول الأعمدة", "COL SCH", "COLUMN SCHEDULE",
            "TYPICAL COLUMN SCHEDULE", "COLUMNS SCHEDULE", "SCHEDULE OF COLUMNS",
            "COLUMNS DETAILS", "COLUMN DETAILS", "COLUMN SCH"
        ],
        "pdf_type": "structural",
        "extract_items": ["column_concrete_1st", "column_concrete_2nd", "column_concrete_roof"],
        "ai_prompt_focus": "Extract full column schedule: each type with width, length, and count per floor.",
    },
    "neck_columns": {
        "drawing_keywords": [
            "neck column", "ground column", "gf column", "ground floor column",
            "أعمدة الرقبة", "أعمدة الأرضي", "NECK COL", "NECK COLUMN SCHEDULE",
            "GROUND FLOOR COLUMNS", "GF COLUMNS", "NECK COLUMNS", "NECK COLUMN PLAN"
        ],
        "pdf_type": "structural",
        "extract_items": ["neck_column_concrete", "neck_column_bitumen", "col_gf_to_1st"],
        "ai_prompt_focus": "Extract ground-floor / neck columns: each mark with width, length, count.",
    },
    "columns_1f": {
        "drawing_keywords": ["1st floor column", "first floor column", "1st flr col", "أعمدة الأول", "1ST FLOOR COLUMNS", "FIRST FLOOR COLUMNS"],
        "pdf_type": "structural",
        "extract_items": ["col_1st_to_2nd"],
        "ai_prompt_focus": "Extract 1st-floor columns: each mark with width, length, count.",
    },
    "columns_2f": {
        "drawing_keywords": ["2nd floor column", "second floor column", "2nd flr col", "أعمدة الثاني", "2ND FLOOR COLUMNS", "SECOND FLOOR COLUMNS"],
        "pdf_type": "structural",
        "extract_items": ["col_2nd_to_roof"],
        "ai_prompt_focus": "Extract 2nd-floor columns: each mark with width, length, count.",
    },
    "columns_roof": {
        "drawing_keywords": ["roof column", "roof col", "أعمدة السطح", "ROOF COLUMNS", "ROOF FLOOR COLUMNS"],
        "pdf_type": "structural",
        "extract_items": ["col_roof"],
        "ai_prompt_focus": "Extract roof columns: each mark with width, length, count.",
    },
    "slab_1st": {
        "drawing_keywords": [
            "1st slab", "first floor", "SLAB 1", "S1", "الدور الأول", "1ST FLOOR",
            "FIRST FLOOR SLAB", "1ST FLOOR SLAB", "SLAB & BEAM PLAN", "FIRST FLOOR FRAMING",
            "1ST FLOOR FRAMING PLAN", "1ST FLOOR SLAB DETAILS"
        ],
        "pdf_type": "structural",
        "extract_items": ["beam_concrete", "slab_concrete", "staircase_concrete"],
        "ai_prompt_focus": "Extract 1st floor slab thickness, beam schedule (width, depth, length), slab area.",
    },
    "slab_2nd": {
        "drawing_keywords": [
            "2nd slab", "second floor", "SLAB 2", "S2", "الدور الثاني",
            "SECOND FLOOR SLAB", "2ND FLOOR SLAB", "2ND FLOOR FRAMING PLAN"
        ],
        "pdf_type": "structural",
        "extract_items": ["beam_concrete", "slab_concrete"],
        "ai_prompt_focus": "Extract 2nd floor slab thickness, beam schedule, slab area.",
    },
    "roof_slab": {
        "drawing_keywords": [
            "roof slab", "roof beam", "السطح", "PARAPET", "ROOF SLAB PLAN",
            "ROOF SLAB DETAILS", "UPPER ROOF SLAB", "ROOF FRAMING PLAN", "ROOF SLAB & BEAM"
        ],
        "pdf_type": "structural",
        "extract_items": ["slab_concrete", "beam_concrete", "parapet_block_work", "parapet_concrete"],
        "ai_prompt_focus": "Extract roof slab thickness, beam dims, parapet height and perimeter.",
    },
    "setting_out": {
        "drawing_keywords": [
            "setting out", "site plan", "INTERLOCK", "COMPOUND", "موقع", "plot plan",
            "boundary", "master plan", "layout plan", "SETTING OUT PLAN", "LOCATION PLAN",
            "COMPOUND WALL DETAILS"
        ],
        "pdf_type": "architectural",
        "extract_items": ["interlock_paving", "compound_wall"],
        "ai_prompt_focus": "Extract plot area, GF footprint, compound wall length.",
    },
    "ground_floor_plan": {
        "drawing_keywords": [
            "ground floor", "G.F", "GF", "GROUND", "الأرضي", "G.F.P", "GROUND FLOOR PLAN",
            "G.F. PLAN", "GROUND FLOOR LAYOUT", "PROPOSED GROUND FLOOR", "GF PLAN",
            "GROUND FLOOR ARCHITECTURAL PLAN"
        ],
        "pdf_type": "architectural",
        "extract_items": [
            "thermal_block_external", "block_20_internal", "internal_plaster",
            "external_plaster", "wall_tiles", "paint_int", "dry_area_flooring",
            "dry_area_ceiling", "wet_area_flooring", "wet_area_waterproofing",
            "wet_area_ceiling", "balcony_waterproofing",
        ],
        "ai_prompt_focus": "Extract total floor area, external perimeter, internal walls length, wet areas (area+perimeter), dry area, balcony area, floor height.",
    },
    "first_floor_plan": {
        "drawing_keywords": [
            "1st floor", "first floor", "F1", "1F", "الأول", "FIRST FLOOR", "1st flr",
            "first flr", "f.f.p", "f.f plan", "floor 1", "FIRST FLOOR PLAN", "1ST FLOOR PLAN",
            "FIRST FLOOR LAYOUT", "1ST FLOOR LAYOUT", "FF PLAN", "1ST FLOOR ARCHITECTURAL"
        ],
        "pdf_type": "architectural",
        "extract_items": [
            "thermal_block_external", "block_20_internal", "internal_plaster",
            "wall_tiles", "paint_int", "dry_area_flooring", "wet_area_flooring",
            "wet_area_waterproofing", "wet_area_ceiling", "balcony_waterproofing",
        ],
        "ai_prompt_focus": "Extract 1st floor area, wet areas, dry areas, balcony area, internal walls length, external perimeter.",
    },
    "second_floor_plan": {
        "drawing_keywords": [
            "2nd floor", "second floor", "F2", "2F", "الثاني", "SECOND FLOOR",
            "SECOND FLOOR PLAN", "2ND FLOOR PLAN", "SECOND FLOOR LAYOUT"
        ],
        "pdf_type": "architectural",
        "extract_items": [
            "thermal_block_external", "block_20_internal", "internal_plaster",
            "wall_tiles", "paint_int", "dry_area_flooring", "wet_area_flooring",
            "wet_area_waterproofing", "wet_area_ceiling",
        ],
        "ai_prompt_focus": "Extract 2nd floor area, wet areas, dry areas, internal walls length.",
    },
    "roof_floor_plan": {
        "drawing_keywords": [
            "roof plan", "roof floor", "ROOF PLAN", "مسقط السطح", "ROOF FLOOR PLAN",
            "TOP ROOF PLAN", "ROOF PLAN & ELEVATION", "UPPER ROOF PLAN"
        ],
        "pdf_type": "architectural",
        "extract_items": ["roof_waterproofing"],
        "ai_prompt_focus": "Extract roof slab area and perimeter.",
    },
    "elevations": {
        "drawing_keywords": [
            "elevation", "elevations", "واجهة", "واجهات", "ELEV", "FACADE",
            "FRONT ELEVATION", "REAR ELEVATION", "SIDE ELEVATION", "EAST ELEVATION",
            "WEST ELEVATION", "NORTH ELEVATION", "SOUTH ELEVATION", "ELEVATIONS & SECTIONS"
        ],
        "pdf_type": "architectural",
        "extract_items": ["finish_ext", "external_plaster"],
        "ai_prompt_focus": "Extract total villa height and external wall areas for each face.",
    },
    "schedules": {
        "drawing_keywords": [
            "schedule", "جدول", "DOOR SCHEDULE", "WINDOW SCHEDULE", "OPENING",
            "doors details", "windows details", "doors & windows", "d & w", "doors/windows",
            "finish schedule", "door type", "window type", "qty", "quantity", "schedule of doors",
            "SCHEDULE OF DOORS", "SCHEDULE OF WINDOWS", "DOOR & WINDOW SCHEDULE",
            "FINISHES SCHEDULE", "ROOM FINISH SCHEDULE"
        ],
        "pdf_type": "architectural",
        "extract_items": ["openings_doors", "openings_windows"],
        "ai_prompt_focus": "Extract complete door schedule (type, width, height, count) and window schedule (type, width, height, count).",
    },
}


def classify_all_pages(pdf_texts: List[str], pdf_name: str = "") -> List[Dict]:
    """يصنف كل صفحات PDF ويرجع قائمة بنوع كل صفحة"""
    results = []
    for i, text in enumerate(pdf_texts):
        text_lower = text.lower()
        scores = {}
        for page_type, config in PAGE_ITEMS_MAP.items():
            score = sum(1 for kw in config["drawing_keywords"] if kw.lower() in text_lower)
            if page_type == "schedules" and score > 0:
                score += 5
            scores[page_type] = score

        best_type  = max(scores, key=scores.get)
        best_score = scores[best_type]

        results.append({
            "page_index":    i,
            "page_number":   i + 1,
            "detected_type": best_type if best_score > 0 else "unknown",
            "confidence":    "high" if best_score >= 2 else "medium" if best_score == 1 else "low",
            "score":         best_score,
            "extract_items": PAGE_ITEMS_MAP.get(best_type, {}).get("extract_items", []),
            "ai_focus":      PAGE_ITEMS_MAP.get(best_type, {}).get("ai_prompt_focus", ""),
            "pdf_name":      pdf_name,
        })

    return results
