"""Headless full-pipeline run on any STR+ARCH pair. Usage: py _run_project.py STR ARCH"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")

from pdf_engine.pdf_loader   import load_pdf_pages, extract_page_text
from workflow.step2_classify import _classify_single, _ai_classify
from workflow.step3_extract  import extract_page
from workflow.step5_calculate import _build_floor_slabs
from engine.substructure     import calc_all_substructure
from engine.superstructure   import calc_all_superstructure
from engine.finishes         import calc_villa_finishes
from engine.openings         import calc_doors, calc_windows
from engine.boq_builder      import build_boq_dataframe

STR  = sys.argv[1]
ARCH = sys.argv[2]
GF_H = F1_H = F2_H = 4.0
EXC_DEPTH = 1.25

str_b, arch_b = open(STR, "rb").read(), open(ARCH, "rb").read()
str_pages,  str_texts  = load_pdf_pages(str_b),  extract_page_text(str_b)
arch_pages, arch_texts = load_pdf_pages(arch_b), extract_page_text(arch_b)

classified = []
for i, t in enumerate(str_texts):
    classified.append({"pdf": "structural", "page_index": i, "page_num": i + 1, **_classify_single(t, "structural")})
for i, t in enumerate(arch_texts):
    classified.append({"pdf": "architectural", "page_index": i, "page_num": i + 1, **_classify_single(t, "architectural")})

# vision-verify every page
for p in classified:
    src = str_pages if p["pdf"] == "structural" else arch_pages
    g = _ai_classify(src[p["page_index"]], p["pdf"])
    if g:
        p["detected_type"] = g

print("══ CLASSIFICATION ══")
for p in classified:
    print(f"  {p['pdf'][:4].upper():4s} P{p['page_num']:2d} -> {p['detected_type']}")

# auto floor count: 3 if any 2nd-floor evidence, else 2
types = {p["detected_type"] for p in classified}
NUM_FLOORS = 3 if (types & {"second_floor_plan", "columns_2f", "slab_2f"}) else 2
print(f"\nDetected NUM_FLOORS = {NUM_FLOORS}")

ready = [p for p in classified if p["detected_type"] != "unknown"]
print(f"\n══ EXTRACTION ({len(ready)} pages) ══")
results = {}
for p in ready:
    src = str_pages if p["pdf"] == "structural" else arch_pages
    r = extract_page(src[p["page_index"]], p["detected_type"], "")
    results[f"{p['pdf']}_p{p['page_num']}_{p['detected_type']}"] = {**r, **p}
    print(f"  {p['detected_type']:18s} P{p['page_num']:2d} -> {'ok' if r.get('_ok') else 'ERR'}")

# ── ONE shared path: identical to the Streamlit UI (compute_boq) ──────────────
from workflow.step5_calculate import compute_boq
out = compute_boq(results, num_floors=NUM_FLOORS,
                  heights={"gf": GF_H, "f1": F1_H, "f2": F2_H}, areas=None)
boq = out["boq_df"]
print(f"\n══ FULL BOQ — {(boq['_is_header']==False).sum()} items ══")
print(boq.drop(columns=["_is_header"]).to_string(index=False))
