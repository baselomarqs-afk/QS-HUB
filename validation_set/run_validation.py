"""
QTO validation harness — references real villa projects IN PLACE (no copying,
so the repo stays lean and performance is unaffected).

A project qualifies for validation only if it has all three:
    • architectural drawing  (PDF, name ~ "arch")
    • structural drawing     (PDF, name ~ "str"/"struct")
    • ground-truth BOQ        (Excel, not a system output)

What this does now (cheap, no AI):
    1. Auto-discover qualifying projects under --root.
    2. Parse each ground-truth BOQ into normalized {item: qty}
       (reuses _extract_real_boqs.extract_from_workbook).
    3. Write validation_set/manifest.json (paths + parsed ground truth only).

The heavy drawing→BOQ accuracy run (which calls the AI extractor) is intentionally
opt-in via --run-engine so a full sweep never fires by accident. See README.md.

Usage:
    python validation_set/run_validation.py                 # default root = trainning
    python validation_set/run_validation.py --root "B:\\path\\to\\folder"
"""
import argparse
import json
import os
import re
import sys

_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT_DIR)

from _extract_real_boqs import extract_from_workbook  # reuse the existing BOQ parser

DEFAULT_ROOT = os.environ.get("VALIDATION_ROOT", r"B:\work\trainning")

# Excel files that are OUR system's output, not the human ground-truth BOQ
_SYS_OUTPUT_RX = re.compile(r"qto.?hybrid|hybrid.?test|_qto_test|project_\d+_qto|_qto\.xls", re.I)


def _find(files, *patterns):
    for pat in patterns:
        for f in files:
            if re.search(pat, os.path.basename(f), re.I):
                return f
    return None


def discover(root):
    """Return a list of project dicts with detected arch/str/boq paths."""
    projects = []
    if not os.path.isdir(root):
        return projects
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        if not os.path.isdir(d):
            continue
        files = [os.path.join(d, f) for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        xls = [f for f in files if f.lower().endswith((".xls", ".xlsx"))]

        # Structural abbreviations seen in the wild: str, struct, stc, STC.
        strc = _find(pdfs, r"st[rc]", r"struct")
        # Architectural: arch/architectural/architecture, or an "AR-/AR_/AR " prefix.
        arch = _find([f for f in pdfs if f != strc], r"arch", r"^ar[-_ ]", r"^ar\d")
        # A villa folder holds exactly the two drawings — infer the missing one
        # as "the other PDF" so odd naming never drops a real pair.
        if len(pdfs) == 2:
            if strc and not arch:
                arch = next((f for f in pdfs if f != strc), None)
            elif arch and not strc:
                strc = next((f for f in pdfs if f != arch), None)

        # ground-truth BOQ: drop system outputs; prefer a 'boq'-named file, else the largest
        gt_cands = [f for f in xls if not _SYS_OUTPUT_RX.search(os.path.basename(f))]
        boq = _find(gt_cands, r"boq", r"bill", r"quantit")
        if not boq and gt_cands:
            boq = max(gt_cands, key=lambda f: os.path.getsize(f))

        projects.append({
            "name": name,
            "dir": d,
            "arch_pdf": arch,
            "str_pdf": strc,
            "boq": boq,
            "complete": bool(arch and strc and boq),
        })
    return projects


def main():
    ap = argparse.ArgumentParser(description="QTO validation harness (references files in place).")
    ap.add_argument("--root", default=DEFAULT_ROOT, help="folder whose subfolders are projects")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json"))
    ap.add_argument("--run-engine", action="store_true",
                    help="(heavy, calls AI) run drawings through the engine and score accuracy")
    args = ap.parse_args()

    projects = discover(args.root)
    complete = [p for p in projects if p["complete"]]
    incomplete = [p for p in projects if not p["complete"]]

    print(f"Root: {args.root}")
    print(f"Folders: {len(projects)} | qualifying (arch+str+BOQ): {len(complete)} | incomplete: {len(incomplete)}\n")

    report = []
    for p in complete:
        try:
            gt = extract_from_workbook(p["boq"])
        except Exception as e:
            print(f"[{p['name']}] BOQ parse error: {e}")
            gt = {}
        gt_simple = {k: round(v["qty"], 2) for k, v in gt.items()}
        report.append({
            "name": p["name"],
            "arch_pdf": p["arch_pdf"],
            "str_pdf": p["str_pdf"],
            "boq": p["boq"],
            "boq_item_count": len(gt_simple),
            "boq_items": gt_simple,
        })
        sample = ", ".join(sorted(gt_simple)[:6])
        print(f"[{p['name']:<3}] ground-truth BOQ items: {len(gt_simple):>2}  ({sample}{'...' if len(gt_simple) > 6 else ''})")

    for p in incomplete:
        missing = [k.replace('_pdf', '').replace('boq', 'BOQ') for k in ("arch_pdf", "str_pdf", "boq") if not p[k]]
        print(f"[{p['name']:<3}] SKIP — missing: {', '.join(missing)}")

    manifest = {
        "root": args.root,
        "generated_by": "validation_set/run_validation.py",
        "note": "Drawings/BOQ are referenced in place (never copied) to keep the repo lean.",
        "qualifying_count": len(complete),
        "complete_projects": report,
        "incomplete_projects": [
            {"name": p["name"], "missing": [k for k in ("arch_pdf", "str_pdf", "boq") if not p[k]]}
            for p in incomplete
        ],
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nManifest -> {args.out}  ({len(complete)} validation-ready projects)")

    if args.run_engine:
        print("\n--run-engine requested: the AI accuracy sweep is a separate step "
              "(needs AI_API_KEY and will incur Gemini cost). Not implemented in this cheap pass.")


if __name__ == "__main__":
    main()
