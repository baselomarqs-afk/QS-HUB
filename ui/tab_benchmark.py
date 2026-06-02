"""
تبويب المعايرة — مقارنة نتائج الـ AI بالنطاقات المرجعية
مبنية على 11 مشروع فيلا حقيقية
"""
import streamlit as st
import pandas as pd
import json

from engine.result_validator import (
    validate_quantity,
    validate_all_results,
    get_reference_summary,
    _DB,
)


def render_benchmark_tab():
    st.header(" Benchmark & Validation | المعايرة والتحقق")
    st.caption(
        "Results are validated against **11 real UAE villa BOQ files**. "
        "Each item shows whether the calculated quantity falls within the expected range."
    )

    # ── Reference Database ────────────────────────────────────────────────────
    with st.expander(" Reference Database — 11 Villa Projects", expanded=False):
        st.caption(
            "Ranges extracted from 11 completed UAE villa BOQ files. "
            "Green = your result is within this range."
        )
        ref_rows = get_reference_summary()
        ref_df   = pd.DataFrame(ref_rows)
        st.dataframe(
            ref_df,
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "Min":     st.column_config.NumberColumn(format="%.1f"),
                "Median":  st.column_config.NumberColumn(format="%.1f"),
                "Max":     st.column_config.NumberColumn(format="%.1f"),
                "Std Dev": st.column_config.NumberColumn(format="%.1f"),
            },
        )

    # ── Collect all item results from session state ───────────────────────────
    boq_results: dict = st.session_state.get("boq_item_results", {})

    # Also pull from item-by-item analysis results if present
    all_classified = st.session_state.get("all_classified_pages", [])
    item_results   = {}
    for page in all_classified:
        dtype = page.get("detected_type", "")
        # Scan session state for item_result_{type}_{key} patterns
        for k, v in st.session_state.items():
            if k.startswith(f"item_result_{dtype}_") and isinstance(v, (int, float)):
                item_key = k.replace(f"item_result_{dtype}_", "")
                item_results[item_key] = v

    # Merge
    all_results = {**item_results, **{k: v["quantity"] for k, v in boq_results.items()
                                      if isinstance(v, dict) and "quantity" in v}}

    # ── Combined PCC (UAE BOQ convention: footings + tie beams in one line) ────
    # The reference range for foundation_pcc was extracted from BOQ items that say
    # "100mm PPC under footing & tie beams" — so we compare the SUM of both.
    _pcc_f = all_results.get("foundation_pcc", 0) or 0
    _pcc_t = all_results.get("tie_beam_pcc",   0) or 0
    if _pcc_f > 0 and _pcc_t > 0:
        all_results["pcc_combined"] = round(_pcc_f + _pcc_t, 2)

    # ── Combined Poly Sheet (foundation level + tie beam level) ──────────────
    # UAE BOQ files list polyethylene sheet as one combined item for both levels.
    _poly_f = all_results.get("polyethylene_found", 0) or 0
    _poly_t = all_results.get("poly_sheet_tb",      0) or 0
    if _poly_f > 0 and _poly_t > 0:
        all_results["poly_sheet_combined"] = round(_poly_f + _poly_t, 2)

    if not all_results:
        st.info(
            "No calculated results yet. "
            "Run ** Item Analysis** on your drawings first, then come back here."
        )
        _render_example_check()
        return

    # ── Validation table ──────────────────────────────────────────────────────
    st.markdown("###  Validation Results | نتائج التحقق")
    if "pcc_combined" in all_results or "poly_sheet_combined" in all_results:
        st.info(
            " **UAE BOQ Convention:** Some items are bundled in real BOQ files:\n"
            "- **PCC Total** = footing blinding + tie beam blinding (one line item)\n"
            "- **Poly Sheet Total** = foundation level + tie beam level (one line item)\n"
            "The combined rows validate their sums against the reference ranges."
        )

    rows = []
    ok_count      = 0
    warning_count = 0
    outlier_count = 0
    no_data_count = 0

    for item_key, qty in sorted(all_results.items()):
        v = validate_quantity(item_key, qty)
        ref = v.get("ref") or {}

        status = v["status"]
        if status == "ok":
            ok_count += 1
        elif status in ("low", "high"):
            warning_count += 1
        elif status == "outlier":
            outlier_count += 1
        else:
            no_data_count += 1

        # Human-readable labels for virtual combined keys
        _DISPLAY_NAMES = {
            "pcc_combined":         "PCC Total (Ftg + TB)",
            "poly_sheet_combined":  "Poly Sheet Total (Ftg + TB)",
        }
        display_name = _DISPLAY_NAMES.get(item_key, item_key.replace("_", " ").title())
        rows.append({
            "Item":         display_name,
            "Your Result":  round(qty, 2),
            "Ref Min":      ref.get("min", "—"),
            "Ref Median":   ref.get("median", "—"),
            "Ref Max":      ref.get("max", "—"),
            "Projects":     ref.get("count", "—"),
            "Status":       v["label"],
            "Dev %":        f"{v['pct_dev']:.0f}%" if v["pct_dev"] is not None else "—",
        })

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(" Normal",   ok_count)
    c2.metric(" Watch",    warning_count)
    c3.metric(" Outlier",  outlier_count)
    c4.metric("⚪ No ref",   no_data_count)

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(60 + len(rows) * 35, 600),
        column_config={
            "Your Result": st.column_config.NumberColumn(format="%.2f"),
            "Ref Min":     st.column_config.NumberColumn(format="%.1f"),
            "Ref Median":  st.column_config.NumberColumn(format="%.1f"),
            "Ref Max":     st.column_config.NumberColumn(format="%.1f"),
        },
    )

    # ── Outlier warnings ──────────────────────────────────────────────────────
    outliers = [r for r in rows if "" in r["Status"]]
    warnings_ = [r for r in rows if "" in r["Status"]]

    if outliers:
        st.markdown("---")
        st.markdown("###  Outliers — Double-Check These")
        for r in outliers:
            ref_key = r["Item"].lower().replace(" ", "_")
            ref     = _DB.get(ref_key, {})
            st.error(
                f"**{r['Item']}**: You got `{r['Your Result']}` — "
                f"reference range is `{r['Ref Min']} – {r['Ref Max']}` "
                f"(median `{r['Ref Median']}` from {r['Projects']} projects)"
            )

    if warnings_:
        st.markdown("###  Worth Reviewing")
        for r in warnings_:
            st.warning(
                f"**{r['Item']}**: `{r['Your Result']}` — "
                f"typical range `{r['Ref Min']} – {r['Ref Max']}`, "
                f"deviation `{r['Dev %']}`"
            )

    # ── Confidence score ──────────────────────────────────────────────────────
    if len(all_results) > 0:
        st.markdown("---")
        total_scored = ok_count + warning_count + outlier_count
        if total_scored > 0:
            confidence = round((ok_count + 0.5 * warning_count) / total_scored * 100)
            color = "" if confidence >= 75 else "" if confidence >= 50 else ""
            st.metric(
                label=f"{color} Overall Confidence Score",
                value=f"{confidence}%",
                help=(
                    "Based on how many of your results fall within the reference ranges "
                    "from 11 real UAE villa projects. "
                    "100% = all results match historical data perfectly."
                ),
            )


def _render_example_check():
    """Demo validator so user can try it without real results."""
    st.markdown("---")
    st.markdown("###  Try the Validator | جرّب المدقق")
    col1, col2 = st.columns(2)
    with col1:
        item_opts = [k.replace("_", " ").title() for k in _DB.keys()]
        chosen = st.selectbox("Select item", item_opts, key="bench_demo_item")
        item_key = chosen.lower().replace(" ", "_")
    with col2:
        demo_qty = st.number_input("Enter a quantity to check", min_value=0.0,
                                   value=0.0, step=1.0, key="bench_demo_qty")

    if demo_qty > 0:
        v   = validate_quantity(item_key, demo_qty)
        ref = v.get("ref") or {}
        st.markdown(f"**Result:** {v['label']}")
        if ref:
            st.caption(
                f"Reference from {ref['count']} projects: "
                f"min {ref['min']} · median {ref['median']} · max {ref['max']} {ref['unit'].upper()}"
            )
            if v["pct_dev"] is not None:
                st.caption(f"Your value deviates **{v['pct_dev']:.0f}%** from the median.")
