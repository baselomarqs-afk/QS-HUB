"""
Sanity Checker for QTO Engine
Validates extracted project data against typical engineering and geometric ranges.
"""
from typing import List, Dict, Any

# ── Sanity-check ranges (UAE villa typical) ───────────────────────────────────
SANITY = {
    "plot_area":           (200,  5000),    # m²
    "gf_area":             (100,  1500),    # m²
    "external_perimeter":  (30,   250),     # m
    "total_villa_height":  (4,    20),      # m
    "footing_depth_mm":    (300,  1000),
    "footing_long_mm":     (600,  6000),
    "tie_beam_width_mm":   (150,  500),
    "tie_beam_depth_mm":   (400,  800),
    "column_width_mm":     (150,  600),
    "column_depth_mm":     (200,  1000),
    "slab_thickness_mm":   (150,  350),
    "beam_width_mm":       (150,  600),
    "beam_depth_mm":       (300,  900),
    "foundation_total_m3": (20,   200),
    "wall_to_area_ratio":  (0.3,  5.0),     # internal walls m per floor m²
}

def _in_range(val, key: str, bounds: Dict[str, Any]) -> bool:
    """Check val against bounds[key]=(lo,hi)."""
    if val is None:
        return True
    try:
        val = float(val)
        lo, hi = bounds[key]
        return lo <= val <= hi
    except Exception:
        return True

def sanity_check(data: Dict[str, Any], custom_bounds: Dict[str, Any] = None) -> List[str]:
    """Return list of warnings; empty list = all OK."""
    bounds = dict(SANITY)
    if custom_bounds:
        bounds.update(custom_bounds)
        
    warns = []

    # ── Base dimensions ───────────────────────────────────────────────────────
    for k in ("plot_area", "gf_area", "external_perimeter", "total_villa_height"):
        v = data.get(k)
        if v is not None and not _in_range(v, k, bounds):
            lo, hi = bounds[k]
            warns.append(f"{k} = {v} is outside typical range ({lo}-{hi})")

    # ── Bbox vs gf_area cross-check ───────────────────────────────────────────
    ll = data.get("longest_length")
    lw = data.get("longest_width")
    ga = data.get("gf_area")
    if ll and lw and ga:
        try:
            ratio = float(ga) / (float(ll) * float(lw))
            if ratio < 0.5 or ratio > 1.05:
                warns.append(
                    f"gf_area/bbox ratio = {ratio:.2f} (expected 0.5-1.05) — "
                    f"likely a mis-read of one of: gf_area, longest_length, longest_width"
                )
        except Exception:
            pass

    # ── Foundations ──────────────────────────────────────────────────────────
    footings = data.get("schedules", {}).get("foundation", {}).get("footings", [])
    if not footings:
        warns.append("No footings extracted — check foundation schedule")
    else:
        try:
            total_v = sum(
                (float(f.get("long_mm", 0) or 0) / 1000)
                * (float(f.get("short_mm", 0) or 0) / 1000)
                * (float(f.get("depth_mm", 0) or 0) / 1000)
                * int(f.get("count", 0) or 0)
                for f in footings
            )
            if not _in_range(total_v, "foundation_total_m3", bounds):
                lo, hi = bounds["foundation_total_m3"]
                warns.append(f"foundation total volume {total_v:.1f} m³ outside {lo}-{hi}")
        except Exception:
            pass
            
        for f in footings:
            try:
                d = f.get("depth_mm")
                l = f.get("long_mm")
                if d and not _in_range(d, "footing_depth_mm", bounds):
                    lo, hi = bounds["footing_depth_mm"]
                    warns.append(f"Footing {f.get('type')}: depth={d}mm outside {lo}-{hi}")
                if l and not _in_range(l, "footing_long_mm", bounds):
                    lo, hi = bounds["footing_long_mm"]
                    warns.append(f"Footing {f.get('type')}: long={l}mm outside {lo}-{hi}")
                if not f.get("count"):
                    warns.append(f"Footing {f.get('type')}: count missing or zero")
            except Exception:
                pass

    # ── Tie beams ─────────────────────────────────────────────────────────────
    tbs = data.get("schedules", {}).get("tie_beam", {}).get("tie_beams", [])
    for t in tbs:
        try:
            if t.get("width_mm") and not _in_range(t["width_mm"], "tie_beam_width_mm", bounds):
                lo, hi = bounds["tie_beam_width_mm"]
                warns.append(f"TB {t.get('type')}: width={t['width_mm']}mm outside {lo}-{hi}")
            if t.get("depth_mm") and not _in_range(t["depth_mm"], "tie_beam_depth_mm", bounds):
                lo, hi = bounds["tie_beam_depth_mm"]
                warns.append(f"TB {t.get('type')}: depth={t['depth_mm']}mm outside {lo}-{hi}")
        except Exception:
            pass

    # ── Columns ───────────────────────────────────────────────────────────────
    cols = data.get("schedules", {}).get("column_schedule", {}).get("columns", [])
    for c in cols:
        try:
            if c.get("width_mm") and not _in_range(c["width_mm"], "column_width_mm", bounds):
                lo, hi = bounds["column_width_mm"]
                warns.append(f"Column {c.get('mark')}: width={c['width_mm']}mm outside {lo}-{hi}")
            if c.get("depth_mm") and not _in_range(c["depth_mm"], "column_depth_mm", bounds):
                lo, hi = bounds["column_depth_mm"]
                warns.append(f"Column {c.get('mark')}: depth={c['depth_mm']}mm outside {lo}-{hi}")
        except Exception:
            pass

    # ── Slab beams (all floors) ───────────────────────────────────────────────
    for slab_key in ("slab_1st", "slab_2nd", "roof_slab"):
        slab = data.get("schedules", {}).get(slab_key, {})
        try:
            st = slab.get("slab_thickness_mm")
            if st and not _in_range(st, "slab_thickness_mm", bounds):
                lo, hi = bounds["slab_thickness_mm"]
                warns.append(f"{slab_key}: slab_thickness={st}mm outside {lo}-{hi}")
            for b in slab.get("beams", []):
                if b.get("width_mm") and not _in_range(b["width_mm"], "beam_width_mm", bounds):
                    lo, hi = bounds["beam_width_mm"]
                    warns.append(f"{slab_key} {b.get('mark')}: width={b['width_mm']}mm outside {lo}-{hi}")
                if b.get("depth_mm") and not _in_range(b["depth_mm"], "beam_depth_mm", bounds):
                    lo, hi = bounds["beam_depth_mm"]
                    warns.append(f"{slab_key} {b.get('mark')}: depth={b['depth_mm']}mm outside {lo}-{hi}")
        except Exception:
            pass

    # ── Openings ──────────────────────────────────────────────────────────────
    op_tot = data.get("openings", {}).get("totals", {})
    if int(op_tot.get("door_count", 0) or 0) == 0:
        warns.append("No doors extracted")
    if int(op_tot.get("window_count", 0) or 0) == 0 and float(op_tot.get("window_area", 0) or 0) == 0:
        warns.append("No windows extracted")

    return warns
