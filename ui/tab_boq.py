"""
تبويب BOQ النهائي - النسخة الكاملة
"""
import os, json
import streamlit as st
import pandas as pd

from engine.smart_calculator import calculate_full_boq
from engine.project_history  import save_project, load_all_projects
from engine.project_boq_bridge import build_boq_dataframe_from_project, load_project
from utils.exporter          import export_boq_to_excel

_PROJECT_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "_project_data.json")


def _project_json_ready() -> bool:
    """True if a _project_data.json with real extracted content exists."""
    if not os.path.exists(_PROJECT_JSON):
        return False
    try:
        with open(_PROJECT_JSON, encoding="utf-8") as f:
            p = json.load(f)
        return bool(p.get("schedules") or p.get("floors"))
    except Exception:
        return False


def _concrete_total_from_df(boq_df) -> float:
    """Sum all m³ rows in a bridge-built BOQ DataFrame (for the summary metric)."""
    try:
        data = boq_df[(boq_df["_is_header"] == False) & (boq_df["Unit"] == "m³")]
        return float(data["Quantity"].sum())
    except Exception:
        return 0.0


def _check_approval_gate() -> bool:
    """
    [W10] Real approval gate. Returns True if it's safe to compute the BOQ.

    Rules:
        - If _project_data.json doesn't exist → ok (legacy manual workflow).
        - If _project_data.json exists and _approved=True → ok.
        - If _project_data.json exists and _approved=False → blocked.
        - Also honors st.session_state['schedules_approved'] as live override.
    """
    if not os.path.exists(_PROJECT_JSON):
        return True
    try:
        with open(_PROJECT_JSON, encoding="utf-8") as f:
            project = json.load(f)
    except Exception:
        return True
    approved_on_disk    = bool(project.get("_approved"))
    approved_in_session = bool(st.session_state.get("schedules_approved"))
    return approved_on_disk or approved_in_session


def render_boq_tab(project: dict):
    st.header(" BOQ Summary | ملخص الكميات")

    # ── [W10] Approval gate ──────────────────────────────────────────────────
    if not _check_approval_gate():
        st.error(
            " **BOQ is locked.**\n\n"
            "You have an auto-extracted `_project_data.json` but you haven't "
            "approved it yet. Go to ** Schedule Review** tab, review the values, "
            "and tick the approval checkbox before computing the BOQ."
        )
        st.info(
            " This gate protects you from running BOQ on un-verified AI output. "
            "If you want to bypass it, manually delete `_project_data.json` "
            "or set `_approved=true` in that file."
        )
        return

    # ── Data Source Selection ──
    has_project = _project_json_ready()
    has_auto    = bool(st.session_state.get("confirmed_auto_data"))

    # Prefer the approved project JSON (single source of truth) when present.
    if has_project:
        options = ["project", "manual"]
    elif has_auto:
        options = ["auto", "manual"]
    else:
        options = ["manual"]

    col_src, col_btn = st.columns([2, 1])
    with col_src:
        source = st.radio(
            "Data Source | مصدر البيانات",
            options=options,
            format_func=lambda x: {
                "project": " Approved Project (from Schedule Review)",
                "auto":    " AI Auto-Extracted Data",
                "manual":  "✏️  Manual Input Data",
            }[x],
            horizontal=True,
            key="boq_source",
        )
    with col_btn:
        calc_btn = st.button(
            " Calculate BOQ | احسب الكميات",
            type="primary",
            use_container_width=True,
            key="btn_calc_boq",
        )

    if calc_btn:
        with st.spinner("Calculating... | جاري الحساب..."):
            if source == "project":
                # Single source of truth: the data the user reviewed & approved.
                project_data = load_project(_PROJECT_JSON)
                boq_df, meta = build_boq_dataframe_from_project(project_data)
                st.session_state["boq_df"]           = boq_df
                st.session_state["boq_calculated"]   = True
                st.session_state["boq_raw_results"]  = {}
                st.session_state["boq_bridge_meta"]  = meta
                st.session_state["boq_source_used"]  = source
            else:
                boq_df, raw_results = calculate_full_boq(project, source=source)
                st.session_state["boq_df"]           = boq_df
                st.session_state["boq_calculated"]   = True
                st.session_state["boq_raw_results"]  = raw_results
                st.session_state["boq_bridge_meta"]  = None
                st.session_state["boq_source_used"]  = source

    boq_df = st.session_state.get("boq_df")
    if boq_df is None:
        st.info(" Click 'Calculate BOQ' to generate quantities.")
        return

    source_used = st.session_state.get("boq_source_used", "manual")
    _src_label = {
        "project": " Approved Project (Schedule Review)",
        "auto":    " AI Auto-Extracted",
        "manual":  "✏️ Manual Input",
    }.get(source_used, "✏️ Manual Input")
    st.caption(f"Showing results from: **{_src_label}**")

    # ── Confirm-list for the approved-project path (the "confirm only what's needed" step) ──
    meta = st.session_state.get("boq_bridge_meta")
    if source_used == "project" and meta:
        if meta.get("estimates"):
            st.warning(
                " **Estimated inputs (not on the drawings — confirm in Schedule Review):**\n\n"
                + "\n".join(f"- {e}" for e in meta["estimates"])
            )
        if meta.get("needs_input"):
            st.error(
                " **Missing inputs (these items will read 0 until provided):**\n\n"
                + "\n".join(f"- {n}" for n in meta["needs_input"])
            )

    # ── Summary Metrics ──
    data_rows   = boq_df[boq_df["_is_header"] == False]
    header_rows = boq_df[boq_df["_is_header"] == True]
    raw         = st.session_state.get("boq_raw_results", {})

    st.success(f"BOQ generated: **{len(data_rows)} items** across **{len(header_rows)} sections**")

    c1, c2, c3, c4 = st.columns(4)

    if source_used == "project":
        sub_conc = _concrete_total_from_df(boq_df)
    else:
        sub_conc = sum(
            v[0] for v in raw.get("sub", {}).values()
            if isinstance(v, tuple) and len(v) > 1 and v[1] == "m³"
        )
    c1.metric("Total Concrete (m³)", f"{sub_conc:.1f}")

    total_finish = 0.0
    for fk in ["gf", "f1", "f2"]:
        fres = raw.get("finish", {}).get(fk, {})
        total_finish += fres.get("dry_floor", 0) + fres.get("wet_floor", 0)
    c2.metric("Total Finish Area (m²)", f"{total_finish:.1f}")
    c3.metric("BOQ Items", len(data_rows))
    c4.metric("Sections",  len(header_rows))

    # ── Full BOQ Table ──
    st.markdown("###  Full BOQ Table")
    show_cols = ["#", "Description (English)", "البيان", "Unit", "Quantity"]

    def _style_row(row):
        is_hdr = boq_df.loc[row.name, "_is_header"] if "_is_header" in boq_df.columns else False
        if is_hdr:
            return ["background-color:#2D6A9F; color:white; font-weight:bold;"] * len(row)
        return [""] * len(row)

    display_df = boq_df.drop(columns=["_is_header"], errors="ignore")
    styled     = display_df[show_cols].style.apply(_style_row, axis=1)

    st.dataframe(
        styled,
        use_container_width=True,
        height=520,
        hide_index=True,
        column_config={
            "#":                     st.column_config.TextColumn("#",                     width="small"),
            "Description (English)": st.column_config.TextColumn("Description (English)", width="large"),
            "البيان":                st.column_config.TextColumn("البيان",                width="medium"),
            "Unit":                  st.column_config.TextColumn("Unit",                  width="small"),
            "Quantity":              st.column_config.NumberColumn("Quantity", format="%.2f", width="small"),
        },
    )

    # ── Pricing (Step 7) ──────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("###  Pricing | التسعير")
    enable_pricing = st.checkbox(
        "Add unit prices & totals | أضف الأسعار والإجماليات",
        key="boq_enable_pricing",
    )

    export_df    = boq_df          # default: quantity-only export
    grand_total  = 0.0

    if enable_pricing:
        currency = st.selectbox("Currency | العملة", ["AED", "USD", "SAR", "EGP"],
                                key="boq_currency")
        st.caption(
            "Enter a unit price for each item. **Total = Quantity × Unit Price.** "
            "Add your own rows at the bottom (blank #) for items not auto-computed."
        )

        price_cols = ["#", "Description (English)", "البيان", "Unit", "Quantity", "Unit Price"]
        price_in   = data_rows[["#", "Description (English)", "البيان", "Unit", "Quantity"]].copy()
        price_in["Unit Price"] = 0.0

        edited_prices = st.data_editor(
            price_in[price_cols],
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="boq_price_editor",
            column_config={
                "#":                     st.column_config.TextColumn("#", width="small", disabled=True),
                "Description (English)": st.column_config.TextColumn("Description (English)", width="large"),
                "البيان":                st.column_config.TextColumn("البيان", width="medium"),
                "Unit":                  st.column_config.TextColumn("Unit", width="small"),
                "Quantity":              st.column_config.NumberColumn("Quantity", format="%.2f", disabled=True),
                "Unit Price":            st.column_config.NumberColumn(f"Unit Price ({currency})", format="%.2f"),
            },
        )

        # Compute totals + build a priced export DataFrame that keeps section headers.
        def _num(x):
            try:    return float(x)
            except (TypeError, ValueError): return 0.0

        # map original item # → (unit price)
        price_by_num = {}
        custom_rows  = []
        for r in edited_prices.to_dict("records"):
            num = str(r.get("#", "")).strip()
            up  = _num(r.get("Unit Price"))
            if num.isdigit():
                price_by_num[num] = up
            elif (r.get("Description (English)") or r.get("البيان")):
                qty = _num(r.get("Quantity"))
                custom_rows.append({
                    "#": "", "Description (English)": r.get("Description (English)", ""),
                    "البيان": r.get("البيان", ""), "Unit": r.get("Unit", ""),
                    "Quantity": qty, "Unit Price": up, "Total": round(qty * up, 2),
                    "_is_header": False,
                })

        priced_rows = []
        for r in boq_df.to_dict("records"):
            if r.get("_is_header"):
                priced_rows.append({**r, "Unit Price": "", "Total": ""})
            else:
                up  = price_by_num.get(str(r.get("#", "")).strip(), 0.0)
                qty = _num(r.get("Quantity"))
                tot = round(qty * up, 2)
                grand_total += tot
                priced_rows.append({**r, "Unit Price": up, "Total": tot})

        if custom_rows:
            priced_rows.append({
                "#": "", "Description (English)": "▌ CUSTOM ITEMS | بنود إضافية",
                "البيان": "", "Unit": "", "Quantity": "", "Unit Price": "", "Total": "",
                "_is_header": True,
            })
            for cr in custom_rows:
                grand_total += cr["Total"]
                priced_rows.append(cr)

        export_df = pd.DataFrame(priced_rows)

        m1, m2 = st.columns(2)
        m1.metric(f"Grand Total ({currency})", f"{grand_total:,.2f}")
        m2.metric("Priced Items", len(price_by_num) + len(custom_rows))

    # ── Export ──
    st.markdown("---")
    col_exp1, col_exp2, col_exp3 = st.columns(3)

    with col_exp1:
        _currency = st.session_state.get("boq_currency", "AED")
        excel_bytes = export_boq_to_excel(
            export_df, project.get("project_name", "Project"), currency=_currency)
        st.download_button(
            " Download Excel BOQ",
            data=excel_bytes,
            file_name=f"BOQ_{project.get('project_name','Project').replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="dl_excel",
        )

    with col_exp2:
        csv_data = data_rows[show_cols].to_csv(index=False)
        st.download_button(
            " Download CSV",
            data=csv_data,
            file_name=f"BOQ_{project.get('project_name','Project')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="dl_csv",
        )

    with col_exp3:
        if st.button(" Save to History", use_container_width=True, key="btn_save_hist"):
            user = st.session_state.get("user", {})
            saved = save_project(
                project.get("project_name", "Project"),
                {"items": data_rows[show_cols].to_dict("records")},
                user_id=user.get("id") if user else None,
            )
            st.success("Saved!") if saved else st.error("Save failed.")

    # ── Project History ──
    st.markdown("---")
    with st.expander(" Project History | سجل المشاريع"):
        user = st.session_state.get("user", {})
        history = load_all_projects(user.get("id") if user else None)
        if history:
            for proj in reversed(history[-10:]):
                col_h1, col_h2 = st.columns([3, 1])
                col_h1.markdown(f"**{proj['name']}** — {proj['date']}")
                n_items = len(proj.get("boq_data", {}).get("items", []))
                col_h2.caption(f"{n_items} items")
        else:
            st.caption("No saved projects yet.")
