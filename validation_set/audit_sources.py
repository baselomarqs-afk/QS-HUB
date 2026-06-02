"""
Honest, recursive audit of source folders to find villa projects usable as
drawing->BOQ validation pairs.

For every project (immediate subfolder of each root) it searches ALL nested
folders and reports, with evidence (the actual filenames matched):
    • architectural drawing PDF   (arch | architectural | AR- prefix)
    • structural drawing PDF      (str | stc | struct)
    • ground-truth BOQ Excel      (not a system output)

Verdicts:
    QUALIFIED     — has arch + str + BOQ  (ready validation pair)
    NEEDS REVIEW  — has BOQ + drawings but arch/str couldn't be auto-identified
                    (e.g. one combined drawing set, or unusual naming) -> human check
    INCOMPLETE    — missing drawings or BOQ entirely

No files are read except listing; BOQs are only detected, not parsed (fast).
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

ROOTS = [
    r"B:\work\projects estimation\projects\new quasis ALI\DONE\DONE PAYMENT",
    r"B:\work\projects estimation\projects\unknown jobs\id\Going on",
    r"B:\work\projects estimation\projects\unknown jobs\id\done\done payment",
]

ARCH_RX = re.compile(r"arch|architect|^ar[-_ ]|\bar[-_ ]\d", re.I)
STR_RX  = re.compile(r"\bst[rc]|st[rc][-_ 0-9]|struct|structur", re.I)
SYS_RX  = re.compile(r"qto.?hybrid|hybrid.?test|_qto_test|project_\d+_qto|_qto\.xls", re.I)
# spreadsheets that are clearly not a BOQ
NOTBOQ_RX = re.compile(r"schedule|reinforc|rebar|bar\s*bend|steel\s*sched", re.I)


def scan(folder):
    pdfs, xls = [], []
    for dp, _dn, fn in os.walk(folder):
        for f in fn:
            ext = os.path.splitext(f)[1].lower()
            if ext == ".pdf":
                pdfs.append(os.path.join(dp, f))
            elif ext in (".xls", ".xlsx"):
                xls.append(os.path.join(dp, f))
    return pdfs, xls


def classify(folder):
    pdfs, xls = scan(folder)
    arch = [p for p in pdfs if ARCH_RX.search(os.path.basename(p))]
    strc = [p for p in pdfs if STR_RX.search(os.path.basename(p))]
    boq  = [x for x in xls if not SYS_RX.search(os.path.basename(x))
            and not NOTBOQ_RX.search(os.path.basename(x))]

    has_a, has_s, has_b = bool(arch), bool(strc), bool(boq)
    if has_a and has_s and has_b:
        verdict = "QUALIFIED"
    elif has_b and (len(pdfs) >= 2 or has_a or has_s):
        verdict = "NEEDS REVIEW"
    else:
        verdict = "INCOMPLETE"
    return {
        "verdict": verdict, "n_pdf": len(pdfs), "n_xls": len(xls),
        "arch": arch[:1], "strc": strc[:1], "boq": boq[:1],
        "has_a": has_a, "has_s": has_s, "has_b": has_b,
    }


def main():
    totals = {"QUALIFIED": 0, "NEEDS REVIEW": 0, "INCOMPLETE": 0}
    grand = 0
    for root in ROOTS:
        print("\n" + "=" * 78)
        print(root)
        print("=" * 78)
        if not os.path.isdir(root):
            print("  [MISSING]"); continue
        for name in sorted(os.listdir(root)):
            d = os.path.join(root, name)
            if not os.path.isdir(d):
                continue
            grand += 1
            r = classify(d)
            totals[r["verdict"]] += 1
            tag = {"QUALIFIED": "[OK ]", "NEEDS REVIEW": "[? ]", "INCOMPLETE": "[XX]"}[r["verdict"]]
            miss = "".join(["A" if not r["has_a"] else "·",
                            "S" if not r["has_s"] else "·",
                            "B" if not r["has_b"] else "·"])
            print(f"\n {tag} {name}   (pdf:{r['n_pdf']} xls:{r['n_xls']}  missing[{miss}])")
            if r["arch"]: print(f"        ARCH: {os.path.basename(r['arch'][0])}")
            if r["strc"]: print(f"        STR : {os.path.basename(r['strc'][0])}")
            if r["boq"]:  print(f"        BOQ : {os.path.basename(r['boq'][0])}")
    print("\n" + "=" * 78)
    print(f"TOTAL projects scanned: {grand}")
    print(f"  QUALIFIED (arch+str+BOQ ready): {totals['QUALIFIED']}")
    print(f"  NEEDS REVIEW (BOQ + drawings, identify sheets): {totals['NEEDS REVIEW']}")
    print(f"  INCOMPLETE (missing drawings or BOQ): {totals['INCOMPLETE']}")
    print(f"  => Usable now or after quick review: {totals['QUALIFIED'] + totals['NEEDS REVIEW']}")


if __name__ == "__main__":
    main()
