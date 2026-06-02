"""
Batch-run the REAL QTO pipeline over several villa projects and score each output
against its ground-truth BOQ at the reference-item level (engine keys -> reference
keys via engine.result_validator._ALIAS, then aggregated).

Usage:
    python validation_set/run_batch.py --root "B:\\work\\trainning" --projects 2 3 4 5 6
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _HERE)

from run_engine import run, _detect
from _extract_real_boqs import extract_from_workbook
from engine.result_validator import _ALIAS

_SYS_RX = re.compile(r"qto.?hybrid|hybrid.?test|_qto_test|project_\d+_qto|_qto\.xls", re.I)


def find_boq(project_dir):
    xls = [os.path.join(project_dir, f) for f in os.listdir(project_dir)
           if f.lower().endswith((".xls", ".xlsx")) and not _SYS_RX.search(f)]
    boq = next((x for x in xls if re.search(r"boq|bill|quantit|sheet", os.path.basename(x), re.I)), None)
    return boq or (max(xls, key=os.path.getsize) if xls else None)


def engine_ref(qty_results):
    out = defaultdict(float)
    for ek, q in (qty_results or {}).items():
        rk = _ALIAS.get(ek)
        if rk and q:
            out[rk] += float(q)
    return dict(out)


def gt_ref(boq_path):
    try:
        return {k: v["qty"] for k, v in extract_from_workbook(boq_path).items()}
    except Exception as e:
        print(f"   GT parse error: {e}")
        return {}


# reference items the engine is supposed to compute (skip GT-only trades like MEP/marble)
ENGINE_KEYS = sorted(set(_ALIAS.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"B:\work\trainning")
    ap.add_argument("--projects", nargs="+", default=["2", "3", "4", "5", "6"])
    ap.add_argument("--out", default=os.path.join(_HERE, "batch_results.json"))
    a = ap.parse_args()

    report = {}
    for pid in a.projects:
        d = os.path.join(a.root, pid)
        if not os.path.isdir(d):
            print(f"[{pid}] missing"); continue
        strp, arch = _detect(d)
        boq = find_boq(d)
        print(f"\n{'='*70}\n[{pid}]  STR={os.path.basename(strp or '-')}  ARCH={os.path.basename(arch or '-')}  BOQ={os.path.basename(boq or '-')}\n{'='*70}")
        try:
            df, meta, c, qty = run(strp, arch, 2)
        except Exception as e:
            print(f"   RUN ERROR: {e}")
            report[pid] = {"error": str(e)}
            continue
        eng = engine_ref(qty)
        gt = gt_ref(boq)
        levels = len([k for k in (c.get("floors") or {}) if k in ("gf", "1f", "2f")])
        nonzero = sum(1 for v in eng.values() if v > 0)
        print(f"   levels detected: {levels} | engine non-zero ref-items: {nonzero} | GT items: {len(gt)}")
        print(f"   {'ITEM':<22}{'ENGINE':>10}{'GT':>10}{'DEV%':>8}")
        rows = {}
        for k in ENGINE_KEYS:
            e, g = eng.get(k, 0.0), gt.get(k)
            if not g and not e:
                continue
            dev = (abs(e - g) / g * 100) if g else None
            rows[k] = {"engine": round(e, 1), "gt": round(g, 1) if g else None, "dev": round(dev, 1) if dev is not None else None}
            ds = f"{dev:6.1f}" if dev is not None else "   -  "
            gs = f"{g:.1f}" if g else "-"
            print(f"   {k:<22}{e:>10.1f}{gs:>10}{ds:>8}")
        report[pid] = {"levels": levels, "engine_nonzero": nonzero, "gt_items": len(gt),
                       "key_inputs": {k: c.get(k) for k in ("gf_area", "ext_perimeter", "plot_area", "longest_length", "longest_width") if c.get(k)},
                       "rows": rows}

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    # ── overall accuracy summary ──
    print(f"\n{'#'*70}\nOVERALL ACCURACY (deviation of engine vs ground truth)\n{'#'*70}")
    buckets = {"<=15%": 0, "<=30%": 0, ">30%": 0, "missing(engine=0,gt>0)": 0}
    total = 0
    for pid, r in report.items():
        for k, v in r.get("rows", {}).items():
            if v["gt"] is None:
                continue
            total += 1
            if v["engine"] == 0:
                buckets["missing(engine=0,gt>0)"] += 1
            elif v["dev"] is not None and v["dev"] <= 15:
                buckets["<=15%"] += 1
            elif v["dev"] is not None and v["dev"] <= 30:
                buckets["<=30%"] += 1
            else:
                buckets[">30%"] += 1
    for k, n in buckets.items():
        pct = (100 * n / total) if total else 0
        print(f"   {k:<28} {n:>3}  ({pct:.0f}%)")
    print(f"   TOTAL comparable item-instances: {total}")
    print(f"\nSaved -> {a.out}")


if __name__ == "__main__":
    main()
