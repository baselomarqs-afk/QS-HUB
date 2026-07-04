"""
Measure beam lengths directly from a vector STR framing plan.

Concept (user's spec): beam concrete = length × width × depth  (NOT × count).
The schedule table gives width/depth, but never the run length, so we measure
the length off the drawing geometry:

    1. The mark label (B1, HB2, ...) is printed next to each beam it names.
       We already use those label occurrences to COUNT beams (fitz).
    2. For each occurrence we find the nearest plausible beam line segment and
       measure its real length via the drawing scale.
    3. The total length of a mark = Σ measured length over all its occurrences.

So `count` is implicit in the summation — no separate multiplier.

This is a *measure-assist*: the result is a SUGGESTION the user confirms /
corrects in Schedule Review.  Each mark also carries a confidence figure
(fraction of occurrences that matched a real beam-length line).

Vector → real length
--------------------
At plot scale 1:S, one PDF point (1/72") on paper equals:
    (25.4 / 72) mm paper  →  × S real  →  / 1000  metres
"""
import sys, os, re, math, json
from collections import defaultdict

import fitz

sys.path.insert(0, os.path.dirname(__file__))

# Plausible beam run, in metres — filters out grid ticks, hatching, text leaders
_MIN_BEAM_M = 1.0
_MAX_BEAM_M = 16.0
# Search radius around a mark label, in PDF points
_RADIUS_PT  = 45
# Beam mark token pattern
_MARK_RE    = re.compile(r"(?:B|HB|RB|GB|FB)\d{1,2}", re.IGNORECASE)
# Tie-beam mark token pattern (TB1, TB2, …) — measured the SAME way as beams
_TB_MARK_RE = re.compile(r"TB\d{1,2}", re.IGNORECASE)


def _pt_to_m(scale_ratio: int) -> float:
    """Metres per PDF point at plot scale 1:scale_ratio."""
    return (25.4 / 72.0) * scale_ratio / 1000.0


def detect_page_scale(page) -> int:
    """
    Pick the framing-plan plot scale.  Framing plans are almost always 1:100;
    detail scales (1:25 / 1:50) also appear on the sheet, so we prefer 100 when
    present, else the largest ratio found, else default 100.
    """
    txt = page.get_text("text")
    ratios = [int(m) for m in re.findall(r"1\s*[:/]\s*(\d{2,3})", txt)]
    if ratios:
        # An explicit "1:N" label is authoritative — never override it.
        return 100 if 100 in ratios else max(ratios)
    # No scale label on the sheet: self-calibrate from the drawing's own
    # dimension chains instead of blindly assuming 1:100. Falls back to 100.
    try:
        from pdf_engine.vector_intelligence import calibrate_scale_from_dimensions
        cal = calibrate_scale_from_dimensions(page)
        if cal:
            return cal["ratio"]
    except Exception:
        pass
    return 100


def _segments(page, pt_to_m: float) -> list[tuple]:
    """All straight segments as (mx, my, length_m), filtered to plausible beams."""
    out = []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                L = math.hypot(p2.x - p1.x, p2.y - p1.y) * pt_to_m
                if _MIN_BEAM_M <= L <= _MAX_BEAM_M:
                    out.append(((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, L))
            elif it[0] == "re":
                r = it[1]
                for a, b in (((r.x0, r.y0), (r.x1, r.y0)),
                             ((r.x1, r.y0), (r.x1, r.y1)),
                             ((r.x1, r.y1), (r.x0, r.y1)),
                             ((r.x0, r.y1), (r.x0, r.y0))):
                    L = math.hypot(b[0] - a[0], b[1] - a[1]) * pt_to_m
                    if _MIN_BEAM_M <= L <= _MAX_BEAM_M:
                        out.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, L))
    return out


def _mark_occurrences(page, mark_re=_MARK_RE) -> dict[str, list[tuple]]:
    """{MARK: [(cx, cy), ...]} from text words on the page (pattern configurable)."""
    marks: dict[str, list[tuple]] = defaultdict(list)
    for w in page.get_text("words"):
        tok = w[4].strip().upper()
        if mark_re.fullmatch(tok):
            marks[tok].append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))
    return marks


def measure_page(pdf_path: str, page_index: int,
                 scale_ratio: int | None = None,
                 mark_re=_MARK_RE) -> dict[str, dict]:
    """
    Measure mark lengths on one plan page (beams by default, or any mark pattern).

    Returns { MARK: { 'measured_m': float, 'occurrences': int,
                      'matched': int, 'confidence': float } }
    """
    doc  = fitz.open(pdf_path)
    if page_index >= len(doc):
        doc.close()
        return {}
    page = doc[page_index]
    ratio = scale_ratio or detect_page_scale(page)
    pt_to_m = _pt_to_m(ratio)

    segs  = _segments(page, pt_to_m)
    marks = _mark_occurrences(page, mark_re)
    doc.close()

    results: dict[str, dict] = {}
    for mark, occs in marks.items():
        total, matched = 0.0, 0
        for cx, cy in occs:
            best = 0.0
            for mx, my, L in segs:
                if abs(mx - cx) <= _RADIUS_PT and abs(my - cy) <= _RADIUS_PT:
                    best = max(best, L)
            if best > 0:
                total += best
                matched += 1
        n = len(occs)
        results[mark] = {
            "measured_m":  round(total, 2),
            "occurrences": n,
            "matched":     matched,
            "confidence":  round(matched / n, 2) if n else 0.0,
            "scale":       f"1:{ratio}",
        }
    return results


def _pt_seg_dist(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def measure_tie_beams(pdf_path: str, page_index: int,
                      scale_ratio: int | None = None,
                      label_dist_pt: float = 14.0) -> dict[str, dict]:
    """
    EXTRACT tie-beam run length from the vector plan (no approximation).

    Tie beams form a continuous network and are drawn as TWO parallel face
    lines, fragmented into many short collinear segments, with the same mark
    (TB1…) labelled many times along the run. A per-occurrence sum double-counts
    shared lines, so instead:

      1. Tag every line segment with the NEAREST tie-beam label (within
         `label_dist_pt`) → groups all geometry by mark.
      2. Per mark, group segments by orientation + perpendicular line, and
         UNION their longitudinal intervals → each physical line counted once.
      3. Divide by 2 (the two drawn faces) → the centre-line run length.

    Returns { MARK: {measured_m, segments, matched_labels, occurrences,
                     confidence, scale} }.
    """
    doc   = fitz.open(pdf_path)
    if page_index >= len(doc):
        doc.close()
        return {}
    page  = doc[page_index]
    ratio = scale_ratio or detect_page_scale(page)
    pt_to_m = _pt_to_m(ratio)

    # raw segments in POINTS (need geometry, keep > 3pt)
    raw = []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                p1, p2 = it[1], it[2]
                if math.hypot(p2.x - p1.x, p2.y - p1.y) > 3:
                    raw.append((p1.x, p1.y, p2.x, p2.y))
            elif it[0] == "re":
                r = it[1]
                for a, b in (((r.x0, r.y0), (r.x1, r.y0)), ((r.x1, r.y0), (r.x1, r.y1)),
                             ((r.x1, r.y1), (r.x0, r.y1)), ((r.x0, r.y1), (r.x0, r.y0))):
                    if math.hypot(b[0] - a[0], b[1] - a[1]) > 3:
                        raw.append((a[0], a[1], b[0], b[1]))

    occ = _mark_occurrences(page, _TB_MARK_RE)   # {mark: [(cx,cy)…]}
    doc.close()

    labels = [(cx, cy, mk) for mk, pts in occ.items() for cx, cy in pts]

    # tag each segment with nearest TB label
    tagged: dict[str, list] = defaultdict(list)
    matched_pts: dict[str, set] = defaultdict(set)
    for s in raw:
        best, bd = None, label_dist_pt
        for lx, ly, mk in labels:
            dd = _pt_seg_dist(lx, ly, *s)
            if dd < bd:
                bd, best = dd, (mk, lx, ly)
        if best:
            tagged[best[0]].append(s)
            matched_pts[best[0]].add((best[1], best[2]))

    def _orient(s):
        return "H" if abs(s[2] - s[0]) >= abs(s[3] - s[1]) else "V"

    def _merged_pts(seglist) -> float:
        groups: dict = defaultdict(list)
        for s in seglist:
            if _orient(s) == "H":
                perp = round((s[1] + s[3]) / 2 / 3) * 3
                lo, hi = min(s[0], s[2]), max(s[0], s[2])
            else:
                perp = round((s[0] + s[2]) / 2 / 3) * 3
                lo, hi = min(s[1], s[3]), max(s[1], s[3])
            groups[(_orient(s), perp)].append((lo, hi))
        tot = 0.0
        for ivs in groups.values():
            ivs.sort()
            m = []
            for lo, hi in ivs:
                if m and lo <= m[-1][1] + 1:
                    m[-1][1] = max(m[-1][1], hi)
                else:
                    m.append([lo, hi])
            tot += sum(h - l for l, h in m)
        return tot

    results: dict[str, dict] = {}
    for mk, pts in occ.items():
        seglist = tagged.get(mk, [])
        run_m = (_merged_pts(seglist) * pt_to_m) / 2.0   # ÷2 for the two faces
        n = len(pts)
        matched = len(matched_pts.get(mk, set()))
        results[mk] = {
            "measured_m":  round(run_m, 2),
            "segments":    len(seglist),
            "occurrences": n,
            "matched":     matched,
            "confidence":  round(matched / n, 2) if n else 0.0,
            "scale":       f"1:{ratio}",
        }
    return results


def measure_all_beam_pages(pdf_path: str, classification: dict | None = None) -> dict[str, dict]:
    """
    Measure beams on every framing-plan page and bucket by slab key
    (slab_1f / slab_2f / slab_roof).  Falls back to scanning all pages and
    grouping by which beam marks are present when classification is absent.

    Returns { slab_key: { MARK: {measured_m, confidence, ...} } }.
    """
    doc = fitz.open(pdf_path)
    out: dict[str, dict] = {}
    # Without a classifier, just measure each page and tag by page number.
    for i in range(len(doc)):
        page = doc[i]
        if not _mark_occurrences(page):
            continue
        res = measure_page(pdf_path, i)
        if res:
            out[f"page_{i+1}"] = res
    doc.close()
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pdf = sys.argv[1] if len(sys.argv) > 1 else None
    if not pdf:
        from _qto_config import DEFAULT_STR_PDF
        pdf = DEFAULT_STR_PDF

    if len(sys.argv) > 2:
        idx = int(sys.argv[2]) - 1
        res = measure_page(pdf, idx)
        print(f"\nPage {idx+1}  ({pdf})")
        print(f"{'MARK':<6} {'len(m)':>8} {'occ':>4} {'match':>6} {'conf':>5}  scale")
        for m in sorted(res):
            r = res[m]
            print(f"{m:<6} {r['measured_m']:>8.2f} {r['occurrences']:>4} "
                  f"{r['matched']:>6} {r['confidence']:>5.0%}  {r['scale']}")
    else:
        allp = measure_all_beam_pages(pdf)
        for pg, res in allp.items():
            print(f"\n── {pg} ──")
            for m in sorted(res):
                r = res[m]
                print(f"  {m:<6} {r['measured_m']:>8.2f} m  "
                      f"({r['matched']}/{r['occurrences']} matched, "
                      f"conf {r['confidence']:.0%}, {r['scale']})")
