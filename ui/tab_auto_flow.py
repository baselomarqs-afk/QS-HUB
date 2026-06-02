"""
THE system — one screen, 8 steps. Nothing else.

  1. Upload drawings (STR + ARCH)
  2. Classify page names
  3. System connects pages → items, runs OCR / OpenCV / AI Vision and
     EXTRACTS the values the formulas need
  4. Confirm the few values not seen by AI
     (excavation depth · road base y/n · floor heights · levels)
  5. System applies the formulas
  6. Review results — Sub / Super / Arch
  7. Arrange the BOQ (add items · pricing optional)
  8. Download the final Excel
"""
import os, sys, json
import streamlit as st
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

_PROJECT_JSON = os.path.join(ROOT, "_project_data.json")

from engine.project_boq_bridge import (
    load_project, build_inputs, compute_all_quantities,
    build_boq_dataframe_from_project,
)
from engine.item_detection_map import DRAWING_ITEMS_MAP
from engine.result_validator import validate_quantity
from utils.exporter import export_boq_to_excel
from _page_classifier_ai import classify_and_save, OUT_JSON as CLASS_JSON

_TYPE_LABEL = {
    "foundation": "Foundation (footings)", "tie_beam": "Tie Beam",
    "column_schedule": "Column Schedule", "slab_1f": "1st Floor Slab/Beams",
    "slab_2f": "2nd Floor Slab/Beams", "slab_roof": "Roof Slab/Beams",
    "arch_site": "Site / Setting-out", "arch_gf": "Ground Floor Plan",
    "arch_1f": "1st Floor Plan", "arch_2f": "2nd Floor Plan",
    "arch_roof": "Roof Plan", "arch_elevation": "Elevation",
    "arch_section": "Section", "door_schedule": "Door Schedule",
    "window_schedule": "Window Schedule", "unknown": "Unknown / skip",
}

# Which discipline each DRAWING_ITEMS_MAP page belongs to (for step-6 review)
_DISCIPLINE = {
    "foundations": "SUB", "tie_beam": "SUB",
    "upper_columns": "SUPER", "slab_1st": "SUPER", "slab_2nd": "SUPER", "roof_slab": "SUPER",
    "ground_floor_plan": "ARCH", "first_floor_plan": "ARCH", "second_floor_plan": "ARCH",
    "roof_floor_plan": "ARCH", "elevations": "ARCH", "setting_out": "ARCH", "schedules": "ARCH",
}
_STATUS_ICON = {"ok": "", "low": "", "high": "", "outlier": "", "no_data": "⚪"}


def _load() -> dict:
    if not os.path.exists(_PROJECT_JSON):
        return {}
    try:
        with open(_PROJECT_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    with open(_PROJECT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _save_upload(uploaded, tag: str) -> str:
    path = os.path.join(ROOT, f"_uploaded_{tag}.pdf")
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    return path


def _api_key() -> str:
    return (os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("AI_API_KEY")
            or st.session_state.get("af_api_key", ""))


def render_auto_flow_tab():
    st.markdown("# 🏗️ THE QS HUB — Auto BOQ | جدول الكميات الآلي")

    # ── STEP 1 — UPLOAD ──────────────────────────────────────────────────────
    st.markdown("## 1️⃣ Upload drawings | رفع الرسومات")
    c1, c2 = st.columns(2)
    with c1:
        str_up = st.file_uploader("STR PDF (Structural) | الإنشائي", type="pdf", key="af_str")
    with c2:
        arch_up = st.file_uploader("ARCH PDF (Architectural) | المعماري", type="pdf", key="af_arch")

    if not _api_key():
        st.session_state["af_api_key"] = st.text_input(
            "API key (session only)", type="password", key="af_key_in")

    if str_up and arch_up:
        st.session_state["af_str_path"]  = _save_upload(str_up, "str")
        st.session_state["af_arch_path"] = _save_upload(arch_up, "arch")
    str_path  = st.session_state.get("af_str_path")
    arch_path = st.session_state.get("af_arch_path")

    # ── STEP 2 — CLASSIFY PAGES ──────────────────────────────────────────────
    st.markdown("## 2️⃣ Classify page names | تصنيف أسماء الصفحات")
    if st.button(" Classify pages | صنّف الصفحات", key="af_classify",
                 disabled=not (str_path and arch_path and _api_key())):
        with st.status("Classifying every page…") as s:
            classify_and_save([str_path, arch_path], api_key=_api_key())
            s.update(label=" Pages classified", state="complete")
        st.rerun()

    classification = {}
    if os.path.exists(CLASS_JSON):
        try:
            with open(CLASS_JSON, encoding="utf-8") as f:
                classification = json.load(f)
        except Exception:
            classification = {}

    if classification:
        opts = list(_TYPE_LABEL.keys())
        for pdf_path, pages in classification.items():
            if str_path and pdf_path not in (str_path, arch_path):
                continue
            lbl = "STR" if pdf_path == str_path else ("ARCH" if pdf_path == arch_path else os.path.basename(pdf_path))
            st.markdown(f"**{lbl}**")
            df = pd.DataFrame([{
                "Page": int(i) + 1, "Type": info.get("type", "unknown"),
                "Conf": round(float(info.get("confidence", 0)), 2),
            } for i, info in sorted(pages.items(), key=lambda kv: int(kv[0]))])
            ed = st.data_editor(
                df, hide_index=True, use_container_width=True, key=f"af_cls_{lbl}",
                column_config={
                    "Page": st.column_config.NumberColumn("Page", disabled=True, width="small"),
                    "Type": st.column_config.SelectboxColumn("Page Type", options=opts, width="medium"),
                    "Conf": st.column_config.NumberColumn("Conf", format="%.2f", disabled=True, width="small"),
                })
            for r in ed.to_dict("records"):
                idx = str(int(r["Page"]) - 1)
                if idx in classification[pdf_path]:
                    classification[pdf_path][idx]["type"] = r["Type"]
        with open(CLASS_JSON, "w", encoding="utf-8") as f:
            json.dump(classification, f, indent=2, ensure_ascii=False)
        st.caption("✏️ Correct any wrong **Type** — saved automatically.")

    # ── STEP 3 — EXTRACT ─────────────────────────────────────────────────────
    st.markdown("## 3️⃣ Extract values | استخراج القيم")
    st.caption("System connects each page to its items and extracts the values the "
               "formulas need (schedules, areas, openings, measured beam/tie-beam lengths).")
    if st.button(" Extract | استخرج", type="primary", key="af_extract",
                 disabled=not (str_path and arch_path and _api_key() and classification)):
        from _master_extractor import run_pipeline
        with st.status("Extracting…", expanded=True) as status:
            st.write("Reading schedules, areas, openings; measuring lengths…")
            run_pipeline(str_path, arch_path, api_key=_api_key(), skip_classify=True)
            status.update(label=" Extraction complete", state="complete")
        st.rerun()

    data = _load()
    if not data:
        st.info(" Upload → Classify → Extract to continue.")
        return

    # ── STEP 4 — CONFIRM ESSENTIALS (only what AI can't see) ─────────────────
    st.markdown("## 4️⃣ Confirm essentials | تأكيد القيم الأساسية")
    st.caption("Only the few values not visible on the drawings — confirm or adjust.")
    e1, e2, e3 = st.columns(3)
    with e1:
        lv = int(data.get("structural_levels") or 1)
        lv = st.number_input("Structural levels | الأدوار", 1, 5, lv, 1, key="af_lv")
        data["structural_levels"] = int(lv)
        data["villa_type"] = "G" if lv <= 2 else f"G+{lv-2}"
        st.caption(f"→ {data['villa_type']}")
    with e2:
        data["excavation_depth"] = float(st.number_input(
            "Excavation depth (m) | عمق الحفر", 0.5, 4.0,
            float(data.get("excavation_depth") or 1.25), 0.05, key="af_exc"))
        data["parapet_height"] = float(st.number_input(
            "Parapet height (m) | البارابيت", 0.0, 2.0,
            float(data.get("parapet_height") or 1.0), 0.1, key="af_par"))
    with e3:
        data["road_base_included"] = st.checkbox(
            "Road base? | رمل مدموك؟", value=bool(data.get("road_base_included", True)), key="af_rb")
        floors = data.setdefault("floors", {})
        for fk, l in [("gf", "GF height"), ("1f", "1F height"), ("2f", "2F height")]:
            if fk == "gf" or fk in floors:
                cur = float((floors.get(fk, {}) or {}).get("height") or 4.0)
                floors.setdefault(fk, {})["height"] = float(
                    st.number_input(f"{l} (m)", 2.5, 6.0, cur, 0.1, key=f"af_h_{fk}"))
    _save(data)

    try:
        _, _, meta = build_inputs(data)
        if meta.get("estimates"):
            st.warning(" Estimated: " + "; ".join(meta["estimates"]))
        if meta.get("needs_input"):
            st.error(" Missing: " + "; ".join(meta["needs_input"]))
    except Exception:
        pass

    # ── STEP 5 — APPLY FORMULAS ──────────────────────────────────────────────
    st.markdown("## 5️⃣ Apply formulas | تطبيق المعادلات")
    if st.button(" Calculate | احسب", type="primary", key="af_calc"):
        st.session_state["af_calculated"] = True
    if not st.session_state.get("af_calculated"):
        st.info(" Click to run the formulas on the extracted + confirmed values.")
        return

    project    = _load()
    results, _ = compute_all_quantities(project)
    villa      = project.get("villa_type")

    # ── STEP 6 — REVIEW: SUB / SUPER / ARCH ──────────────────────────────────
    st.markdown("## 6️⃣ Review results | مراجعة النتائج")

    grouped = {"SUB": [], "SUPER": [], "ARCH": []}
    n = 1
    for page_key, page in DRAWING_ITEMS_MAP.items():
        disc = _DISCIPLINE.get(page_key, "ARCH")
        for item in page["items"]:
            q = results.get(item["key"], 0.0)
            v = validate_quantity(item["key"], q, villa_type=villa)
            grouped[disc].append({
                "#": n, "Item": item["name_en"], "البند": item["name_ar"],
                "Unit": item["unit"], "Qty": round(float(q or 0), 2),
                "✓": _STATUS_ICON.get(v["status"], "⚪"),
            })
            n += 1

    titles = {"SUB": "️ Sub-Structure | تحت الأرض",
              "SUPER": " Super-Structure | العلوية",
              "ARCH": " Architectural / Finishes | معماري وتشطيبات"}
    for disc in ("SUB", "SUPER", "ARCH"):
        rows = grouped[disc]
        sub_total = sum(r["Qty"] for r in rows if r["Unit"] == "m³")
        with st.expander(f"{titles[disc]}  —  {len(rows)} items"
                         + (f"  ·  {sub_total:.1f} m³" if sub_total else ""), expanded=True):
            st.dataframe(
                pd.DataFrame(rows), hide_index=True, use_container_width=True,
                column_config={
                    "#":     st.column_config.NumberColumn("#", width="small"),
                    "Item":  st.column_config.TextColumn("Item", width="large"),
                    "البند": st.column_config.TextColumn("البند", width="medium"),
                    "Unit":  st.column_config.TextColumn("Unit", width="small"),
                    "Qty":   st.column_config.NumberColumn("Qty", format="%.2f", width="small"),
                    "✓":     st.column_config.TextColumn("✓", width="small"),
                })
    st.caption(" normal ·  watch ·  verify · ⚪ no reference")

    # ── STEP 7 — ARRANGE BOQ + PRICING (optional) ────────────────────────────
    st.markdown("## 7️⃣ Arrange BOQ | ترتيب جدول الكميات")
    boq_df, _ = build_boq_dataframe_from_project(project)
    export_df, currency = boq_df, "AED"

    if st.checkbox(" Add pricing (optional) | تسعير (اختياري)", key="af_price_on"):
        currency = st.selectbox("Currency | العملة", ["AED", "USD", "SAR", "EGP"], key="af_cur")
        drows = boq_df[boq_df["_is_header"] == False]
        pin = drows[["#", "Description (English)", "البيان", "Unit", "Quantity"]].copy()
        pin["Unit Price"] = 0.0
        ed = st.data_editor(
            pin, hide_index=True, use_container_width=True, num_rows="dynamic",
            key="af_price_ed",
            column_config={
                "#":          st.column_config.TextColumn("#", disabled=True, width="small"),
                "Quantity":   st.column_config.NumberColumn("Quantity", format="%.2f", disabled=True),
                "Unit Price": st.column_config.NumberColumn(f"Unit Price ({currency})", format="%.2f"),
            })

        def _num(x):
            try:    return float(x)
            except (TypeError, ValueError): return 0.0
        by_num, customs, grand = {}, [], 0.0
        for r in ed.to_dict("records"):
            nn = str(r.get("#", "")).strip(); up = _num(r.get("Unit Price"))
            if nn.isdigit():
                by_num[nn] = up
            elif r.get("Description (English)") or r.get("البيان"):
                q = _num(r.get("Quantity"))
                customs.append({"#": "", "Description (English)": r.get("Description (English)", ""),
                                "البيان": r.get("البيان", ""), "Unit": r.get("Unit", ""),
                                "Quantity": q, "Unit Price": up, "Total": round(q*up, 2), "_is_header": False})
        priced = []
        for r in boq_df.to_dict("records"):
            if r.get("_is_header"):
                priced.append({**r, "Unit Price": "", "Total": ""})
            else:
                up = by_num.get(str(r.get("#", "")).strip(), 0.0)
                q = _num(r.get("Quantity")); t = round(q*up, 2); grand += t
                priced.append({**r, "Unit Price": up, "Total": t})
        if customs:
            priced.append({"#": "", "Description (English)": "▌ CUSTOM ITEMS | بنود إضافية",
                           "البيان": "", "Unit": "", "Quantity": "", "Unit Price": "", "Total": "", "_is_header": True})
            for cr in customs:
                grand += cr["Total"]; priced.append(cr)
        export_df = pd.DataFrame(priced)
        st.metric(f"Grand Total ({currency})", f"{grand:,.2f}")

    # ── STEP 8 — DOWNLOAD EXCEL ──────────────────────────────────────────────
    st.markdown("## 8️⃣ Download Excel | تحميل الملف")
    xls = export_boq_to_excel(export_df, project.get("villa_type", "Villa"), currency=currency)
    st.download_button(
        " Download Excel BOQ | حمّل Excel", data=xls,
        file_name=f"BOQ_{project.get('villa_type','Villa')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary", use_container_width=True, key="af_dl")
