"""
STEP 8 — Download Excel
Final professional BOQ export
"""
import streamlit as st
from utils.exporter import export_boq_to_excel
from workflow.workflow_state import mark_step_done
from datetime import date
from utils.i18n import t
from engine.project_history import save_project
import os
import json
import tempfile
from utils.boq_pdf_generator import create_boq_pdf
from utils.usage import EVENT_EXPORT, EVENT_PROJECT, check_limit, log_usage
from utils.qto_quality import quality_report_markdown, score_boq_quality

ROOT = os.path.dirname(os.path.dirname(__file__))
_PROJECT_JSON = os.path.join(ROOT, "_project_data.json")

def _load() -> dict:
    if not os.path.exists(_PROJECT_JSON):
        return {}
    try:
        with open(_PROJECT_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def render_step8():
    st.markdown(t("download_title"))
    st.balloons()
    st.success(t("download_done"))

    project_name = st.session_state.get("project_name", "Villa Project")
    boq_df       = st.session_state.get("boq_df")
    user         = st.session_state.get("user", {})


    if boq_df is None:
        st.error("No BOQ found. Go back to Step 7.")
        return

    # Load project details for PDF specifications page
    project = _load()

    # Update project with priced BOQ if any changes occurred
    if not st.session_state.get(f"auto_saved_step8_{project_name}"):
        show_cols = ["#", "Description (English)", "البيان", "Unit", "Quantity"]
        data_rows = boq_df[boq_df["_is_header"] == False]
        try:
            # Try to grab the priced version if it exists, otherwise use standard columns
            cols_to_save = show_cols + ["Unit Price", "Total"] if "Total" in boq_df.columns else show_cols
            saved = save_project(
                project_name,
                {"items": data_rows[[c for c in cols_to_save if c in data_rows.columns]].to_dict("records")},
                user_id=user.get("id") if user else None,
            )
            if saved:
                st.session_state[f"auto_saved_step8_{project_name}"] = True
        except Exception as e:
            st.warning(f"Could not auto-save project history: {e}")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Summary")
        display = boq_df[boq_df["_is_header"] == False]
        st.metric("Total Items",    len(display))
        st.metric("Total Sections", len(boq_df[boq_df["_is_header"] == True]))
        st.metric("Generated",      date.today().strftime("%d %B %Y"))
        quality = score_boq_quality(boq_df, st.session_state.get("boq_bridge_meta") or {})
        st.metric("QTO Quality Score", f"{quality['score']}/100")
        st.caption(f"Confidence: {quality['confidence']}")

    with col2:
        st.markdown("### 📥 Downloads")

        # Excel
        ok, msg = check_limit(user, EVENT_EXPORT) if user else (True, "OK")
        if user and ok and not st.session_state.get(f"export_logged_excel_{project_name}"):
            log_usage(user["id"], EVENT_EXPORT, metadata={"project_name": project_name, "format": "xlsx"})
            st.session_state[f"export_logged_excel_{project_name}"] = True
        elif not ok:
            st.warning(msg)
        excel_bytes = export_boq_to_excel(boq_df, project_name)
        st.download_button(
            t("download_btn"),
            data=excel_bytes,
            file_name=f"BOQ_{project_name.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

        # PDF Report
        try:
            pdf_items = []
            for idx, r in enumerate(boq_df.to_dict("records")):
                if r.get("_is_header"):
                    continue
                
                qty = r.get("Quantity")
                try:
                    qty = float(qty) if (qty != "" and qty is not None) else 0.0
                except (TypeError, ValueError):
                    qty = 0.0
                    
                rate = r.get("Unit Price", 0.0)
                try:
                    rate = float(rate) if (rate != "" and rate is not None) else 0.0
                except (TypeError, ValueError):
                    rate = 0.0
                    
                total = r.get("Total", 0.0)
                try:
                    total = float(total) if (total != "" and total is not None) else 0.0
                except (TypeError, ValueError):
                    total = qty * rate
                    
                desc = r.get("Description (English)", "")
                category = "finishing"
                desc_lower = desc.lower()
                if any(k in desc_lower for k in ["excavation", "backfill", "foundation", "footing", "neck", "tie beam", "grade slab"]):
                    category = "substructure"
                elif any(k in desc_lower for k in ["column", "slab", "beam", "staircase", "concrete"]):
                    category = "superstructure"
                elif any(k in desc_lower for k in ["door", "window"]):
                    category = "openings"
                
                pdf_items.append({
                    "code": r.get("#") or f"ITEM-{idx+1}",
                    "desc_en": desc,
                    "name": desc,
                    "unit": r.get("Unit") or "unit",
                    "qty": qty,
                    "rate_aed": rate,
                    "total_aed": total,
                    "category": category
                })
            
            project_info = {
                "plot_area": project.get("plot_area", "N/A"),
                "gf_area": project.get("gf_area", "N/A") or project.get("floors", {}).get("gf", {}).get("area", "N/A"),
                "ext_perimeter": project.get("external_perimeter", "N/A") or project.get("ext_perimeter", "N/A")
            }
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                tmp_path = tmp_pdf.name
            
            create_boq_pdf(
                project_name=f"{project_name}",
                boq_items=pdf_items,
                output_pdf_path=tmp_path,
                project_info=project_info
            )
            
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
                
            try:
                os.remove(tmp_path)
            except Exception:
                pass
                
            st.download_button(
                "📄 Download PDF Report | حمّل تقرير PDF",
                data=pdf_bytes,
                file_name=f"BOQ_Report_{project_name.replace(' ','_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Error generating PDF Report: {e}")

        # CSV
        csv = display[["#","Description (English)","البيان","Unit","Quantity"]].to_csv(index=False)
        st.download_button(
            "💾 Download CSV",
            data=csv,
            file_name=f"BOQ_{project_name.replace(' ','_')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        qto_report = quality_report_markdown(project_name, boq_df, st.session_state.get("boq_bridge_meta") or {})
        st.download_button(
            "Download QTO Quality Report",
            data=qto_report,
            file_name=f"QTO_Quality_{project_name.replace(' ','_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # Start new project
    st.divider()
    if st.button(" Start New Project", use_container_width=True):
        keys_to_clear = [
            "str_pages","arch_pages","classified_pages",
            "extraction_results","sub_results","super_results",
            "finish_results","opening_results","boq_df",
            "calc_done","current_step",
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]
        for step in ["upload","classify","extract","confirm","calculate","review","arrange"]:
            if f"step_done_{step}" in st.session_state:
                del st.session_state[f"step_done_{step}"]
        st.rerun()

