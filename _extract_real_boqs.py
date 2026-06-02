"""
Extract item quantities from real completed villa BOQ files
(DONE PAYMENT folder + verified single-villa projects from downloads).

Strategy
--------
1) Walk a curated list of BOQ Excel files (only G+1 / G+1+Roof villas).
2) For each file, scan every row, fuzzy-match the description against the
   canonical item keys in our engine (excavation, foundation_pcc, etc.).
3) Read qty + unit, validate it's in the right unit (m³ / m² / no.).
4) Aggregate per item across all projects.
5) Output `_extracted_real_boqs.json` with raw values + per-project breakdown
   for traceability (so we can re-build reference_ranges.json with confidence).

Usage:
    py _extract_real_boqs.py
"""
import os, sys, re, json, glob, openpyxl
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

# ── Curated source files ─────────────────────────────────────────────────────
DONE_PAYMENT = r'B:\work\projects estimation\projects\new quasis ALI\DONE\DONE PAYMENT'
DOWNLOADS    = r'B:\work\projects estimation\projects\downloads'

# Folders to SKIP — not villas
SKIP_DP   = {'STR ONLY'}                              # warehouse
SKIP_DL   = {'16 villas', 'brahim', 'G+4', '11_TENDER',
             '2. Tender Documents', 'Swimming Pool Design',
             '20251023 Submission to QS Consultant', 'eng a7md 3',
             'eng ahmed 2', 'Swimming Pool Design', 'service block ready package',
             'ware house', '00001 Retender Documents', '2',
             'TransferNow-20260312XHzXW2Gj'}


def collect_villa_boqs() -> list[tuple[str, str]]:
    """Return [(project_name, boq_xlsx_path), ...] for villa-only BOQs."""
    out = []

    # 1) DONE PAYMENT — prefer 'boq detailed.xlsx', else 'final BOQ*.xlsx'
    for folder in sorted(os.listdir(DONE_PAYMENT)):
        if folder in SKIP_DP: continue
        fp = os.path.join(DONE_PAYMENT, folder)
        if not os.path.isdir(fp): continue
        for pat in ('boq detailed.xlsx', 'final BOQ*.xlsx', 'FINAL BOQ*.xlsx',
                    'Final Boq*.xlsx'):
            hits = glob.glob(os.path.join(fp, '**', pat), recursive=True)
            if hits:
                out.append((folder, hits[0]))
                break

    # 2) downloads — only verified single-villa folders
    verified_villas = ['ali', 'new villa', 'jhangir', 'jhangir 4',
                       'new villa mode', 'shj-102', 'sameer', 'new client',
                       'new projects', 'JH']
    for folder in verified_villas:
        fp = os.path.join(DOWNLOADS, folder)
        if not os.path.isdir(fp): continue
        for pat in ('BOQ.xlsx', 'Villa  BOQ.xlsx', 'BOQ.xls'):
            hits = glob.glob(os.path.join(fp, '**', pat), recursive=True)
            if hits:
                out.append((f'downloads/{folder}', hits[0]))
                break
    return out


# ── Item key mapping (BOQ description regex → canonical key) ─────────────────
# Each rule: (regex, canonical_key, expected_unit)
ITEM_RULES = [
    (r'\bexc?[a]v[ae]tion',                'excavation',          'm3'),
    (r'\b(back\s*fil+ing|backfill)\b',     'backfill',            'm3'),
    (r'\broad\s*base\b',                   'road_base',           'm3'),

    (r'PPC|PCC.*under.*footing|100\s*mm.*PPC|PCC.*under.*tie',
                                            'foundation_pcc',     'm3'),
    (r'(anti.?term[ia]te|polyth[ye]l?ene|polyethelene|poly\s*sheet)',
                                            'polyethylene',       'm2'),
    (r'R\.?C\.?C\.?\s*footing',            'foundation_concrete', 'm3'),
    (r'R\.?C\.?C\.?.*neck\s*column',       'neck_column_concrete','m3'),
    (r'R\.?C\.?C\.?.*tie\s*beam|TIE\s*Beam','tie_beam_concrete',  'm3'),
    (r'solid\s*block.*(under|tie\s*beam|step)','solid_block',     'm2'),
    (r'wall\s*footing',                    'wall_footing',        'm3'),
    (r'strap\s*beam',                      'strap_beam',          'm3'),

    (r'(slab\s*on\s*grade|10\s*cm.*slab.*grade|S\.?O\.?G\.?)',
                                            'slab_on_grade',      'm3'),
    (r'R\.?C\.?C\.?\s*columns?\b',         'column_concrete',     'm3'),
    (r'R\.?C\.?C\.?\s*beams?\b',           'beam_concrete',       'm3'),
    (r'R\.?C\.?C\.?\s*slabs?\b',           'slab_concrete',       'm3'),
    (r'(staircase|stair\s*case)',          'staircase_concrete',  'm3'),
    (r'(parapet|coping\s*beam)',           'parapet',             'm3'),

    (r'(insulat.*block|thermal\s*block|25\s*cm.*block.*parapet)',
                                            'thermal_block',      'm2'),
    (r'(20\s*cm.*hollow|hollow\s*block.*internal|internal\s*wall.*block)',
                                            'internal_block',     'm2'),

    (r'plaster.*internal',                 'internal_plaster',    'm2'),
    (r'plaster.*external',                 'external_plaster',    'm2'),
    (r'ceiling.*spray\s*plaster|spray.*ceiling','ceiling_plaster','m2'),
    (r'paint.*internal',                   'internal_paint',      'm2'),
    (r'paint.*external',                   'external_paint',      'm2'),

    (r'(bet?umin?e|bitumen|bitumin).*sub.?structure|bet?umin?e.*2.*coats',
                                            'foundation_bitumen', 'm2'),
    (r'wet.*area.*water.?proof',           'wet_waterproofing',   'm2'),
    (r'roof.*water.?proof',                'roof_waterproofing',  'm2'),

    (r'(skirting|sk?irting)',              'skirting',            'rm'),
    (r'(granite)',                         'granite',             'm2'),
    (r'(marble)',                          'marble',              'rm'),
    (r'wall\s*tile',                       'wall_tiles',          'm2'),
    (r'floor.*tile|interlock\s*tile',      'interlock_paving',    'm2'),

    (r'compound\s*wall',                   'compound_wall',       'rm'),
    (r'(wooden|wood)\s*door',              'door_openings',       'no'),
    (r'(window|aluminum.*window|aluminium.*window)','window_openings','m2'),
]


def normalize_unit(unit: str) -> str:
    """Canonical units. 'm3', 'm2', 'rm' (running meter), 'no'."""
    if not unit: return ''
    u = str(unit).lower().strip().replace('.', '').replace(' ', '')
    if u in ('m3', 'mᶾ', 'm³', 'cum', 'cu.m', 'cubicmeter'): return 'm3'
    if u in ('m2', 'm²', 'sqm', 'sq.m', 'squaremeter'):      return 'm2'
    if u in ('rm', 'lm', 'm1', 'm', 'lin.m', 'linearmeter'): return 'rm'
    if u in ('no', 'nos', 'no.', 'pcs', 'pc', 'each', 'ea'): return 'no'
    if u in ('ls', 'lsum', 'lumpsum', 'l.s'):                return 'ls'
    return u


def match_item(description: str) -> tuple[str | None, str | None]:
    """Return (canonical_key, expected_unit) or (None, None)."""
    if not description: return None, None
    d = description.lower()
    for rx, key, unit in ITEM_RULES:
        if re.search(rx, d, re.IGNORECASE):
            return key, unit
    return None, None


# ── Excel parser ─────────────────────────────────────────────────────────────
def extract_from_workbook(path: str) -> dict:
    """Extract {item_key: qty} from a BOQ workbook."""
    out = {}
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as e:
        print(f"  ERR opening {path}: {e}")
        return {}

    # Try every sheet
    for sh in wb.sheetnames:
        ws = wb[sh]
        for row in ws.iter_rows(values_only=True):
            if not row: continue
            # Find description column (usually col 1 or 2, sometimes shifted)
            cells = [c for c in row if c is not None]
            if len(cells) < 3: continue

            # Strategy: scan each row for description-like text + qty + unit pattern
            for idx, cell in enumerate(cells):
                if not isinstance(cell, str): continue
                if len(cell) < 10: continue        # too short to be a description
                key, expected_unit = match_item(cell)
                if not key: continue

                # Look ahead in this row for qty + unit
                rest = cells[idx+1:]
                qty, unit = None, None
                for j, v in enumerate(rest):
                    if isinstance(v, (int, float)) and v > 0:
                        qty = float(v)
                        # Next cell after qty is usually unit
                        if j+1 < len(rest) and isinstance(rest[j+1], str):
                            unit = normalize_unit(rest[j+1])
                        break

                if qty is None: continue
                if unit and expected_unit and unit != expected_unit:
                    continue   # unit mismatch — likely a row in different category

                # Skip suspicious values
                if qty < 0.1 or qty > 100000:
                    continue

                # Keep the FIRST occurrence per key (sub-structure rows come first)
                if key not in out:
                    out[key] = {'qty': qty, 'unit': unit or expected_unit}
                # For internal_block / external_plaster etc, sum if multiple floors
                elif key in ('internal_block', 'thermal_block', 'internal_plaster',
                             'external_plaster', 'internal_paint', 'external_paint',
                             'wall_tiles', 'interlock_paving', 'skirting'):
                    out[key]['qty'] += qty
    wb.close()
    return out


# ── Driver ───────────────────────────────────────────────────────────────────
def main():
    sources = collect_villa_boqs()
    print(f"Processing {len(sources)} villa BOQ files...\n")

    by_project: dict[str, dict] = {}
    aggregate:  dict[str, list[float]] = defaultdict(list)

    for name, path in sources:
        print(f"  [{name}]")
        items = extract_from_workbook(path)
        if not items:
            print(f"    (no items extracted — skipping)")
            continue
        by_project[name] = items
        for key, info in items.items():
            aggregate[key].append(info['qty'])
            print(f"    {key:25s} {info['qty']:>8.1f} {info['unit']}")

    # ── Summary stats ────────────────────────────────────────────────────────
    summary = {}
    for key, vals in aggregate.items():
        if len(vals) < 2:
            summary[key] = {'count': len(vals), 'values': vals, 'note': 'too few'}
            continue
        vals_sorted = sorted(vals)
        n = len(vals_sorted)
        median = (vals_sorted[n//2] if n % 2 else (vals_sorted[n//2 - 1] + vals_sorted[n//2]) / 2)
        mean   = sum(vals_sorted) / n
        var    = sum((v - mean) ** 2 for v in vals_sorted) / n
        stdev  = var ** 0.5
        summary[key] = {
            'count':  n,
            'min':    round(min(vals_sorted), 1),
            'max':    round(max(vals_sorted), 1),
            'median': round(median, 1),
            'mean':   round(mean, 1),
            'stdev':  round(stdev, 1),
            'values': vals_sorted,
        }

    out_path = r'C:\Users\basel\villa_qto\_extracted_real_boqs.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'sources':     sources,
            'by_project':  by_project,
            'summary':     summary,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"SUMMARY (from {len(by_project)} villa projects)")
    print(f"{'='*70}")
    print(f"{'Item':<25} {'N':>3} {'min':>8} {'median':>8} {'max':>8} {'mean±sd':>14}")
    print('-' * 70)
    for k in sorted(summary):
        s = summary[k]
        if s.get('note'): continue
        print(f"{k:<25} {s['count']:>3} {s['min']:>8.1f} {s['median']:>8.1f} "
              f"{s['max']:>8.1f}   {s['mean']:>6.1f}±{s['stdev']:>4.1f}")

    print(f"\nSaved → {out_path}")


if __name__ == '__main__':
    main()
