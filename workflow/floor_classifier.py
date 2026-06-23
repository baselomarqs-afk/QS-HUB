"""
Deterministic per-floor TYPE detection for UAE villa architectural PDFs.

Goal: tell a *full living floor* apart from a *roof / stair-room-only level*
(very common: the top "floor" of a G+1 / G+2 villa is just the staircase room
on an open roof, NOT a full floor — so it must not generate full-floor block,
plaster and flooring).

Signal (text-layer, no AI): on a floor-PLAN sheet a full floor names living
rooms (bedroom / majlis / living / kitchen / dining …); a roof stair-room level
names none of them (only STAIR / ROOF / parapet) and has no wet rooms.

Returns {'gf':'full','1f':'full','2f':'stair_room', ...} for the floors found.
"""
import re
import fitz

_LIVING = ("BED ROOM", "BEDROOM", "MAJLIS", "MAGLIS", "MAJLES", "LIVING",
           "DINING", "GUEST", "FAMILY", "KITCHEN", "MASTER", "HALL", "SITTING")
_WET = ("TOILET", "BATH", "W.C", "WC", "WASH", "LAUNDRY", "ENSUITE")
_FLOOR_TITLE = re.compile(
    r"(GROUND|FIRST|SECOND|THIRD|ROOF|MEZZANINE)\s+FLOOR\s+PLAN", re.IGNORECASE)
_TITLE_TO_FK = {"GROUND": "gf", "FIRST": "1f", "SECOND": "2f",
                "THIRD": "3f", "MEZZANINE": "mezz", "ROOF": "roof"}
_SIZE_RE = re.compile(r"\d\.\d{2}\s*[xX×]\s*\d\.\d{2}")


def _plan_pages(doc):
    """{fk: best_page_index} — the real plan sheet for each floor label.

    A plan sheet is chosen over elevations/sections that merely mention the same
    floor name: we score each candidate by how much room content it carries.
    """
    best = {}   # fk -> (score, page_index)
    for i in range(len(doc)):
        t = doc[i].get_text("text")
        u = t.upper()
        titles = set(m.group(1).upper() for m in _FLOOR_TITLE.finditer(u))
        if not titles:
            continue
        # a schedule sheet is not a plan
        if len(_SIZE_RE.findall(t)) >= 4 and ("DETAIL" in u or "SCHEDULE" in u):
            continue
        room_score = sum(u.count(k) for k in _LIVING + _WET)
        # When a single sheet legitimately is one floor's plan it usually names
        # exactly one floor; multi-floor titles are elevations/sections.
        for title in titles:
            fk = _TITLE_TO_FK.get(title)
            if not fk:
                continue
            # prefer sheets that name THIS floor alone, and have room content
            score = room_score + (50 if len(titles) == 1 else 0)
            if fk not in best or score > best[fk][0]:
                best[fk] = (score, i)
    return {fk: idx for fk, (score, idx) in best.items()}


def classify_floor_types(pdf_path: str) -> dict:
    """{fk: {'type': 'full'|'stair_room', 'living': int, 'wet': int, 'page': n}}."""
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return {}
    out = {}
    for fk, idx in _plan_pages(doc).items():
        u = doc[idx].get_text("text").upper()
        living = sum(u.count(k) for k in _LIVING)
        wet = sum(u.count(k) for k in _WET)
        # Ground floor is always a full floor. Upper floors with no living rooms
        # AND no wet rooms are stair-room / roof levels.
        if fk == "gf":
            ftype = "full"
        else:
            # A full living floor names several rooms; a roof stair-room level
            # names essentially none (allow 1 stray label) and has no wet rooms.
            ftype = "stair_room" if (living <= 1 and wet == 0) else "full"
        out[fk] = {"type": ftype, "living": living, "wet": wet, "page": idx + 1}
    doc.close()
    return out


def classify_for_project(project_cache: str) -> dict:
    """Merge classification across all cached arch_*.pdf files for a project."""
    import os, glob
    res = {}
    for pdf in sorted(glob.glob(os.path.join(project_cache, "arch_*.pdf"))):
        for fk, info in classify_floor_types(pdf).items():
            # keep the richest reading (a real plan beats an empty mention)
            if fk not in res or info["living"] + info["wet"] > res[fk]["living"] + res[fk]["wet"]:
                res[fk] = info
    return res


if __name__ == "__main__":
    import sys, json
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(classify_floor_types(sys.argv[1]), ensure_ascii=False, indent=2))
