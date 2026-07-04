"""
Vector-intelligence helpers for PDF drawings (PDF-only, no DXF).

Every function here is ADDITIVE and DEFENSIVE: it either returns a confident,
sanity-checked result or a safe empty/None value. Callers keep their existing
behaviour as the fallback, so a bad drawing can never make the output worse than
it already was.

Covers:
  1. Self-calibrating scale from the drawing's own dimension chains.
  2. Real closed-polygon areas (shoelace) instead of a bounding box.
  3. Wall geometry filtered by line-weight (dimension/grid lines dropped).
  4. A compact geometry context string to hand the vision model.
  5. Reconciliation of two independently-derived values into a confidence.
  6. Scale from a graphical scale bar (OCR of the numbers under the bar).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Optional

try:
    import fitz  # PyMuPDF
except Exception:  # pragma: no cover
    fitz = None

# Standard architectural plot scales.
_STANDARD_SCALES = (20, 25, 50, 75, 100, 125, 150, 200, 250)
# FLOOR-PLAN scales only — calibration snaps to these. Detail scales (1:20/1:25)
# are deliberately excluded: a floor plan is never 1:20, so a stray match there
# must be rejected (falling back to the safe 1:100 default) rather than shrink
# every quantity ~5×.
_PLAN_SCALES = (50, 75, 100, 125, 150, 200)
_PT_PER_M_BASE = 72.0 / 25.4 * 1000.0  # points per metre at 1:1


def _pt_to_m(scale_ratio: float) -> float:
    return (25.4 / 72.0) * scale_ratio / 1000.0


def _iter_segments(page):
    """Yield (x1, y1, x2, y2, length_pt, width) for every straight edge, incl.
    rectangle sides. `width` is the stroke line-weight (0 if unknown)."""
    for d in page.get_drawings():
        width = float(d.get("width") or 0) or 0.0
        for it in d.get("items", []):
            try:
                if it[0] == "l":
                    p1, p2 = it[1], it[2]
                    yield (p1.x, p1.y, p2.x, p2.y, math.hypot(p2.x - p1.x, p2.y - p1.y), width)
                elif it[0] == "re":
                    r = it[1]
                    corners = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
                    for a, b in zip(corners, corners[1:] + corners[:1]):
                        yield (a[0], a[1], b[0], b[1], math.hypot(b[0] - a[0], b[1] - a[1]), width)
            except Exception:
                continue


def _dimension_tokens(page):
    """Numeric dimension tokens from the vector text layer as
    (value_m, cx, cy). Only clean numbers in a villa-plausible range."""
    out = []
    try:
        words = page.get_text("words")
    except Exception:
        return out
    num_re = re.compile(r"^\d{2,6}(?:\.\d+)?$")
    for w in words:
        tok = (w[4] or "").strip()
        if not num_re.match(tok):
            continue
        try:
            v = float(tok)
        except Exception:
            continue
        # Interpret magnitude → metres (drawings label mm most often).
        if v > 100:
            v_m = v / 1000.0
        elif v > 20:
            v_m = v / 100.0
        else:
            v_m = v
        if 0.3 <= v_m <= 60.0:
            cx = (w[0] + w[2]) / 2.0
            cy = (w[1] + w[3]) / 2.0
            out.append((v_m, cx, cy))
    return out


# ── 1 + 6. Scale ────────────────────────────────────────────────────────────

def calibrate_scale_from_dimensions(page) -> Optional[dict]:
    """Infer the plot scale from the drawing itself by matching dimension texts
    to nearby parallel wall segments. Returns {ratio, confidence, samples} only
    when several independent samples AGREE and land on a standard scale — else
    None (so the caller keeps its own scale).
    """
    if fitz is None:
        return None
    try:
        dims = _dimension_tokens(page)
        if len(dims) < 4:
            return None
        segs = [s for s in _iter_segments(page) if s[4] > 8]  # ignore tiny ticks
        if len(segs) < 8:
            return None

        candidates = []
        for v_m, cx, cy in dims:
            # nearest segment whose drawn length could plausibly equal v_m at a
            # standard scale; require the text to sit close to that segment.
            best = None
            best_d = 40.0  # points
            for x1, y1, x2, y2, Lpt, _w in segs:
                if Lpt < 10:
                    continue
                mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                d = math.hypot(mx - cx, my - cy)
                if d < best_d:
                    best_d = d
                    best = Lpt
            if not best:
                continue
            # ratio implied: v_m metres spread over `best` points
            ratio = v_m * _PT_PER_M_BASE / best
            if 15 <= ratio <= 300:
                candidates.append(ratio)

        if len(candidates) < 3:
            return None
        candidates.sort()
        med = candidates[len(candidates) // 2]
        # snap to nearest FLOOR-PLAN scale within 10 % (reject detail/odd scales)
        snapped = min(_PLAN_SCALES, key=lambda s: abs(s - med))
        if abs(snapped - med) / snapped > 0.10:
            return None
        # agreement: how many candidates are within 12 % of the snapped scale
        agree = sum(1 for c in candidates if abs(c - snapped) / snapped <= 0.12)
        conf = round(agree / len(candidates), 2)
        # Only override the safe default when strongly supported.
        if agree < 4 or conf < 0.6:
            return None
        return {"ratio": int(snapped), "confidence": conf, "samples": len(candidates)}
    except Exception:
        return None


def scale_from_scale_bar(page_array) -> Optional[int]:
    """OCR the numbers beneath a graphical scale bar (bottom of the sheet) and
    derive the scale ratio. Returns a standard ratio or None. Best-effort."""
    try:
        import numpy as np  # noqa
        import cv2
        from pdf_engine.ocr_engine import extract_all_text
        h, w = page_array.shape[:2]
        crop = page_array[int(h * 0.82):, :]
        texts = extract_all_text(crop, preprocess=True)
        # a scale bar reads like "0 1 2 3 4 5 m" — find the max metre number and
        # the horizontal extent of those number labels.
        metre_labels = []
        for t in texts:
            tok = (t.get("text") or "").strip().lower().replace("m", "")
            if re.fullmatch(r"\d{1,2}", tok):
                metre_labels.append((int(tok), t["center_x"]))
        if len(metre_labels) < 3:
            return None
        metre_labels.sort(key=lambda z: z[1])
        real_span = metre_labels[-1][0] - metre_labels[0][0]
        px_span = metre_labels[-1][1] - metre_labels[0][1]
        if real_span <= 0 or px_span <= 0:
            return None
        # We cannot know DPI reliably here, so only use the bar to sanity-flag,
        # not to set an absolute scale. Return None (kept for future wiring).
        return None
    except Exception:
        return None


def best_page_scale(page, text_ratio: Optional[int]) -> dict:
    """Decide the scale for a page. Trusts an explicit '1:N' label when present;
    only self-calibrates when the label is missing (safe — never overrides a
    real label). Returns {ratio, source, confidence}."""
    if text_ratio:
        return {"ratio": int(text_ratio), "source": "label", "confidence": 1.0}
    cal = calibrate_scale_from_dimensions(page)
    if cal:
        return {"ratio": cal["ratio"], "source": "calibrated", "confidence": cal["confidence"]}
    return {"ratio": 100, "source": "default", "confidence": 0.0}


# ── 2 + 3. Areas & filtered bounds ──────────────────────────────────────────

def _shoelace(points) -> float:
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polygon_area_m2(page, scale_ratio: int) -> Optional[float]:
    """Largest plausible CLOSED polygon area (m²) via shoelace — a real footprint
    instead of a bounding box. Returns None if nothing convincing is found."""
    if fitz is None:
        return None
    try:
        pt_to_m = _pt_to_m(scale_ratio)
        w, h = page.rect.width, page.rect.height
        mx, my = w * 0.06, h * 0.06
        best = 0.0
        for d in page.get_drawings():
            for it in d.get("items", []):
                pts = []
                try:
                    if it[0] == "re":
                        r = it[1]
                        pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
                    elif it[0] == "l":
                        continue  # single lines can't form an area alone
                except Exception:
                    continue
                if len(pts) < 3:
                    continue
                if not all(mx < px < w - mx and my < py < h - my for px, py in pts):
                    continue
                a = _shoelace(pts) * pt_to_m * pt_to_m
                if a > best:
                    best = a
        # villa footprint sanity window
        if 30.0 <= best <= 2000.0:
            return round(best, 2)
        return None
    except Exception:
        return None


def filtered_building_bounds(page, scale_ratio: int) -> Optional[dict]:
    """Bounding box of the WALL-weight geometry only (dimension/grid lines have a
    thinner stroke and are dropped), clipped away from the title block. Returns
    {longest_length_m, longest_width_m, external_perimeter_m} or None."""
    if fitz is None:
        return None
    try:
        pt_to_m = _pt_to_m(scale_ratio)
        w, h = page.rect.width, page.rect.height
        mx, my = w * 0.08, h * 0.08
        segs = [s for s in _iter_segments(page)
                if mx < s[0] < w - mx and my < s[1] < h - my
                and mx < s[2] < w - mx and my < s[3] < h - my]
        if len(segs) < 12:
            return None
        widths = sorted(s[5] for s in segs if s[5] > 0)
        if widths:
            thresh = widths[len(widths) // 2]  # median line-weight
            wall = [s for s in segs if s[5] >= thresh] or segs
        else:
            wall = segs
        xs = [c for s in wall for c in (s[0], s[2])]
        ys = [c for s in wall for c in (s[1], s[3])]
        length_m = (max(xs) - min(xs)) * pt_to_m
        width_m = (max(ys) - min(ys)) * pt_to_m
        L, W = max(length_m, width_m), min(length_m, width_m)
        if W < 2.0 or L > 150.0:
            return None
        return {
            "longest_length_m": round(L, 2),
            "longest_width_m": round(W, 2),
            "external_perimeter_m": round(2 * (L + W), 2),
        }
    except Exception:
        return None


# ── 4. Vision context ───────────────────────────────────────────────────────

def build_geometry_context(page, scale_ratio: int) -> str:
    """A short, factual summary of what the vectors say — handed to the vision
    model so it reasons over real geometry, not only pixels. Empty on failure."""
    try:
        parts = [f"Detected plot scale ≈ 1:{scale_ratio}."]
        b = filtered_building_bounds(page, scale_ratio)
        if b:
            parts.append(
                f"Vector footprint extent ≈ {b['longest_length_m']} m × "
                f"{b['longest_width_m']} m (perimeter ≈ {b['external_perimeter_m']} m)."
            )
        area = polygon_area_m2(page, scale_ratio)
        if area:
            parts.append(f"Largest closed slab/room polygon ≈ {area} m².")
        dims = _dimension_tokens(page)
        if dims:
            vals = sorted({round(v, 2) for v, _, _ in dims}, reverse=True)[:12]
            parts.append("Dimension labels found (m): " + ", ".join(str(v) for v in vals) + ".")
        if len(parts) == 1:
            return ""
        return (
            "VECTOR MEASUREMENTS (deterministic, from the PDF geometry — trust "
            "these for scale/size and reconcile your visual reading against them):\n"
            + "\n".join(parts)
        )
    except Exception:
        return ""


# ── 5. Reconciliation ───────────────────────────────────────────────────────

def reconcile(vector_val, ai_val, tol: float = 0.12) -> dict:
    """Combine a deterministic vector value with the AI value into a confidence.
    Returns {value, confidence: high|medium|low, agree}."""
    try:
        v = float(vector_val) if vector_val is not None else None
    except Exception:
        v = None
    try:
        a = float(ai_val) if ai_val is not None else None
    except Exception:
        a = None

    if v is not None and a is not None:
        base = max(abs(v), abs(a), 1e-9)
        agree = abs(v - a) / base <= tol
        # Prefer the deterministic vector figure when they agree closely.
        return {"value": v if agree else v, "confidence": "high" if agree else "low", "agree": agree}
    if v is not None:
        return {"value": v, "confidence": "medium", "agree": None}
    if a is not None:
        return {"value": a, "confidence": "medium", "agree": None}
    return {"value": None, "confidence": "low", "agree": None}
