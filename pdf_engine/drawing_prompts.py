"""
Detailed per-drawing-type prompts for AI Engine analysis.
Concept ported from simple app's buildPromptForDrawingType().
Each drawing type tells the AI WHERE to look, HOW to count, and what JSON to return.
"""


def build_prompt(page_type: str) -> str:
    """Returns a detailed, drawing-specific prompt for AI Vision."""

    if page_type == "foundations":
        return """Analyze this foundation drawing and extract the following in JSON format.

1. From the FOUNDATION SCHEDULE TABLE (usually right side):
   - Extract ALL footing types (F1, F2, F3, CF1, CF2, etc.)
   - For each footing: dimensions WIDTHxLENGTHxDEPTH in centimeters → convert to METERS

2. From the PLAN DRAWING (left side) — COUNTING RULES:
   - Count EVERY instance of each footing label (F1, F2, etc.) in the plan
   - Each label = 1 footing. If F2 appears 3 times → count = 3
   - Look at the ENTIRE plan: corners, edges, center — do not miss any
   - Count from the plan ONLY, not from the table
   - If a type is in the table but NOT in the plan → count = 0

3. BUILDING DIMENSIONS:
   - LONGEST LENGTH: total horizontal dimension at top of drawing
   - LONGEST WIDTH: look at LEFT SIDE, find ALL vertical dimension segments, ADD THEM ALL:
     Example: 1.75 + 2.00 + 2.40 + 4.45 + 1.75 = 12.35m (do NOT read just one number)

Return ONLY valid JSON:
{
  "dimensions": {
    "footings": [
      {"type": "F1", "width": 1.00, "length": 1.00, "depth": 0.40, "count": 4, "confidence": 95}
    ],
    "longest_length": 11.85,
    "longest_width": 9.30,
    "exc_depth": 1.25
  },
  "scale": "1:100",
  "confidence": 95,
  "warnings": []
}

RULES: Convert CM→M. Dimensions 0.10–5.00m. Counts are positive integers. Return ONLY JSON."""

    if page_type == "tie_beam":
        return """Analyze this tie beam drawing and extract the following in JSON format.

1. From the TIE BEAM SCHEDULE TABLE (usually right side):
   - Extract ALL beam types (TB1, TB2, TB3, etc.)
   - For each beam: WIDTHxDEPTH in centimeters → convert to METERS

2. From the PLAN DRAWING — MEASURE TOTAL LENGTH (not count!):
   - For each beam type: sum ALL segment lengths of that type in the plan
   - Example: TB1 in 3 locations (5m + 3m + 4m) → total length = 12m

3. AREA AND WALL MEASUREMENTS from plan:
   - Ground floor slab area (m²)
   - Total wall length (linear meters, for block work below grade)
   
4. TYPICAL DIMENSIONS:
   - Determine the most common or "typical" tie beam width and depth (e.g. 0.20 and 0.60) from the schedule.

Return ONLY valid JSON:
{
  "dimensions": {
    "beams": [
      {"type": "TB1", "width": 0.25, "depth": 0.50, "length": 12.50, "confidence": 90}
    ],
    "typical_tb_width": 0.20,
    "typical_tb_depth": 0.60,
    "gf_area": 95.50,
    "wall_length": 45.30,
    "exc_depth": 1.50,
    "pcc_thickness": 0.10
  },
  "scale": "1:100",
  "confidence": 92,
  "warnings": []
}

RULES: Length = SUM of all segments per beam type. Convert CM→M. Return ONLY JSON."""

    if page_type in ("upper_columns", "ground_columns"):
        return """Analyze this column drawing and extract the following in JSON format.

1. From the COLUMN SCHEDULE TABLE (usually right side):
   - Extract ALL column types (C1, C2, C3, etc.)
   - For each column: WIDTHxLENGTH in centimeters → convert to METERS

2. From the PLAN DRAWING — COUNTING RULES:
   - Count EVERY instance of each column label (C1, C2, etc.) in the plan
   - Each label = 1 column. If C1 appears 4 times → count = 4
   - Look at the ENTIRE plan: corners, edges, center
   - If a type is in the table but NOT in the plan → count = 0

Return ONLY valid JSON:
{
  "dimensions": {
    "columns": [
      {"type": "C1", "width": 0.25, "length": 0.60, "count": 4, "confidence": 95},
      {"type": "C2", "width": 0.30, "length": 0.30, "count": 8, "confidence": 90}
    ]
  },
  "scale": "1:100",
  "confidence": 93,
  "warnings": []
}

RULES: Convert CM→M. Counts are positive integers. Return ONLY JSON."""

    if page_type == "slab_1st":
        return """Analyze this 1st floor slab drawing and extract the following in JSON format.

1. From the BEAM SCHEDULE TABLE (right side):
   - Extract ALL beam types (B1, B2, B3, etc.)
   - For each beam: WIDTHxDEPTH in centimeters → convert to METERS

2. From the PLAN DRAWING — BEAM LENGTHS:
   - For each beam type: measure TOTAL LINEAR LENGTH (sum of all segments in meters)
   - Also count how many beams of each type

3. SLAB:
   - Total slab area (m²)
   - Slab thickness (Look carefully for general notes like "ALL SLABS 200MM U.N.O" or "SLAB THICKNESS = 20CM". Convert to meters, e.g. 0.20)
   - Floor height (look for note, default 4.0m)

4. STAIRCASE: Does this floor have a staircase? If yes, stair width (default 1.2m), count.

Return ONLY valid JSON:
{
  "dimensions": {
    "beams": [
      {"type": "B1", "width": 0.25, "depth": 0.50, "length": 15.50, "count": 3, "confidence": 90}
    ],
    "slab_area": 120.50,
    "slab_thickness": 0.20,
    "floor_height": 4.0,
    "stair_width": 1.2,
    "stair_count": 1
  },
  "scale": "1:100",
  "confidence": 91,
  "warnings": []
}

RULES: Length = SUM of all segments. Convert CM→M. Return ONLY JSON."""

    if page_type == "slab_2nd":
        return """Analyze this 2nd floor slab drawing and extract the following in JSON format.

1. From the BEAM SCHEDULE TABLE:
   - Extract ALL beam types (B1, B2, B3, etc.): WIDTHxDEPTH in CM → METERS

2. From the PLAN DRAWING:
   - For each beam type: TOTAL LINEAR LENGTH (sum of all segments in meters), count
   - Total slab area (m²), slab thickness (Look carefully for general notes like "ALL SLABS 200MM U.N.O", convert to meters, e.g. 0.20)

Return ONLY valid JSON:
{
  "dimensions": {
    "beams": [
      {"type": "B1", "width": 0.25, "depth": 0.50, "length": 15.50, "count": 3, "confidence": 90}
    ],
    "slab_area": 120.50,
    "slab_thickness": 0.20
  },
  "scale": "1:100",
  "confidence": 91,
  "warnings": []
}

RULES: Length = SUM of all segments. Convert CM→M. Return ONLY JSON."""

    if page_type == "roof_slab":
        return """Analyze this roof slab drawing and extract the following in JSON format.

1. From the BEAM SCHEDULE TABLE:
   - Extract ALL beam types (B1, B2, etc.): WIDTHxDEPTH in CM → METERS

2. From the PLAN DRAWING:
   - For each beam type: TOTAL LINEAR LENGTH (sum of all segments), count
   - Total slab area (m²), slab thickness (Look carefully for notes, e.g. 0.20m)

3. PARAPET:
   - Parapet perimeter (external perimeter of roof in meters)
   - Parapet height (look for note, default 1.0m)
   - Parapet thickness (default 0.20m)

Return ONLY valid JSON:
{
  "dimensions": {
    "beams": [
      {"type": "B1", "width": 0.25, "depth": 0.50, "length": 15.50, "count": 3, "confidence": 90}
    ],
    "slab_area": 120.50,
    "slab_thickness": 0.20,
    "parapet_perimeter": 45.30,
    "parapet_height": 1.0,
    "parapet_thickness": 0.20
  },
  "scale": "1:100",
  "confidence": 91,
  "warnings": []
}

RULES: Length = SUM of all segments. Convert CM→M. Return ONLY JSON."""

    if page_type == "setting_out":
        return """Analyze this setting out / site plan drawing and extract the following in JSON format.

1. INTERLOCK PAVING AREA: total external area around the building for interlock paving (m²)
2. COMPOUND WALL LENGTH: total perimeter wall length around the property (linear meters)
3. PLOT AREA: total plot area (m²)
4. GF FOOTPRINT: ground floor building footprint area (m²)

Return ONLY valid JSON:
{
  "dimensions": {
    "plot_area": 500.00,
    "gf_footprint": 150.00,
    "interlock_area": 150.50,
    "compound_length": 85.30
  },
  "scale": "1:100",
  "confidence": 90,
  "warnings": []
}

RULES: Measure areas and lengths carefully. Return ONLY JSON."""

    if page_type == "ground_floor_plan":
        return """Analyze this GROUND FLOOR PLAN drawing and extract the following in JSON format.

1. EXTERNAL WALLS: external perimeter (m), floor height (look for note, default 4.0m)
2. INTERNAL WALLS: total internal walls length (m), for block work
3. DRY AREAS: total dry area (living rooms, bedrooms, corridors) floor area (m²), dry perimeter (m)
4. WET AREAS: total wet area (bathrooms, kitchens, laundry) floor area (m²), wet perimeter (m)
5. BALCONY: balcony area (m²), 0 if no balcony
6. TOTAL FLOOR AREA: complete floor area including all rooms (m²)

Return ONLY valid JSON:
{
  "dimensions": {
    "total_area": 145.50,
    "ext_perimeter": 45.30,
    "int_walls_length": 65.20,
    "floor_height": 4.0,
    "dry_area": 120.00,
    "dry_perimeter": 75.00,
    "wet_area": 25.50,
    "wet_perimeter": 32.00,
    "balcony_area": 8.50
  },
  "scale": "1:100",
  "confidence": 88,
  "warnings": []
}

RULES: Separate dry and wet areas carefully. Measure all perimeters. Return ONLY JSON."""

    if page_type == "first_floor_plan":
        return """Analyze this 1ST FLOOR PLAN drawing and extract the following in JSON format.

1. EXTERNAL WALLS: external perimeter (m), floor height (default 4.0m)
2. INTERNAL WALLS: total internal walls length (m)
3. DRY AREAS: total dry area floor area (m²), dry perimeter (m)
4. WET AREAS: total wet area floor area (m²), wet perimeter (m)
5. BALCONY: balcony area (m²), 0 if none
6. TOTAL FLOOR AREA (m²)

Return ONLY valid JSON:
{
  "dimensions": {
    "total_area": 145.50,
    "ext_perimeter": 45.30,
    "int_walls_length": 65.20,
    "floor_height": 4.0,
    "dry_area": 120.00,
    "dry_perimeter": 75.00,
    "wet_area": 25.50,
    "wet_perimeter": 32.00,
    "balcony_area": 8.50
  },
  "scale": "1:100",
  "confidence": 88,
  "warnings": []
}

RULES: Separate dry and wet areas carefully. Return ONLY JSON."""

    if page_type == "second_floor_plan":
        return """Analyze this 2ND FLOOR PLAN drawing and extract the following in JSON format.

1. EXTERNAL WALLS: external perimeter (m), floor height (default 4.0m)
2. INTERNAL WALLS: total internal walls length (m)
3. DRY AREAS: total dry area (m²), dry perimeter (m)
4. WET AREAS: total wet area (m²), wet perimeter (m)
5. TOTAL FLOOR AREA (m²)

Return ONLY valid JSON:
{
  "dimensions": {
    "total_area": 145.50,
    "ext_perimeter": 45.30,
    "int_walls_length": 65.20,
    "floor_height": 4.0,
    "dry_area": 120.00,
    "dry_perimeter": 75.00,
    "wet_area": 25.50,
    "wet_perimeter": 32.00,
    "balcony_area": 0
  },
  "scale": "1:100",
  "confidence": 88,
  "warnings": []
}

RULES: Separate dry and wet areas carefully. Return ONLY JSON."""

    if page_type == "roof_floor_plan":
        return """Analyze this ROOF FLOOR PLAN drawing and extract the following in JSON format.

1. ROOF SLAB AREA: complete roof slab area for waterproofing (m²)
2. ROOF PERIMETER: external perimeter of roof (m)

Return ONLY valid JSON:
{
  "dimensions": {
    "roof_area": 145.50,
    "roof_perimeter": 48.60
  },
  "scale": "1:100",
  "confidence": 92,
  "warnings": []
}

RULES: Measure complete roof area. Return ONLY JSON."""

    if page_type == "elevations":
        return """Analyze this ELEVATION drawing and extract the following in JSON format.

1. EXTERNAL FINISH AREA: total external wall area visible in this elevation (m²)
   - Measure full wall area then deduct windows and doors
2. TOTAL VILLA HEIGHT: overall building height from ground to top (m)

Return ONLY valid JSON:
{
  "dimensions": {
    "external_finish_area": 85.50,
    "total_height": 12.0
  },
  "scale": "1:100",
  "confidence": 90,
  "warnings": []
}

RULES: Deduct window and door openings from wall area. Return ONLY JSON."""

    if page_type == "schedules":
        return """Analyze this DOOR/WINDOW SCHEDULE drawing and extract the following in JSON format.

1. DOOR SCHEDULE: Extract ALL door types (D1, D2, D3, etc.)
   - For each door: width (m), height (m), quantity/count
   - Get dimensions from the schedule table
   - Get count from the QTY column in the table

2. WINDOW SCHEDULE: Extract ALL window types (W1, W2, W3, etc.)
   - For each window: width (m), height (m), quantity/count
   - Get dimensions from the schedule table
   - Get count from the QTY column in the table

Return ONLY valid JSON:
{
  "dimensions": {
    "doors": [
      {"type": "D1", "width": 0.90, "height": 2.10, "count": 5, "confidence": 95},
      {"type": "D2", "width": 1.20, "height": 2.10, "count": 3, "confidence": 92}
    ],
    "windows": [
      {"type": "W1", "width": 1.20, "height": 1.50, "count": 4, "confidence": 95},
      {"type": "W2", "width": 1.00, "height": 1.20, "count": 6, "confidence": 92}
    ]
  },
  "scale": "1:100",
  "confidence": 93,
  "warnings": []
}

RULES: Extract ALL types from schedule. Get count from QTY column. Convert CM→M if needed. Return ONLY JSON."""

    # fallback
    return (
        "You are a QTO engineer analyzing a UAE villa construction drawing. "
        "Extract all dimensions, measurements, and quantities visible. "
        "Return structured JSON with a 'dimensions' key containing all extracted values, "
        "a 'confidence' score (0-100), and a 'warnings' array."
    )
