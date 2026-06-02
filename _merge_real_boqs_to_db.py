"""
Merge extracted real-villa BOQ data into engine/reference_ranges.json.

Pipeline:
    1. Load _extracted_real_boqs.json (built by _extract_real_boqs.py).
    2. For each item, drop projects whose values are outside hard sanity bounds
       (e.g., a "villa" with 55,000 m³ excavation is junk — it was an apartment
       complex misfiled as a villa).
    3. For each item, MERGE the surviving values with the existing reference
       database (we keep the original 11 projects + add new ones).
    4. Recompute min/median/max/mean/stdev.
    5. Write back to engine/reference_ranges.json + backup the old one.

Usage:
    py _merge_real_boqs_to_db.py
    py _merge_real_boqs_to_db.py --dry-run   # show what would change without writing
"""
import os, sys, json, shutil, statistics, argparse
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

EXTRACTED_JSON = r'C:\Users\basel\villa_qto\_extracted_real_boqs.json'
DB_JSON        = r'C:\Users\basel\villa_qto\engine\reference_ranges.json'
BACKUP_DIR     = r'C:\Users\basel\villa_qto\engine\_db_backups'
os.makedirs(BACKUP_DIR, exist_ok=True)


# ── Hard sanity bounds for an INDIVIDUAL UAE villa (G to G+2) ─────────────────
# Anything outside is dropped as bad data — not blended into the DB.
SANITY_BOUNDS = {
    # Earthworks (m3)
    'excavation':           (100, 2500),    # >2500 means apartment/compound
    'backfill':             (200, 2000),
    'road_base':            (10,  300),

    # Substructure (m3)
    'foundation_pcc':       (5,   50),
    'foundation_concrete':  (15,  150),
    'neck_column_concrete': (1,   15),
    'tie_beam_concrete':    (3,   50),
    'wall_footing':         (0.5, 20),
    'strap_beam':           (0.1, 15),       # 1250 m³ strap = typo

    # Superstructure (m3)
    'slab_on_grade':        (10,  80),
    'column_concrete':      (5,   60),
    'beam_concrete':        (5,   50),
    'slab_concrete':        (40,  200),
    'staircase_concrete':   (1,   30),
    'parapet':              (1,   40),

    # Block work (m2)
    'thermal_block':        (50,  800),
    'internal_block':       (40,  900),
    'solid_block':          (40,  700),

    # Finishes (m2)
    'internal_plaster':     (300, 3000),
    'external_plaster':     (200, 2000),
    'ceiling_plaster':      (50,  800),
    'internal_paint':       (300, 2500),
    'external_paint':       (200, 2000),

    # Waterproofing (m2)
    'foundation_bitumen':   (200, 2000),
    'wet_waterproofing':    (10,  150),
    'roof_waterproofing':   (100, 600),

    # Floor finishes
    'granite':              (5,   200),     # m2
    'marble':               (5,   100),     # rm
    'wall_tiles':           (100, 1000),    # m2
    'interlock_paving':     (50,  1500),    # m2
    'skirting':             (10,  600),     # rm

    # Polyethylene (m2) — combined footing+TB level
    'polyethylene':         (200, 800),

    # Compound wall (rm)
    'compound_wall':        (30,  250),

    # Openings
    'door_openings':        (5,   40),      # number of doors
    'window_openings':      (30,  400),     # m2
}


# ── Engine canonical units ────────────────────────────────────────────────────
ITEM_UNITS = {
    'excavation': 'm3', 'backfill': 'm3', 'road_base': 'm3',
    'foundation_pcc': 'm3', 'foundation_concrete': 'm3',
    'neck_column_concrete': 'm3', 'tie_beam_concrete': 'm3',
    'wall_footing': 'm3', 'strap_beam': 'm3',
    'slab_on_grade': 'm3', 'column_concrete': 'm3',
    'beam_concrete': 'm3', 'slab_concrete': 'm3',
    'staircase_concrete': 'm3', 'parapet': 'm3',
    'thermal_block': 'm2', 'internal_block': 'm2', 'solid_block': 'm2',
    'internal_plaster': 'm2', 'external_plaster': 'm2', 'ceiling_plaster': 'm2',
    'internal_paint': 'm2', 'external_paint': 'm2',
    'foundation_bitumen': 'm2', 'wet_waterproofing': 'm2', 'roof_waterproofing': 'm2',
    'granite': 'm2', 'marble': 'rm', 'wall_tiles': 'm2',
    'interlock_paving': 'm2', 'skirting': 'rm',
    'polyethylene': 'm2', 'compound_wall': 'rm',
    'door_openings': 'no', 'window_openings': 'm2',
}


def filter_and_aggregate(extracted: dict) -> dict[str, list[float]]:
    """
    Walk per-project data and bucket per item, filtering by SANITY_BOUNDS.
    Returns {item_key: [filtered_values]}.
    """
    by_project = extracted['by_project']
    clean: dict[str, list[float]] = {}
    rejected: dict[str, list[tuple[str, float]]] = {}

    for proj_name, items in by_project.items():
        for key, info in items.items():
            qty = info['qty']
            bounds = SANITY_BOUNDS.get(key)
            if bounds is None:
                continue  # we don't track this item
            lo, hi = bounds
            if lo <= qty <= hi:
                clean.setdefault(key, []).append(qty)
            else:
                rejected.setdefault(key, []).append((proj_name, qty))

    print(f"\n── Filter Report ──")
    for key in sorted(SANITY_BOUNDS):
        accepted = len(clean.get(key, []))
        rejected_n = len(rejected.get(key, []))
        if accepted + rejected_n == 0: continue
        msg = f"  {key:25s} accepted={accepted:>3}, rejected={rejected_n:>3}"
        if rejected_n:
            samples = ', '.join(f"{n}={q:.0f}" for n, q in rejected[key][:2])
            msg += f"  [rejected: {samples}]"
        print(msg)
    return clean


def merge_into_db(clean: dict[str, list[float]], db: dict) -> tuple[dict, dict]:
    """
    Merge new clean values into the existing DB.

    Strategy: we don't have per-project arrays in the original DB, but we
    DO have the (count, min, max, median, stdev). We treat those as a "prior"
    distribution and SUPPLEMENT (not replace) it with the new values. New
    items not in the DB get added fresh.

    Returns (new_db, change_report).
    """
    new_db = {**db}
    changes = {}

    for key, new_vals in clean.items():
        if not new_vals:
            continue

        unit_canonical = ITEM_UNITS.get(key, db.get(key, {}).get('unit', 'm3'))

        if key in db:
            # Existing item — reconstruct an approximate distribution from
            # (count, min, max, median) and pad to that count, then add new.
            old = db[key]
            old_count = old['count']
            # Approximate the old distribution: use [min, median, median, max] repeated
            approx_old = (
                [old['min']]              * (old_count // 4)
                + [old['median']]         * (old_count // 2)
                + [old['max']]            * (old_count // 4)
            )
            # Pad to exact count with median
            while len(approx_old) < old_count:
                approx_old.append(old['median'])
            combined = approx_old + new_vals
        else:
            combined = list(new_vals)

        if len(combined) < 2:
            continue

        combined.sort()
        n = len(combined)
        median = (combined[n//2] if n % 2 else (combined[n//2 - 1] + combined[n//2]) / 2)
        mean   = sum(combined) / n
        stdev  = statistics.stdev(combined) if n > 1 else 0

        new_entry = {
            'count':  n,
            'min':    round(min(combined), 1),
            'max':    round(max(combined), 1),
            'median': round(median, 1),
            'mean':   round(mean, 1),
            'stdev':  round(stdev, 1),
            'unit':   unit_canonical,
            # Preserve by_villa_type if present in original
            **({'by_villa_type': db[key]['by_villa_type']} if key in db and 'by_villa_type' in db[key] else {})
        }

        # Report
        if key in db:
            old = db[key]
            changes[key] = {
                'before': {'count': old['count'], 'min': old['min'],
                           'median': old['median'], 'max': old['max']},
                'after':  {'count': new_entry['count'], 'min': new_entry['min'],
                           'median': new_entry['median'], 'max': new_entry['max']},
                'new_n':  len(new_vals),
            }
        else:
            changes[key] = {
                'before': None,
                'after':  {'count': new_entry['count'], 'min': new_entry['min'],
                           'median': new_entry['median'], 'max': new_entry['max']},
                'new_n':  len(new_vals),
                'NEW_ITEM': True,
            }
        new_db[key] = new_entry

    return new_db, changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true', help="Don't write, just preview")
    args = ap.parse_args()

    with open(EXTRACTED_JSON, encoding='utf-8') as f:
        extracted = json.load(f)
    with open(DB_JSON, encoding='utf-8') as f:
        db = json.load(f)

    print(f"Loaded {len(extracted['by_project'])} project extractions.")
    print(f"Loaded {len(db)} items from existing reference_ranges.json.\n")

    clean = filter_and_aggregate(extracted)
    new_db, changes = merge_into_db(clean, db)

    print(f"\n── Merge Report ──")
    print(f"{'Item':<25} {'Old N':>5} {'New +':>6} {'Old median':>11} {'New median':>11} {'Status':>10}")
    print('-' * 78)
    for key in sorted(changes):
        c = changes[key]
        old_n = c['before']['count'] if c['before'] else 0
        old_m = f"{c['before']['median']:.1f}" if c['before'] else '—'
        new_m = c['after']['median']
        status = 'NEW' if c.get('NEW_ITEM') else 'updated'
        print(f"{key:<25} {old_n:>5} {c['new_n']:>6} {old_m:>11} {new_m:>11.1f} {status:>10}")

    if args.dry_run:
        print(f"\n(--dry-run set; not writing to disk)")
        return

    # Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'reference_ranges_{ts}.json')
    shutil.copy(DB_JSON, backup_path)
    print(f"\nBackup → {backup_path}")

    with open(DB_JSON, 'w', encoding='utf-8') as f:
        json.dump(new_db, f, indent=2, ensure_ascii=False)
    print(f"Updated → {DB_JSON}")
    print(f"Total items in DB: {len(new_db)}")


if __name__ == '__main__':
    main()
