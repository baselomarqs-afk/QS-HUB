"""
End-to-end villa-QTO extraction pipeline.

Inputs:
    --str    path/to/STR.pdf
    --arch   path/to/ARCH.pdf
    --apikey <AI API key>      (optional; falls back to GOOGLE_API_KEY env)

Pipeline:
    1. Classify every page of both PDFs.
    2. Extract STR schedules (footings, tie beams, columns, slab beams).
    3. Extract ARCH base data (plot/areas/perimeters/heights).
    4. Extract opening schedules (doors + windows).
    5. Estimate wall lengths (AI; user can refine in Streamlit).
    6. Run sanity checks; print warnings.
    7. Build a single _project_data.json that the BOQ engine consumes.

Output:
    _project_data.json   — single source of truth, replaces hardcoded `base` dict.

Usage:
    py _master_extractor.py --str "B:/path/STR.pdf" --arch "B:/path/ARCH.pdf"
"""
import sys, os, json, argparse, subprocess
from typing import Optional

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from _pdf_utils import pdf_page_count
from _page_classifier_ai import classify_and_save, OUT_JSON as CLASS_JSON
from _read_arch_ai       import extract_arch,     OUT_JSON as ARCH_JSON
from _read_openings_ai   import extract_openings, OUT_JSON as OPEN_JSON
from _wall_length_extractor  import extract_walls_all_floors, OUT_JSON as WALL_JSON
from _qto_config             import (
    SCHEDULE_JSON, PROJECT_JSON, SANITY, derive_villa_type, get_logger,
)

log = get_logger("master_extractor")


# ── Sanity checks [W11] ───────────────────────────────────────────────────────
def _in_range(val, key: str) -> bool:
    """Check val against SANITY[key]=(lo,hi)."""
    if val is None:
        return True
    lo, hi = SANITY[key]
    return lo <= val <= hi


def sanity_check(data: dict) -> list[str]:
    """Return list of warnings; empty list = all OK."""
    warns = []

    # ── Base dimensions ───────────────────────────────────────────────────────
    for k in ("plot_area", "gf_area", "external_perimeter", "total_villa_height"):
        v = data.get(k)
        if v is not None and not _in_range(v, k):
            lo, hi = SANITY[k]
            warns.append(f"{k}={v} outside typical range ({lo}-{hi})")

    # ── Bbox vs gf_area cross-check ───────────────────────────────────────────
    ll = data.get("longest_length")
    lw = data.get("longest_width")
    ga = data.get("gf_area")
    if ll and lw and ga:
        ratio = ga / (ll * lw)
        if ratio < 0.5 or ratio > 1.05:
            warns.append(
                f"gf_area/bbox ratio = {ratio:.2f} (expected 0.5-1.05) — "
                f"likely a mis-read of one of: gf_area, longest_length, longest_width"
            )

    # ── Foundations ──────────────────────────────────────────────────────────
    footings = data.get("schedules", {}).get("foundation", {}).get("footings", [])
    if not footings:
        warns.append("No footings extracted — check foundation schedule")
    else:
        total_v = sum(
            (f.get("long_mm", 0) or 0) / 1000
            * (f.get("short_mm", 0) or 0) / 1000
            * (f.get("depth_mm", 0) or 0) / 1000
            * (f.get("count", 0) or 0)
            for f in footings
        )
        if not _in_range(total_v, "foundation_total_m3"):
            lo, hi = SANITY["foundation_total_m3"]
            warns.append(f"foundation total volume {total_v:.1f} m³ outside {lo}-{hi}")
        for f in footings:
            d = f.get("depth_mm")
            l = f.get("long_mm")
            if d and not _in_range(d, "footing_depth_mm"):
                lo, hi = SANITY["footing_depth_mm"]
                warns.append(f"Footing {f.get('type')}: depth={d}mm outside {lo}-{hi}")
            if l and not _in_range(l, "footing_long_mm"):
                lo, hi = SANITY["footing_long_mm"]
                warns.append(f"Footing {f.get('type')}: long={l}mm outside {lo}-{hi}")
            if not f.get("count"):
                warns.append(f"Footing {f.get('type')}: count missing or zero")

    # ── Tie beams ─────────────────────────────────────────────────────────────
    tbs = data.get("schedules", {}).get("tie_beam", {}).get("tie_beams", [])
    for t in tbs:
        if t.get("width_mm") and not _in_range(t["width_mm"], "tie_beam_width_mm"):
            lo, hi = SANITY["tie_beam_width_mm"]
            warns.append(f"TB {t.get('type')}: width={t['width_mm']}mm outside {lo}-{hi}")
        if t.get("depth_mm") and not _in_range(t["depth_mm"], "tie_beam_depth_mm"):
            lo, hi = SANITY["tie_beam_depth_mm"]
            warns.append(f"TB {t.get('type')}: depth={t['depth_mm']}mm outside {lo}-{hi}")

    # ── Columns ───────────────────────────────────────────────────────────────
    cols = data.get("schedules", {}).get("column_schedule", {}).get("columns", [])
    for c in cols:
        if c.get("width_mm") and not _in_range(c["width_mm"], "column_width_mm"):
            lo, hi = SANITY["column_width_mm"]
            warns.append(f"Column {c.get('mark')}: width={c['width_mm']}mm outside {lo}-{hi}")
        if c.get("depth_mm") and not _in_range(c["depth_mm"], "column_depth_mm"):
            lo, hi = SANITY["column_depth_mm"]
            warns.append(f"Column {c.get('mark')}: depth={c['depth_mm']}mm outside {lo}-{hi}")

    # ── Slab beams (all floors) ───────────────────────────────────────────────
    for slab_key in ("slab_1f", "slab_2f", "slab_roof"):
        slab = data.get("schedules", {}).get(slab_key, {})
        st   = slab.get("slab_thickness_mm")
        if st and not _in_range(st, "slab_thickness_mm"):
            lo, hi = SANITY["slab_thickness_mm"]
            warns.append(f"{slab_key}: slab_thickness={st}mm outside {lo}-{hi}")
        for b in slab.get("beams", []):
            if b.get("width_mm") and not _in_range(b["width_mm"], "beam_width_mm"):
                lo, hi = SANITY["beam_width_mm"]
                warns.append(f"{slab_key} {b.get('mark')}: width={b['width_mm']}mm outside {lo}-{hi}")
            if b.get("depth_mm") and not _in_range(b["depth_mm"], "beam_depth_mm"):
                lo, hi = SANITY["beam_depth_mm"]
                warns.append(f"{slab_key} {b.get('mark')}: depth={b['depth_mm']}mm outside {lo}-{hi}")

    # ── Openings ──────────────────────────────────────────────────────────────
    op_tot = data.get("openings", {}).get("totals", {})
    if op_tot.get("door_count", 0) == 0:
        warns.append("No doors extracted")
    if op_tot.get("window_count", 0) == 0:
        warns.append("No windows extracted")

    # ── Walls vs floor areas ──────────────────────────────────────────────────
    walls = data.get("walls", {})
    floors = data.get("floors", {})
    for fk, w in walls.items():
        intl = w.get("internal_total_m")
        fa   = (floors.get(fk) or {}).get("area")
        if intl and fa:
            ratio = intl / fa
            lo, hi = SANITY["wall_to_area_ratio"]
            if not (lo <= ratio <= hi):
                warns.append(
                    f"{fk}: internal_walls/area = {ratio:.2f} m/m² outside {lo}-{hi}"
                )

    return warns


# ── Stage runners ─────────────────────────────────────────────────────────────
def run_str_schedules(str_pdf: str, api_key: str | None):
    """Run the (already-existing) STR schedule extractor as a subprocess."""
    env = os.environ.copy()
    env["STR_PDF_PATH"] = str_pdf
    if api_key:
        env["GOOGLE_API_KEY"] = api_key
    cmd = [sys.executable,
           os.path.join(os.path.dirname(__file__), "_read_schedules_ai.py")]
    if api_key:
        cmd.append(api_key)
    print(f"\n  → invoking _read_schedules_ai.py")
    subprocess.run(cmd, env=env, check=False)


# ── Main pipeline ─────────────────────────────────────────────────────────────
def run_pipeline(str_pdf: str, arch_pdf: str, api_key: str | None = None,
                 skip_schedule: bool = False, skip_walls: bool = False,
                 skip_classify: bool = False) -> dict:

    print("=" * 78)
    print(" THE QS HUB MASTER EXTRACTOR")
    print("=" * 78)
    print(f"  STR  : {str_pdf}  ({pdf_page_count(str_pdf)} pages)")
    print(f"  ARCH : {arch_pdf} ({pdf_page_count(arch_pdf)} pages)")

    # ── Step 1: classify pages ────────────────────────────────────────────────
    print("\n── STEP 1: Page Classification ──────────────────────────────────")
    if skip_classify and os.path.exists(CLASS_JSON):
        # Use the classification the user already reviewed/corrected in the UI.
        with open(CLASS_JSON, encoding="utf-8") as f:
            classification = json.load(f)
        print("  (using existing / user-confirmed page classification)")
    else:
        classification = classify_and_save([str_pdf, arch_pdf], api_key=api_key)

    # ── Step 2: STR schedules ─────────────────────────────────────────────────
    print("\n── STEP 2: STR Schedule Extraction ──────────────────────────────")
    if not skip_schedule:
        run_str_schedules(str_pdf, api_key)
    schedule_data = {}
    if os.path.exists(SCHEDULE_JSON):
        with open(SCHEDULE_JSON, encoding='utf-8') as f:
            schedule_data = json.load(f)

    # ── Step 3: ARCH base data ────────────────────────────────────────────────
    print("\n── STEP 3: ARCH Base Data ───────────────────────────────────────")
    arch_data = extract_arch(arch_pdf, classification, api_key=api_key)
    with open(ARCH_JSON, 'w', encoding='utf-8') as f:
        json.dump(arch_data, f, indent=2, ensure_ascii=False)

    # ── Step 4: Openings ──────────────────────────────────────────────────────
    print("\n── STEP 4: Door & Window Schedules ──────────────────────────────")
    open_data = extract_openings(arch_pdf, classification, api_key=api_key)
    with open(OPEN_JSON, 'w', encoding='utf-8') as f:
        json.dump(open_data, f, indent=2, ensure_ascii=False)

    # ── Step 5: Walls ─────────────────────────────────────────────────────────
    wall_data = {}
    if not skip_walls:
        print("\n── STEP 5: Wall Length Estimation ───────────────────────────")
        # Pass floor areas so wall extractor can sanity-check its output [W7]
        floor_areas = {
            fk: f.get("area") for fk, f in arch_data.get("floors", {}).items()
            if f.get("area")
        }
        wall_data = extract_walls_all_floors(
            arch_pdf, classification, api_key=api_key, floor_areas=floor_areas
        )
        with open(WALL_JSON, 'w', encoding='utf-8') as f:
            json.dump(wall_data, f, indent=2, ensure_ascii=False)

    # ── Step 6: Build _project_data.json ──────────────────────────────────────
    print("\n── STEP 6: Build _project_data.json ─────────────────────────────")
    villa_type = derive_villa_type(arch_data.get("structural_levels"))
    project = {
        # core dimensions
        "villa_type":           villa_type,
        "plot_area":            arch_data.get("plot_area"),
        "gf_area":              arch_data.get("gf_area"),
        "external_perimeter":   arch_data.get("external_perimeter"),
        "ext_perimeter":        arch_data.get("external_perimeter"),
        "roof_slab_area":       arch_data.get("roof_slab_area"),
        "roof_perimeter":       arch_data.get("roof_perimeter"),
        "longest_length":       arch_data.get("longest_length"),
        "longest_width":        arch_data.get("longest_width"),
        "total_villa_height":   arch_data.get("total_villa_height"),
        "structural_levels":    arch_data.get("structural_levels"),
        "compound_length":      arch_data.get("compound_length"),
        "parapet_height":       arch_data.get("parapet_height") or 1.0,

        # default substructure (overrideable in UI)
        "excavation_depth":     1.25,

        # per-floor block
        "floors":               arch_data.get("floors", {}),

        # source schedules
        "schedules":            schedule_data,

        # openings
        "openings":             open_data,

        # walls
        "walls":                wall_data,

        # metadata
        "_meta": {
            "str_pdf":          str_pdf,
            "arch_pdf":         arch_pdf,
        },
    }

    # Merge wall data into per-floor block for engine consumption
    for fk, w in wall_data.items():
        if fk in project["floors"]:
            project["floors"][fk]["wall_internal"] = w.get("internal_total_m")
            project["floors"][fk]["wall_external"] = w.get("external_total_m")

    # ── Step 7: Sanity check ──────────────────────────────────────────────────
    print("\n── STEP 7: Sanity Check ─────────────────────────────────────────")
    warns = sanity_check(project)
    project["_sanity_warnings"] = warns
    if not warns:
        print("  ✓ All values within expected ranges.")
    else:
        print(f"    {len(warns)} warnings:")
        for w in warns:
            print(f"     - {w}")

    with open(PROJECT_JSON, 'w', encoding='utf-8') as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓ Saved → {PROJECT_JSON}")
    return project


def cli():
    ap = argparse.ArgumentParser(description="THE QS HUB master extractor")
    ap.add_argument("--str",  required=True,  help="path to STR PDF")
    ap.add_argument("--arch", required=True,  help="path to ARCH PDF")
    ap.add_argument("--apikey",               help="AI API key (optional)")
    ap.add_argument("--skip-schedule", action="store_true",
                    help="skip the STR schedule pass (use existing _schedule_data.json)")
    ap.add_argument("--skip-walls", action="store_true",
                    help="skip the wall-length AI pass")
    args = ap.parse_args()
    run_pipeline(args.str, args.arch,
                 api_key=args.apikey,
                 skip_schedule=args.skip_schedule,
                 skip_walls=args.skip_walls)


if __name__ == "__main__":
    cli()
