"""
Score a QTO output against a ground-truth BOQ, item by item.

Both files are parsed with the existing _extract_real_boqs.extract_from_workbook,
which fuzzy-maps construction descriptions to canonical item keys and reads the
quantity (m3/m2/no) — so it works on human BOQs and on our own xlsx exports.

Usage:
    # explicit files
    python validation_set/score.py --gt "ground_truth.xlsx" --pred "system_output.xlsx"
    # or point at a project folder (auto-detects ground-truth BOQ + a *_QTO/_TEST output)
    python validation_set/score.py --project "B:\\work\\trainning\\1"
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _extract_real_boqs import extract_from_workbook

_SYS_RX = re.compile(r"qto.?hybrid|hybrid.?test|_qto_test|project_\d+_qto|_qto\.xls", re.I)


def _qty(path):
    return {k: v["qty"] for k, v in extract_from_workbook(path).items()}


def _auto(project_dir):
    xls = [os.path.join(project_dir, f) for f in os.listdir(project_dir)
           if f.lower().endswith((".xls", ".xlsx"))]
    pred = next((x for x in xls if _SYS_RX.search(os.path.basename(x))), None)
    gts = [x for x in xls if x != pred]
    gt = next((x for x in gts if re.search(r"boq|bill|quantit", os.path.basename(x), re.I)), None)
    if not gt and gts:
        gt = max(gts, key=os.path.getsize)
    return gt, pred


def score(gt_path, pred_path):
    gt, pred = _qty(gt_path), _qty(pred_path)
    keys = sorted(set(gt) | set(pred))
    rows, devs = [], []
    n_ok = n_close = n_off = n_missing = n_extra = 0
    for k in keys:
        g, p = gt.get(k), pred.get(k)
        if g and p:
            dev = abs(p - g) / g * 100
            devs.append(dev)
            tag = "OK" if dev < 10 else ("CLOSE" if dev < 25 else "OFF")
            n_ok += dev < 10
            n_close += 10 <= dev < 25
            n_off += dev >= 25
            rows.append((k, g, p, f"{dev:5.1f}%", tag))
        elif g and not p:
            n_missing += 1
            rows.append((k, g, None, "  -  ", "MISSING/0"))
        else:
            n_extra += 1
            rows.append((k, None, p, "  -  ", "EXTRA"))
    return rows, {
        "gt_items": len(gt), "pred_items": len(pred),
        "ok": n_ok, "close": n_close, "off": n_off,
        "missing": n_missing, "extra": n_extra,
        "mean_dev": round(sum(devs) / len(devs), 1) if devs else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gt")
    ap.add_argument("--pred")
    ap.add_argument("--project")
    args = ap.parse_args()

    gt, pred = (args.gt, args.pred)
    if args.project:
        gt, pred = _auto(args.project)
    if not gt or not pred:
        print("Need both a ground-truth and a prediction file "
              "(use --gt/--pred or --project with a folder that has a *_QTO output).")
        return

    print(f"GROUND TRUTH : {os.path.basename(gt)}")
    print(f"PREDICTION   : {os.path.basename(pred)}\n")
    rows, s = score(gt, pred)
    print(f"{'ITEM':<24}{'GROUND':>10}{'SYSTEM':>10}{'DEV':>8}  STATUS")
    print("-" * 62)
    for k, g, p, dev, tag in rows:
        gs = f"{g:.1f}" if g is not None else "-"
        ps = f"{p:.1f}" if p is not None else "-"
        print(f"{k:<24}{gs:>10}{ps:>10}{dev:>8}  {tag}")
    print("-" * 62)
    print(f"Ground-truth items: {s['gt_items']} | system items: {s['pred_items']}")
    print(f"Within 10%: {s['ok']}   within 25%: {s['close']}   off>25%: {s['off']}")
    print(f"System missing/zero: {s['missing']}   system extra: {s['extra']}")
    print(f"Mean abs deviation (on matched items): "
          f"{s['mean_dev']}%" if s['mean_dev'] is not None else "Mean abs deviation: n/a")
    covered = s['ok'] + s['close'] + s['off']
    print(f"\nCOVERAGE: system produced a value for {covered}/{s['gt_items']} ground-truth items.")


if __name__ == "__main__":
    main()
