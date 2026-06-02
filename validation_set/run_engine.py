"""
Run the REAL QTO pipeline end-to-end on one villa's two PDFs and print a BOQ
(Description + Quantity + Unit). Uses the SAME functions the API uses — AI-vision
classification & extraction (Gemini), OpenCV floor-plan CV, PyMuPDF/OCR text, the
healing logic, and the engine formulas. Nothing mocked, nothing modified.

Usage:
    python validation_set/run_engine.py --project "B:\\work\\trainning\\1" --floors 2
    python validation_set/run_engine.py --str STR.pdf --arch ARCH.pdf --floors 2 --out out.xlsx
"""
import argparse
import os
import re
import sys
import tempfile

import numpy as np
from PIL import Image

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

from pdf_engine.pdf_loader import load_pdf_pages, extract_page_text, page_to_pil
from pdf_engine.smart_classifier import PAGE_ITEMS_MAP
from workflow.step2_classify import _classify_single, _ai_classify
from workflow.step3_extract import extract_page
from engine.advanced_cv_extractor import process_floor_plan_image
from engine.project_boq_bridge import build_boq_dataframe_from_project
from api.workflow import reconstruct_project_inputs

FLOOR_TYPES = {"ground_floor_plan", "first_floor_plan", "second_floor_plan", "roof_floor_plan", "setting_out"}


def _save_pages(content, prefix, cache):
    texts = extract_page_text(content)
    pages = load_pdf_pages(content)
    for idx, arr in enumerate(pages):
        pil = page_to_pil(arr)
        w, h = pil.size
        if max(w, h) > 1600:
            s = 1600 / max(w, h)
            pil = pil.resize((int(w * s), int(h * s)))
        pil.save(os.path.join(cache, f"{prefix}_page_{idx}.png"))
    return texts


def _detect(project_dir):
    files = [os.path.join(project_dir, f) for f in os.listdir(project_dir) if os.path.isfile(os.path.join(project_dir, f))]
    pdfs = [f for f in files if f.lower().endswith(".pdf")]
    strc = next((f for f in pdfs if re.search(r"st[rc]|struct", os.path.basename(f), re.I)), None)
    arch = next((f for f in pdfs if f != strc and re.search(r"arch|^ar[-_ ]|^ar\d", os.path.basename(f), re.I)), None)
    if len(pdfs) == 2:
        if strc and not arch: arch = next((f for f in pdfs if f != strc), None)
        elif arch and not strc: strc = next((f for f in pdfs if f != arch), None)
    return strc, arch


def run(str_pdf, arch_pdf, floors):
    cache = tempfile.mkdtemp(prefix="qto_run_")
    str_texts = _save_pages(open(str_pdf, "rb").read(), "str", cache) if str_pdf else []
    arch_texts = _save_pages(open(arch_pdf, "rb").read(), "arch", cache) if arch_pdf else []
    print(f"Loaded pages: structural={len(str_texts)}  architectural={len(arch_texts)}")

    classified = []
    for i, t in enumerate(str_texts):
        classified.append({"pdf": "structural", "page_index": i, "page_num": i + 1, **_classify_single(t, "structural")})
    for i, t in enumerate(arch_texts):
        classified.append({"pdf": "architectural", "page_index": i, "page_num": i + 1, **_classify_single(t, "architectural")})

    from concurrent.futures import ThreadPoolExecutor

    def cls(p):
        # AI-verify EVERY page (matches the API + Streamlit flow)
        prefix = "str" if p["pdf"] == "structural" else "arch"
        ip = os.path.join(cache, f"{prefix}_page_{p['page_index']}.png")
        if os.path.exists(ip):
            try:
                arr = np.array(Image.open(ip))[:, :, ::-1].copy()
                g = _ai_classify(arr, p["pdf"])
                if g:
                    p["detected_type"] = g
                    p["confidence"] = "high(ai)"
                    p["items"] = PAGE_ITEMS_MAP.get(g, {}).get("extract_items", [])
            except Exception as e:
                print(f"   [cls err p{p['page_num']}] {e}")
        return p

    with ThreadPoolExecutor(max_workers=6) as ex:
        classified = list(ex.map(cls, classified))

    ready = [p for p in classified if p.get("detected_type") and p["detected_type"] != "unknown"]
    print(f"\nPages identified ({len(ready)}):")
    for p in ready:
        print(f"   {p['pdf'][:4]:4} p{p['page_num']:<2} -> {p['detected_type']}")

    results = {}

    def ext(p):
        dt = p["detected_type"]
        prefix = "str" if p["pdf"] == "structural" else "arch"
        ip = os.path.join(cache, f"{prefix}_page_{p['page_index']}.png")
        if not os.path.exists(ip):
            return None
        texts = str_texts if p["pdf"] == "structural" else arch_texts
        ptext = texts[p["page_index"]] if p["page_index"] < len(texts) else ""
        try:
            arr = np.array(Image.open(ip))[:, :, ::-1].copy()
            e = extract_page(arr, dt, ptext, 1)
            if dt in FLOOR_TYPES:
                e.update(process_floor_plan_image(ip))
            return f"{p['pdf']}_p{p['page_num']}_{dt}", {**e, **p}
        except Exception as ee:
            return f"{p['pdf']}_p{p['page_num']}_{dt}", {"_ok": False, "_error": str(ee), "drawing_type": dt, **p}

    print("\nExtracting (AI vision + CV)...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        for it in ex.map(ext, ready):
            if it:
                results[it[0]] = it[1]

    state = {"extraction_results": results, "confirmed_auto_data": {}}
    reconstruct_project_inputs(state)
    c = state["confirmed_auto_data"]
    payload = {
        "longest_length": c.get("longest_length"), "longest_width": c.get("longest_width"),
        "plot_area": c.get("plot_area"), "gf_area": c.get("gf_area"),
        "external_perimeter": c.get("external_perimeter"), "ext_perimeter": c.get("ext_perimeter"),
        "roof_perimeter": c.get("roof_perimeter"), "roof_slab_area": c.get("roof_slab_area"),
        "compound_length": c.get("compound_length"), "total_villa_height": c.get("total_villa_height"),
        "parapet_height": c.get("parapet_height", 1.0),
        "excavation_depth": c.get("excavation_depth") or 1.25,
        "neck_column_height": c.get("neck_column_height") or 1.0,
        "solid_block_height": c.get("solid_block_height") or 1.0,
        "staircase_volume_per_level": c.get("staircase_volume_per_level") or 5.2,
        # auto-detect structural levels from the floor plans the AI actually found
        # (works for G, G+1, G+2 ...) — fall back to the --floors hint
        "structural_levels": (len([k for k in (c.get("floors") or {}) if k in ("gf", "1f", "2f")]) or floors),
        "road_base_included": True,
        "gf_height": 4.0, "f1_height": 4.0, "f2_height": 4.0,
        "schedules": c.get("schedules") or {}, "floors": c.get("floors") or {},
        "walls": c.get("walls") or {}, "openings": c.get("openings") or {},
    }
    from engine.project_boq_bridge import compute_all_quantities
    qty_results, _ = compute_all_quantities(payload)
    df, meta = build_boq_dataframe_from_project(payload)
    return df, meta, c, qty_results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--str", dest="strp")
    ap.add_argument("--arch")
    ap.add_argument("--project")
    ap.add_argument("--floors", type=int, default=2)
    ap.add_argument("--out")
    a = ap.parse_args()

    strp, arch = a.strp, a.arch
    if a.project:
        strp, arch = _detect(a.project)
    print(f"STR : {strp}\nARCH: {arch}\n")

    df, meta, confirmed, _qty = run(strp, arch, a.floors)

    print("\n" + "=" * 64)
    print("BOQ OUTPUT (Description | Unit | Quantity)")
    print("=" * 64)
    nonzero = 0
    for _, r in df.iterrows():
        if r.get("_is_header"):
            print(f"\n# {r['Description (English)']}")
            continue
        q = r.get("Quantity") or 0
        flag = "" if (isinstance(q, (int, float)) and q > 0) else "   (0)"
        if isinstance(q, (int, float)) and q > 0:
            nonzero += 1
        print(f"   {str(r['Description (English)'])[:42]:<42} {str(r.get('Unit') or ''):<4} {q}{flag}")

    items = df[df["_is_header"] == False] if "_is_header" in df.columns else df
    print("\n" + "=" * 64)
    print(f"Items total: {len(items)} | with a non-zero quantity: {nonzero}")
    if meta.get("estimates"):
        print(f"Estimated (flagged): {len(meta['estimates'])}")
    if meta.get("needs_input"):
        print(f"Needs input: {meta['needs_input']}")
    print("Key extracted inputs:",
          {k: confirmed.get(k) for k in ("gf_area", "ext_perimeter", "plot_area", "longest_length", "longest_width") if confirmed.get(k)})

    if a.out:
        from utils.exporter import export_boq_to_excel
        with open(a.out, "wb") as f:
            f.write(export_boq_to_excel(df, "Villa"))
        print(f"\nSaved BOQ -> {a.out}")


if __name__ == "__main__":
    main()
