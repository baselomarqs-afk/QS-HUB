"""
كل مخطط بيستخرج بس اللي معادلاته محتاجاه
مبني على equations_and_pages_detections.txt بالظبط
"""
import re

# ══════════════════════════════════════════════════════
# كل drawing → المعادلات اللي فيه → الـ inputs المطلوبة
# ══════════════════════════════════════════════════════

DRAWING_REQUIRED_INPUTS = {

    "foundations": {
        "label": "Foundations | الأساسات",
        "formulas_and_inputs": {
            "excavation":          ["longest_length", "longest_width"],
            "foundation_concrete": ["footing_width", "footing_length", "footing_depth", "footing_count"],
            "foundation_pcc":      ["footing_width", "footing_length", "footing_count"],
            "foundation_bitumen":  ["footing_width", "footing_length", "footing_depth", "footing_count"],
            "anti_termite_found":  ["longest_length", "longest_width"],
            "road_base":           ["longest_length", "longest_width"],
            "polyethylene_found":  ["footing_width", "footing_length", "footing_count"],
            "backfill":            ["longest_length", "longest_width",
                                    "footing_width", "footing_length", "footing_depth", "footing_count"],
        },
        "extract_only": [
            "longest_length",
            "longest_width",
            "footing_width",
            "footing_length",
            "footing_depth",
            "footing_count",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "floor_heights",
            "areas", "perimeters",
        ],
        "ai_instruction": """
Extract ONLY:
1. The overall building footprint: longest_length and longest_width (full extent of all footings combined)
2. For each footing type (F1, F2, etc.): width, length, depth, count

DO NOT extract:
- Floor heights, column dimensions, beam dimensions
- Areas or perimeters
- Any dates, sheet numbers, scale ratios, revision marks
""",
    },

    "tie_beam": {
        "label": "Tie Beam | الميدة",
        "formulas_and_inputs": {
            "tie_beam_concrete":  ["tb_width", "tb_depth", "tb_total_length"],
            "tie_beam_pcc":       ["tb_width", "tb_total_length"],
            "tie_beam_bitumen":   ["tb_total_length", "tb_depth"],
            "slab_on_grade":      ["gf_area"],
            "solid_block_work":   ["ext_perimeter"],
            "block_work_bitumen": ["ext_perimeter"],
            "anti_termite_tb":    ["gf_area"],
            "polyethylene_tb":    ["gf_area", "tb_width", "tb_total_length"],
        },
        "extract_only": [
            "tb_width",
            "tb_depth",
            "tb_total_length",
            "gf_area",
            "ext_perimeter",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "footing_dimensions", "column_dimensions", "beam_dimensions",
            "floor_heights", "individual_segment_lengths",
        ],
        "ai_instruction": """
Extract ONLY:
1. Tie beam cross-section: width and depth
2. Total tie beam length (sum of ALL segments — not individual spans)
3. Ground floor total area (inside the tie beams)
4. External perimeter of the building

DO NOT extract:
- Individual tie beam segment lengths
- Footing, column, or beam dimensions
- Floor heights
- Any dates, sheet numbers, scale ratios
""",
    },

    "ground_columns": {
        "label": "Ground Columns (Neck) | أعمدة الرقبة",
        "formulas_and_inputs": {
            "neck_column_concrete": ["nc_width", "nc_length", "nc_count"],
            "neck_column_bitumen":  ["nc_width", "nc_length", "nc_count"],
        },
        "extract_only": [
            "nc_width",
            "nc_length",
            "nc_count",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "footing_dimensions", "beam_dimensions", "floor_heights",
            "areas", "perimeters", "slab_dimensions",
        ],
        "ai_instruction": """
Extract ONLY:
For each neck column type (NC1, NC2, etc.): width, length, count

DO NOT extract:
- Footing or upper column dimensions
- Beam or slab dimensions
- Heights, areas, perimeters
- Any dates, sheet numbers, scale ratios
""",
    },

    "upper_columns": {
        "label": "Upper Columns | الأعمدة العلوية",
        "formulas_and_inputs": {
            "col_concrete_1st":  ["col_width", "col_length", "col_count"],
            "col_concrete_2nd":  ["col_width", "col_length", "col_count"],
            "col_concrete_roof": ["col_width", "col_length", "col_count"],
        },
        "extract_only": [
            "col_width",
            "col_length",
            "col_count",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "footing_dimensions", "beam_dimensions", "floor_heights",
            "areas", "perimeters", "slab_thickness",
            "column_heights",  # fixed in formulas: 4.0m floors, 3.5m roof
        ],
        "ai_instruction": """
Extract ONLY from the column schedule:
For each column type (C1, C2, etc.): width, length, and count per floor

DO NOT extract:
- Column heights (fixed: 4.0m for floors, 3.5m for roof)
- Footing, beam, or slab dimensions
- Floor heights, areas, perimeters
- Any dates, sheet numbers, scale ratios, revision marks
""",
    },

    "slab_1st": {
        "label": "1st Floor Slab | بلاطة الأول",
        "formulas_and_inputs": {
            "slab_concrete":      ["slab_area", "slab_thickness"],
            "beam_concrete":      ["beam_length", "beam_width", "beam_depth"],
            "staircase_concrete": ["structural_levels"],
        },
        "extract_only": [
            "slab_area",
            "slab_thickness",
            "beam_length",
            "beam_width",
            "beam_depth",
            "structural_levels",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "footing_dimensions",
            "floor_heights", "perimeters", "reinforcement_details",
        ],
        "ai_instruction": """
Extract ONLY:
1. Slab total area and thickness
2. For each beam (B1, B2, etc.): length, width, depth
3. Number of structural levels (G+1=1, G+2=2, G+3=3)

DO NOT extract:
- Column or footing dimensions
- Floor heights or perimeters
- Reinforcement bar details
- Any dates, sheet numbers, scale ratios
""",
    },

    "slab_2nd": {
        "label": "2nd Floor Slab | بلاطة الثاني",
        "formulas_and_inputs": {
            "slab_concrete": ["slab_area", "slab_thickness"],
            "beam_concrete": ["beam_length", "beam_width", "beam_depth"],
        },
        "extract_only": [
            "slab_area", "slab_thickness",
            "beam_length", "beam_width", "beam_depth",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "footing_dimensions",
            "floor_heights", "perimeters", "reinforcement_details",
        ],
        "ai_instruction": """
Extract ONLY:
1. Slab total area and thickness
2. For each beam: length, width, depth

DO NOT extract:
- Column or footing dimensions
- Floor heights, perimeters, reinforcement details
- Dates, sheet numbers, scale ratios
""",
    },

    "roof_slab": {
        "label": "Roof Slab | بلاطة السطح",
        "formulas_and_inputs": {
            "slab_concrete":      ["slab_area", "slab_thickness"],
            "beam_concrete":      ["beam_length", "beam_width", "beam_depth"],
            "parapet_block_work": ["roof_perimeter"],
            "parapet_concrete":   ["roof_perimeter"],
        },
        "extract_only": [
            "slab_area", "slab_thickness",
            "beam_length", "beam_width", "beam_depth",
            "roof_perimeter",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "footing_dimensions",
            "floor_heights", "reinforcement_details",
        ],
        "ai_instruction": """
Extract ONLY:
1. Roof slab area and thickness
2. For each roof beam: length, width, depth
3. Roof slab perimeter (for parapet calculation)

DO NOT extract:
- Column or footing dimensions
- Floor heights, reinforcement details
- Dates, sheet numbers, scale ratios
""",
    },

    "setting_out": {
        "label": "Setting Out | مخطط الموقع",
        "formulas_and_inputs": {
            "interlock_paving": ["plot_area", "gf_area"],
            "compound_wall":    ["compound_length"],
        },
        "extract_only": [
            "plot_area",
            "gf_area",
            "compound_length",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions",
            "floor_heights", "individual_room_areas",
        ],
        "ai_instruction": """
Extract ONLY:
1. "plot_area": Total plot/land area (If not explicitly written, calculate it mathematically by multiplying the outer boundary dimensions: Length × Width)
2. "gf_area": Ground floor building footprint area
3. "compound_length": Total compound/boundary wall length (This is the PERIMETER of the plot. CRITICAL: If there is no explicit "total length" text, YOU MUST VISUALLY ESTIMATE OR CALCULATE the perimeter by summing the boundary lines you see (Top + Right + Bottom + Left). Do NOT return null if you can estimate the boundary length from the drawing scale or grid.)

DO NOT extract:
- Individual room areas
- Column or beam dimensions
- Floor heights
- Dates, sheet numbers, scale ratios
""",
    },

    "ground_floor_plan": {
        "label": "Ground Floor Plan | مسقط الأرضي",
        "formulas_and_inputs": {
            "thermal_block_external": ["ext_perimeter", "floor_height"],
            "block_20_internal":      ["int_walls_length", "floor_height"],
            "internal_plaster":       ["int_walls_length", "ext_perimeter", "floor_height"],
            "dry_area_flooring":      ["total_floor_area", "wet_area"],
            "wet_area_flooring":      ["wet_area"],
            "wall_tiles":             ["wet_perimeter", "floor_height"],
            "skirting":               ["dry_perimeter"],
            "paint_int":              ["dry_perimeter", "floor_height"],
            "dry_area_ceiling":       ["total_floor_area", "wet_area"],
            "wet_area_ceiling":       ["wet_area"],
            "balcony_waterproofing":  ["balcony_area"],
        },
        "extract_only": [
            "total_floor_area",
            "wet_area",
            "wet_perimeter",
            "dry_perimeter",
            "ext_perimeter",
            "int_walls_length",
            "floor_height",
            "balcony_area",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "footing_dimensions",
            "individual_room_names", "furniture_dimensions",
            "door_dimensions", "window_dimensions", "reinforcement_details",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total floor area
2. Total wet area (bathrooms + toilets + kitchen + laundry combined)
3. Total wet rooms perimeter
4. Total dry areas perimeter
5. External perimeter of floor
6. Total internal partition walls length
7. Floor to ceiling height
8. Balcony/terrace area (0 if none)

DO NOT extract:
- Individual room dimensions or names
- Door or window dimensions
- Column, beam, footing dimensions
- Furniture dimensions
- Dates, sheet numbers, scale ratios
""",
    },

    "first_floor_plan": {
        "label": "1st Floor Plan | مسقط الأول",
        "formulas_and_inputs": {
            "thermal_block_external": ["ext_perimeter", "floor_height"],
            "block_20_internal":      ["int_walls_length", "floor_height"],
            "internal_plaster":       ["int_walls_length", "ext_perimeter", "floor_height"],
            "dry_area_flooring":      ["total_floor_area", "wet_area"],
            "wet_area_flooring":      ["wet_area"],
            "wall_tiles":             ["wet_perimeter", "floor_height"],
            "skirting":               ["dry_perimeter"],
            "paint_int":              ["dry_perimeter", "floor_height"],
            "dry_area_ceiling":       ["total_floor_area", "wet_area"],
            "wet_area_ceiling":       ["wet_area"],
            "wet_area_waterproofing": ["wet_area"],
            "balcony_waterproofing":  ["balcony_area"],
        },
        "extract_only": [
            "total_floor_area", "wet_area", "wet_perimeter",
            "dry_perimeter", "ext_perimeter",
            "int_walls_length", "floor_height", "balcony_area",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "footing_dimensions",
            "individual_room_dimensions", "door_dimensions", "window_dimensions",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total floor area
2. Total wet area (all wet rooms combined)
3. Total wet rooms perimeter
4. Total dry areas perimeter
5. External perimeter
6. Total internal walls length
7. Floor height
8. Balcony area (0 if none)

DO NOT extract:
- Individual room dimensions
- Door or window dimensions
- Column, beam, footing dimensions
- Dates, sheet numbers, scale ratios
""",
    },

    "second_floor_plan": {
        "label": "2nd Floor Plan | مسقط الثاني",
        "formulas_and_inputs": {
            "thermal_block_external": ["ext_perimeter", "floor_height"],
            "block_20_internal":      ["int_walls_length", "floor_height"],
            "internal_plaster":       ["int_walls_length", "ext_perimeter", "floor_height"],
            "dry_area_flooring":      ["total_floor_area", "wet_area"],
            "wet_area_flooring":      ["wet_area"],
            "wall_tiles":             ["wet_perimeter", "floor_height"],
            "skirting":               ["dry_perimeter"],
            "paint_int":              ["dry_perimeter", "floor_height"],
            "wet_area_waterproofing": ["wet_area"],
            "balcony_waterproofing":  ["balcony_area"],
        },
        "extract_only": [
            "total_floor_area", "wet_area", "wet_perimeter",
            "dry_perimeter", "ext_perimeter",
            "int_walls_length", "floor_height", "balcony_area",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "individual_room_dimensions",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total floor area
2. Total wet area
3. Wet rooms perimeter
4. Dry areas perimeter
5. External perimeter
6. Internal walls length
7. Floor height
8. Balcony area (0 if none)

DO NOT extract:
- Individual room dimensions
- Column or beam dimensions
- Dates, sheet numbers, scale ratios
""",
    },

    "roof_floor_plan": {
        "label": "Roof Floor Plan | مسقط السطح",
        "formulas_and_inputs": {
            "roof_waterproofing": ["roof_slab_area"],
        },
        "extract_only": [
            "roof_slab_area",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "perimeters",
            "parapet_dimensions", "heights",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total roof slab area

Nothing else. No perimeters, no heights, no column dims, no dates.
""",
    },

    "elevations": {
        "label": "Elevations | الواجهات",
        "formulas_and_inputs": {
            "external_plaster": ["ext_perimeter", "total_villa_height"],
            "finish_ext":       ["ext_perimeter", "total_villa_height"],
        },
        "extract_only": [
            "ext_perimeter",
            "total_villa_height",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "footing_dimensions",
            "floor_heights", "individual_wall_lengths",
            "window_dimensions", "door_dimensions", "room_dimensions",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total external perimeter of the villa
2. Total villa height from ground level to roof top

DO NOT extract:
- Individual floor heights (total only)
- Individual wall lengths
- Column, beam, footing, window, door dimensions
- Dates, sheet numbers, scale ratios
""",
    },

    "schedules": {
        "label": "Door & Window Schedules | الجداول",
        "formulas_and_inputs": {
            "openings_doors":   ["door_count"],
            "openings_windows": ["win_width", "win_height", "win_count"],
        },
        "extract_only": [
            "door_count",
            "win_width",
            "win_height",
            "win_count",
        ],
        "ignore_completely": [
            "dates", "sheet_numbers", "revision_marks", "scale_ratios",
            "column_dimensions", "beam_dimensions", "footing_dimensions",
            "floor_heights", "areas", "perimeters",
            "door_dimensions",   # only count needed for doors
            "frame_dimensions", "threshold_dimensions",
        ],
        "ai_instruction": """
Extract ONLY:
1. Total door count (all types combined)
2. For each window type: width, height, count

DO NOT extract:
- Door dimensions (only count needed)
- Column, beam, footing dimensions
- Floor heights, areas, perimeters
- Dates, sheet numbers, scale ratios
""",
    },
}


def get_ai_prompt_for_drawing(drawing_type: str) -> str:
    """Builds a focused prompt telling the AI exactly what to extract."""
    config = DRAWING_REQUIRED_INPUTS.get(drawing_type)
    if not config:
        return "Extract all visible dimensions and return as JSON."

    lines = "\n".join(f"  - {inp}" for inp in config["extract_only"])
    return (
        f"Drawing type: {config['label']}\n"
        f"{config['ai_instruction']}\n"
        f"Required outputs (ONLY these keys):\n{lines}\n\n"
        "Return ONLY valid JSON with these exact keys. Use null for anything not found."
    )


def filter_ocr_by_drawing_inputs(raw_dims: list, drawing_type: str) -> list:
    """
    Keeps only OCR-extracted numbers that could be formula inputs for this drawing.
    Drops dates, scale ratios, revision marks, and noise.
    """
    config = DRAWING_REQUIRED_INPUTS.get(drawing_type)
    if not config:
        return raw_dims

    filtered = []
    for dim in raw_dims:
        txt = str(dim.get("original_text", "")).lower()

        skip = False
        # Date pattern
        if re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', txt):
            skip = True
        # Scale ratio
        if re.search(r'1\s*[:/]\s*\d+', txt):
            skip = True
        # Revision mark
        if re.search(r'\brev\s*\d+\b|r\d+\s*$', txt, re.IGNORECASE):
            skip = True
        # Sheet / drawing number patterns (e.g. "S-01", "A03")
        if re.search(r'\b[a-zA-Z]{1,2}-?\d{2,3}\b', txt) and not re.search(r'\d+\.\d+', txt):
            skip = True

        if not skip:
            filtered.append(dim)

    return filtered
