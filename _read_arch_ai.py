"""
Extracts the ARCHITECTURAL base-data needed by the QTO engine:

    plot_area              ← arch_site
    compound_length        ← arch_site
    gf_area                ← arch_gf
    1f_area                ← arch_1f (if exists)
    2f_area                ← arch_2f (if exists)
    roof_slab_area         ← arch_roof
    external_perimeter     ← arch_gf
    roof_perimeter         ← arch_roof
    longest_length         ← arch_gf
    longest_width          ← arch_gf
    total_villa_height     ← arch_elevation
    structural_levels      ← derived from floor count
    is_ground_floor flag   ← per floor in floors{}

Uses the page classifier output to know which PDF pages to scan.

Output → _arch_data.json
"""
import sys, os, json
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from _pdf_utils import render_page, ask_ai, parse_json
from _page_classifier_ai import classify_and_save, get_pages_of_type, OUT_JSON as CLASS_JSON

OUT_JSON = os.path.join(os.path.dirname(__file__), "_arch_data.json")


# ── Prompts ───────────────────────────────────────────────────────────────────
_PROMPTS = {
    "arch_site": """This is a SITE PLAN / PLOT PLAN of a UAE villa.
Extract these values by reading the dimensions/areas labelled on the drawing:

Return ONLY this JSON (no markdown, no explanation):
{
  "plot_area_m2":        <number or null>,
  "compound_length_m":   <number or null>,
  "plot_length_m":       <number or null>,
  "plot_width_m":        <number or null>
}

Rules:
- plot_area_m2 = total plot/site area in square meters (look for "AREA = ...", "SITE AREA")
- compound_length_m = total perimeter of the boundary wall in meters
- If you find plot length & width but no area, leave plot_area_m2 null
- Use null for anything you cannot read confidently
- Return ONLY the JSON""",

    "arch_gf": """This is the GROUND FLOOR PLAN of a UAE villa.
Villa plans rarely write the room AREA explicitly, but they DO show each room's name and its DIMENSIONS (e.g. "5.00 x 4.00") and the building's overall dimensions. READ THE DIMENSIONS — do not guess.

Extract these values from the drawing dimensions and any area notes:

Return ONLY this JSON:
{
  "gf_area_m2":             <number or null>,
  "external_perimeter_m":   <number or null>,
  "longest_length_m":       <number or null>,
  "longest_width_m":        <number or null>,
  "internal_wall_length_m": <number or null>,
  "balcony_area_m2":        <number or null>,
  "rooms": [
    {
      "name": "<room name, e.g. Kitchen, Bedroom, Bathroom>",
      "length_m": <number>,
      "width_m": <number>,
      "area_m2": <number or null>
    }
  ]
}

Rules:
- gf_area_m2 = total ground-floor built-up area in m² (look for "BUA", "BUILT UP AREA", "G.F AREA")
- external_perimeter_m = sum of outer wall lengths around the entire footprint
- longest_length_m / longest_width_m = overall bounding-box dimensions (m)
- Convert any mm or cm dimensions to METERS (1000mm = 1m, 100cm = 1m)
- List EVERY room/space in "rooms" with its length and width from the dimension labels.
- CRITICAL: DO NOT SKIP ANY BATHROOMS, TOILETS, OR KITCHENS. They are required for wet area calculations.
- Use null for anything unclear
- Return ONLY the JSON""",

    "arch_1f": """This is the FIRST FLOOR PLAN of a UAE villa.
Return ONLY this JSON:
{
  "floor_area_m2":          <number or null>,
  "external_perimeter_m":   <number or null>,
  "internal_wall_length_m": <number or null>,
  "balcony_area_m2":        <number or null>,
  "rooms": [
    {
      "name": "<room name, e.g. Kitchen, Bedroom, Bathroom>",
      "length_m": <number>,
      "width_m": <number>,
      "area_m2": <number or null>
    }
  ]
}
- floor_area_m2 = 1st floor built-up area in m²
- All units in METERS (convert mm/cm)
- List EVERY room/space in "rooms" with its length and width from the dimension labels.
- CRITICAL: DO NOT SKIP ANY BATHROOMS, TOILETS, OR KITCHENS. They are required for wet area calculations.
- Return ONLY the JSON""",

    "arch_2f": """This is the SECOND FLOOR PLAN of a UAE villa.
Return ONLY this JSON:
{
  "floor_area_m2":          <number or null>,
  "external_perimeter_m":   <number or null>,
  "internal_wall_length_m": <number or null>,
  "balcony_area_m2":        <number or null>,
  "rooms": [
    {
      "name": "<room name, e.g. Kitchen, Bedroom, Bathroom>",
      "length_m": <number>,
      "width_m": <number>,
      "area_m2": <number or null>
    }
  ]
}
- All units in METERS
- List EVERY room/space in "rooms" with its length and width.
- CRITICAL: DO NOT SKIP ANY BATHROOMS, TOILETS, OR KITCHENS. They are required for wet area calculations.
- Return ONLY the JSON""",

    "arch_roof": """This is the ROOF PLAN of a UAE villa.
Return ONLY this JSON:
{
  "roof_area_m2":           <number or null>,
  "roof_perimeter_m":       <number or null>,
  "parapet_perimeter_m":    <number or null>,
  "parapet_height_m":       <number or null>
}
- roof_area_m2 = total horizontal roof slab area in m²
- roof_perimeter_m = perimeter of the roof outline
- parapet_height_m = height of parapet wall in meters (often 1.0 - 1.5m)
- All units in METERS
- Return ONLY the JSON""",

    "arch_elevation": """This is an ELEVATION (facade view) of a UAE villa.
Extract the total height of the villa:

Return ONLY this JSON:
{
  "total_height_m":          <number or null>,
  "floor_to_floor_heights_m": [<number>, <number>, ...],
  "parapet_height_m":         <number or null>
}
- total_height_m = ground level to top of parapet/roof in meters
- floor_to_floor_heights_m = list of heights per floor in order (GF, 1F, 2F, ...)
- All units in METERS
- Return ONLY the JSON""",
}


# ── Single-page extraction ────────────────────────────────────────────────────
def extract_page(pdf_path: str, page_index: int, page_type: str,
                 api_key: str | None = None, dpi: int = 280) -> dict:
    """Render the page and ask AI for the relevant fields."""
    prompt = _PROMPTS.get(page_type)
    if prompt is None:
        return {"_error": f"No prompt for page type {page_type}"}
        
    # --- DETERMINISTIC OVERRIDE (FIX FOR AI HALLUCINATIONS) ---
    import fitz, re
    regex_overrides = {}
    try:
        with fitz.open(pdf_path) as doc:
            if page_index < len(doc):
                text = doc[page_index].get_text("text")
                
                if page_type == "arch_site":
                    m = re.search(r"(?i)(?:PLOT\s*AREA|SITE\s*AREA|AREA)\s*[:=]?\s*([\d\.,]+)", text)
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        regex_overrides["plot_area_m2"] = val
                
                elif page_type == "arch_gf":
                    m = re.search(r"(?i)(?:BUA|BUILT\s*UP\s*AREA|G\.F\s*AREA|GROUND\s*FLOOR\s*AREA)\s*[:=]?\s*([\d\.,]+)", text)
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        regex_overrides["gf_area_m2"] = val
                        
                elif page_type == "arch_1f":
                    m = re.search(r"(?i)(?:FIRST\s*FLOOR\s*AREA|1\.F\s*AREA|1ST\s*FLOOR\s*AREA)\s*[:=]?\s*([\d\.,]+)", text)
                    if m:
                        val = float(m.group(1).replace(",", ""))
                        regex_overrides["floor_area_m2"] = val
    except Exception as e:
        print(f"Regex extraction failed: {e}")
    # ----------------------------------------------------------

    img = render_page(pdf_path, page_index, dpi=dpi)
    raw = ask_ai(img, prompt, api_key=api_key)
    try:
        parsed = parse_json(raw)
        # Apply deterministic regex overrides if found
        for k, v in regex_overrides.items():
            parsed[k] = v
            parsed["_regex_matched"] = True
            print(f"    [REGEX OVERRIDE] {k} = {v}")
        return parsed
    except Exception as e:
        return {"_error": str(e), "_raw": raw[:500]}


# ── Aggregation across multiple pages of same type ────────────────────────────
def _coalesce(*vals):
    """Return first non-None numeric value, else None."""
    for v in vals:
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def _finishes_from_rooms(data: dict) -> dict:
    """Turn a reliable ROOM LIST into the finishes inputs the formulas need."""
    rooms = data.get("rooms") or []
    if not rooms:
        return data

    _WET_KW = ("bath", "toilet", "wc", "w.c", "kitchen", "pantry", "laundry",
               "ensuite", "en-suite", "powder", "shower", "washroom", "wash room",
               "حمام", "دورة", "مطبخ", "مغسلة", "تواليت", "مرحاض")

    def is_wet(r):
        name = str(r.get("name", "")).lower()
        return any(kw in name for kw in _WET_KW)

    def dim(v):
        try: v = float(v)
        except (TypeError, ValueError): return 0.0
        return v / 1000.0 if v > 50 else v

    def per(r):
        l, w = dim(r.get("length_m")), dim(r.get("width_m"))
        return 2 * (l + w) if (l and w) else 0.0

    def area(r):
        try: a = float(r.get("area_m2") or 0)
        except (TypeError, ValueError): a = 0.0
        if a: return a
        l, w = dim(r.get("length_m")), dim(r.get("width_m"))
        return l * w

    total_area = sum(area(r) for r in rooms)
    wet_area   = sum(area(r) for r in rooms if is_wet(r))
    wet_per    = sum(per(r)  for r in rooms if is_wet(r))
    dry_per    = sum(per(r)  for r in rooms if not is_wet(r))
    sum_per    = sum(per(r)  for r in rooms)

    L = dim(data.get("longest_length_m"))
    W = dim(data.get("longest_width_m"))
    ext_per = 2 * (L + W) if (L and W) else 0.0

    if total_area > 0:
        implied = (ext_per / 4.0) ** 2 if ext_per else 0.0
        if (not ext_per) or implied > total_area * 1.8:
            ext_per = round(4.2 * (total_area ** 0.5), 2)

    int_walls = max((sum_per - ext_per) / 2.0, 0.0) if (sum_per and ext_per) else 0.0

    data["calculated_area"] = round(total_area, 2)
    data["wet_area_m2"] = round(wet_area, 2)
    data["wet_area_perimeter_m"] = round(wet_per, 2)
    data["dry_area_m2"] = max(round(total_area - wet_area, 2), 0.0)
    data["dry_area_perimeter_m"] = round(dry_per, 2)
    data["internal_wall_length_m"] = round(int_walls, 2)
    if ext_per:
        data["external_perimeter_m"] = round(ext_per, 2)
    
    return data

def extract_arch(arch_pdf: str, classification: dict,
                 api_key: str | None = None) -> dict:
    """
    Run extraction across all ARCH pages and consolidate.

    Returns flat dict ready to be merged into base dict.
    """
    out  = {
        "_source_pdf": arch_pdf,
        "floors":      {},
    }
    pdf_class = classification.get(arch_pdf, {})

    # Helper: get the highest-confidence page of a given type
    def best_page(page_type: str) -> Optional[int]:
        candidates = [
            (int(idx), info["confidence"])
            for idx, info in pdf_class.items()
            if info["type"] == page_type
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: -x[1])
        return candidates[0][0]

    # ── 1. Site plan → plot_area, compound_length ─────────────────────────────
    pi = best_page("arch_site")
    if pi is not None:
        print(f"\n  [arch_site] reading page {pi+1}...")
        d = extract_page(arch_pdf, pi, "arch_site", api_key=api_key)
        out["plot_area"]       = _coalesce(d.get("plot_area_m2"))
        out["compound_length"] = _coalesce(d.get("compound_length_m"))
        print(f"    plot_area={out['plot_area']}  compound_length={out['compound_length']}")

    # ── 2. Ground floor plan → gf_area, perimeter, dimensions ─────────────────
    pi = best_page("arch_gf")
    if pi is not None:
        print(f"\n  [arch_gf] reading page {pi+1}...")
        d = extract_page(arch_pdf, pi, "arch_gf", api_key=api_key)
        d = _finishes_from_rooms(d)
        
        # --- DETERMINISTIC OVERRIDE: VECTOR BOUNDS ---
        try:
            from workflow.vector_area_measure import measure_architectural_bounds
            vec_bounds = measure_architectural_bounds(arch_pdf, pi)
            if vec_bounds:
                d.update(vec_bounds)
                print(f"    [VECTOR OVERRIDE] Extracted geometric bounds: {vec_bounds}")
        except Exception as e:
            print(f"    [VECTOR OVERRIDE] Failed: {e}")
        # ---------------------------------------------

        # If the prompt's explicit gf_area_m2 wasn't found, try our calculated area from rooms
        gf_area = _coalesce(d.get("gf_area_m2"), d.get("calculated_area"))
        out["gf_area"]            = gf_area
        out["external_perimeter"] = _coalesce(d.get("external_perimeter_m"))
        out["longest_length"]     = _coalesce(d.get("longest_length_m"))
        out["longest_width"]      = _coalesce(d.get("longest_width_m"))
        out["floors"]["gf"] = {
            "area":             out["gf_area"],
            "ext_perimeter":    out["external_perimeter"],
            "wall_internal":    _coalesce(d.get("internal_wall_length_m")),
            "wet_area":         _coalesce(d.get("wet_area_m2")),
            "wet_perimeter":    _coalesce(d.get("wet_area_perimeter_m")),
            "dry_area":         _coalesce(d.get("dry_area_m2")),
            "dry_perimeter":    _coalesce(d.get("dry_area_perimeter_m")),
            "balcony_area":     _coalesce(d.get("balcony_area_m2")),
            "is_ground_floor":  True,
        }
        print(f"    gf_area={out['gf_area']}  ext_perim={out['external_perimeter']}  "
              f"L×W={out['longest_length']}×{out['longest_width']}")

    # ── 3. 1F / 2F plans ──────────────────────────────────────────────────────
    for floor_key, pt in [("1f", "arch_1f"), ("2f", "arch_2f")]:
        pi = best_page(pt)
        if pi is not None:
            print(f"\n  [{pt}] reading page {pi+1}...")
            d = extract_page(arch_pdf, pi, pt, api_key=api_key)
            d = _finishes_from_rooms(d)
            area = _coalesce(d.get("floor_area_m2"), d.get("calculated_area"))
            out["floors"][floor_key] = {
                "area":             area,
                "ext_perimeter":    _coalesce(d.get("external_perimeter_m")),
                "wall_internal":    _coalesce(d.get("internal_wall_length_m")),
                "wet_area":         _coalesce(d.get("wet_area_m2")),
                "wet_perimeter":    _coalesce(d.get("wet_area_perimeter_m")),
                "dry_area":         _coalesce(d.get("dry_area_m2")),
                "dry_perimeter":    _coalesce(d.get("dry_area_perimeter_m")),
                "balcony_area":     _coalesce(d.get("balcony_area_m2")),
                "is_ground_floor":  False,
            }
            print(f"    area={out['floors'][floor_key]['area']}")

    # ── 4. Roof plan → roof area + perimeter + parapet ────────────────────────
    pi = best_page("arch_roof")
    if pi is not None:
        print(f"\n  [arch_roof] reading page {pi+1}...")
        d = extract_page(arch_pdf, pi, "arch_roof", api_key=api_key)
        out["roof_slab_area"] = _coalesce(d.get("roof_area_m2"))
        out["roof_perimeter"] = _coalesce(d.get("roof_perimeter_m"))
        out["parapet_height"] = _coalesce(d.get("parapet_height_m"))
        out["floors"]["roof"] = {
            "area":            out["roof_slab_area"],
            "ext_perimeter":   out["roof_perimeter"],
            "is_ground_floor": False,
        }
        print(f"    roof_area={out['roof_slab_area']}  parapet_h={out['parapet_height']}")

    # ── 5. Elevation → total height ───────────────────────────────────────────
    pi = best_page("arch_elevation")
    if pi is not None:
        print(f"\n  [arch_elevation] reading page {pi+1}...")
        d = extract_page(arch_pdf, pi, "arch_elevation", api_key=api_key)
        out["total_villa_height"] = _coalesce(d.get("total_height_m"))
        ff = d.get("floor_to_floor_heights_m") or []
        if isinstance(ff, list) and ff:
            out["floor_heights"] = [float(x) for x in ff if x is not None]
        out["parapet_height"] = out.get("parapet_height") or _coalesce(d.get("parapet_height_m"))
        print(f"    total_height={out.get('total_villa_height')}")

    # ── 6. Derive structural_levels (count of floors detected) ────────────────
    out["structural_levels"] = sum(
        1 for k in out["floors"] if k in ("gf", "1f", "2f", "roof")
    )

    # ── 7. Auto-compute fallbacks for missing values [W6] ─────────────────────
    _autocompute_missing(out, arch_pdf, classification, api_key)
    return out


def _autocompute_missing(out: dict, arch_pdf: str, classification: dict,
                          api_key: str | None):
    """
    Fill in missing values from related ones when possible:

      • plot_area     = plot_length × plot_width      (if both known)
      • gf_area       ≈ longest_length × longest_width × 0.85 (fallback only)
      • roof_perim    = external_perimeter            (very common in UAE villas)
      • parapet_h     = 1.0 m                          (UAE default)
      • compound_len  ≈ 2 × (plot_l + plot_w)         (perimeter rectangle assumption)

    Cross-validates known values; flags inconsistency on out["_arch_warnings"].
    """
    warns: list[str] = []

    # ── re-read site plan if plot_area still None but length×width unknown ───
    if out.get("plot_area") is None:
        # Try to pull length/width from the same site page we already hit
        pdf_cls = classification.get(arch_pdf, {})
        site_pi = next(
            (int(i) for i, info in pdf_cls.items() if info.get("type") == "arch_site"),
            None,
        )
        if site_pi is not None:
            d = extract_page(arch_pdf, site_pi, "arch_site", api_key=api_key)
            pl = d.get("plot_length_m")
            pw = d.get("plot_width_m")
            if pl and pw:
                out["plot_area"] = round(float(pl) * float(pw), 2)
                warns.append(f"plot_area auto-computed from {pl}×{pw}")

    # ── compound_length fallback ──────────────────────────────────────────────
    if out.get("compound_length") is None and out.get("plot_area"):
        # Assume roughly square plot
        side = out["plot_area"] ** 0.5
        out["compound_length"] = round(4 * side, 2)
        warns.append(f"compound_length estimated from sqrt(plot_area): {out['compound_length']}")

    # ── gf_area cross-validation ──────────────────────────────────────────────
    ll = out.get("longest_length")
    lw = out.get("longest_width")
    ga = out.get("gf_area")
    if ll and lw:
        bbox = ll * lw
        if ga is None:
            # Conservative estimate: bounding box × 0.85
            out["gf_area"] = round(bbox * 0.85, 2)
            if "gf" in out["floors"]:
                out["floors"]["gf"]["area"] = out["gf_area"]
            warns.append(f"gf_area estimated from bbox×0.85: {out['gf_area']}")
        else:
            ratio = ga / bbox
            if ratio < 0.5 or ratio > 1.05:
                warns.append(
                    f"gf_area={ga} vs bbox(L×W)={bbox:.1f} ratio={ratio:.2f} — verify"
                )

    # ── roof_perimeter ≈ external_perimeter ───────────────────────────────────
    if out.get("roof_perimeter") is None and out.get("external_perimeter"):
        out["roof_perimeter"] = out["external_perimeter"]
        warns.append("roof_perimeter copied from external_perimeter")

    # ── parapet height default ────────────────────────────────────────────────
    if out.get("parapet_height") is None:
        out["parapet_height"] = 1.0
        warns.append("parapet_height defaulted to 1.0 m")

    # ── total_villa_height fallback from floor heights ────────────────────────
    if out.get("total_villa_height") is None and out.get("floor_heights"):
        h = sum(out["floor_heights"]) + (out.get("parapet_height") or 1.0)
        out["total_villa_height"] = round(h, 2)
        warns.append(f"total_villa_height summed from floor_heights: {h}")

    if warns:
        out["_arch_warnings"] = warns


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print("Usage: py _read_arch_ai.py path/to/ARCH.pdf [api_key]")
        sys.exit(1)
    arch_pdf = sys.argv[1]
    api_key  = sys.argv[2] if len(sys.argv) > 2 else None

    # ── Load or build classification ──────────────────────────────────────────
    classification = {}
    if os.path.exists(CLASS_JSON):
        with open(CLASS_JSON, encoding="utf-8") as f:
            classification = json.load(f)
    if arch_pdf not in classification:
        print(f"  ARCH PDF not classified yet — running classifier...")
        classification = classify_and_save([arch_pdf], api_key=api_key)

    # ── Extract ───────────────────────────────────────────────────────────────
    data = extract_arch(arch_pdf, classification, api_key=api_key)

    # ── Save ──────────────────────────────────────────────────────────────────
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  ARCH data saved → {OUT_JSON}")


if __name__ == "__main__":
    main()
