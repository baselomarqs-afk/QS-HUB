"""
Schedule Review tab — the human gate before BOQ computation.

Shows every extracted schedule & base value in an editable table.
The user must approve before the BOQ engine consumes _project_data.json.

Loads from:
    _project_data.json   (output of _master_extractor.py)

Saves to:
    _project_data.json   (with user edits applied)

Sections:
    1. Base data        (plot/areas/perimeters/heights)
    2. Foundations      (footings schedule)
    3. Tie beams        (TB + wall footings)
    4. Columns          (full column schedule)
    5. Slab beams       (1F + Roof + 2F if present)
    6. Doors & windows  (opening schedules)
    7. Wall lengths     (AI estimates + manual override)
    8. Sanity panel     (live warnings)
    9. Approve & Continue button → unlocks BOQ tab
"""
import os, json
import streamlit as st
import pandas as pd

PROJECT_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "_project_data.json")


def _load() -> dict:
    if not os.path.exists(PROJECT_JSON):
        return {}
    try:
        with open(PROJECT_JSON, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    with open(PROJECT_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _sanity_warnings(data: dict) -> list[str]:
    """Re-run sanity check after user edits."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from _master_extractor import sanity_check
        return sanity_check(data)
    except Exception as e:
        return [f"[sanity check error] {e}"]


def render_schedule_review_tab():
    st.header(" Schedule Review | مراجعة الجداول")
    st.caption(
        "Review every extracted value before BOQ computation. "
        "Every cell is editable. Click **Approve & Continue** when done."
    )

    data = _load()
    if not data:
        st.warning(
            "No `_project_data.json` found. "
            "Run the master extractor first:\n\n"
            "`py _master_extractor.py --str path/to/STR.pdf --arch path/to/ARCH.pdf`"
        )
        return

    # ── Step 4: Confirm Essentials (the few values NOT on the drawings) ───────
    st.markdown("###  Confirm Essentials | تأكيد القيم الأساسية")
    st.caption(
        "These few values are not (reliably) on the drawings but the formulas need "
        "them. Confirm or adjust — everything else is auto-extracted below."
    )
    ce1, ce2, ce3 = st.columns(3)
    with ce1:
        lvls = int(data.get("structural_levels") or 1)
        lvls = st.number_input(
            "Structural levels | عدد الأدوار الإنشائية", 1, 5, lvls, 1,
            help="G=1, G+1=2, G+2=3 …", key="ce_levels")
        data["structural_levels"] = int(lvls)
        data["villa_type"] = "G" if lvls <= 2 else f"G+{lvls-2}"
        st.caption(f"→ Villa type: **{data['villa_type']}**")
    with ce2:
        data["excavation_depth"] = float(st.number_input(
            "Excavation depth (m) | عمق الحفر", 0.5, 4.0,
            float(data.get("excavation_depth") or 1.25), 0.05, key="ce_exc"))
        data["parapet_height"] = float(st.number_input(
            "Parapet height (m) | ارتفاع البارابيت", 0.0, 2.0,
            float(data.get("parapet_height") or 1.0), 0.1, key="ce_par"))
    with ce3:
        data["road_base_included"] = st.checkbox(
            "Road base included? | يشمل الرمل المدموك؟",
            value=bool(data.get("road_base_included", True)), key="ce_road")
        floors = data.setdefault("floors", {})
        for fk, lbl in [("gf", "GF height (m)"), ("1f", "1F height (m)"), ("2f", "2F height (m)")]:
            if fk in floors or fk == "gf":
                cur = float((floors.get(fk, {}) or {}).get("height") or 4.0)
                h = st.number_input(f"{lbl} | ارتفاع", 2.5, 6.0, cur, 0.1, key=f"ce_h_{fk}")
                floors.setdefault(fk, {})["height"] = float(h)

    # Surface any low-confidence / estimated values flagged by the bridge.
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from engine.project_boq_bridge import build_inputs
        _, _, _meta = build_inputs(data)
        if _meta.get("needs_input"):
            st.error(" Missing (item will be 0 until provided): "
                     + "; ".join(_meta["needs_input"]))
        if _meta.get("estimates"):
            st.warning(" Estimated (verify below): " + "; ".join(_meta["estimates"]))
    except Exception:
        pass

    st.markdown("---")

    # ── Section 1: Base data ──────────────────────────────────────────────────
    st.markdown("### 1️⃣ Base Project Data")
    base_keys = [
        "plot_area", "gf_area", "external_perimeter", "roof_slab_area",
        "roof_perimeter", "longest_length", "longest_width",
        "total_villa_height", "structural_levels", "compound_length",
        "parapet_height", "excavation_depth",
    ]
    base_df = pd.DataFrame(
        [{"Field": k, "Value": data.get(k), "Source": "auto" if data.get(k) is not None else "missing"}
         for k in base_keys]
    )
    edited_base = st.data_editor(
        base_df, hide_index=True, use_container_width=True,
        column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
        key="base_editor",
    )
    for _, r in edited_base.iterrows():
        if r["Value"] is not None:
            data[r["Field"]] = float(r["Value"])

    # ── Section 2: Foundations ────────────────────────────────────────────────
    st.markdown("### 2️⃣ Foundations | الأساسات")
    foots = data.get("schedules", {}).get("foundation", {}).get("footings", [])
    if foots:
        f_df = pd.DataFrame(foots)
        edited_f = st.data_editor(
            f_df, hide_index=True, use_container_width=True,
            num_rows="dynamic", key="footings_editor",
        )
        # Display computed total volume
        total_v = sum(
            (row.get("long_mm", 0) or 0) / 1000
            * (row.get("short_mm", 0) or 0) / 1000
            * (row.get("depth_mm", 0) or 0) / 1000
            * (row.get("count", 0) or 0)
            for _, row in edited_f.iterrows()
        )
        st.info(f" Total foundation concrete: **{total_v:.2f} m³**")
        data["schedules"].setdefault("foundation", {})["footings"] = edited_f.to_dict("records")
    else:
        st.warning("No footings extracted.")

    # ── Section 3: Tie beams ──────────────────────────────────────────────────
    st.markdown("### 3️⃣ Tie Beams | الميد")
    st.caption(
        "Tie-beam concrete = **width × depth × length**. `length_m` is the TOTAL run "
        "per mark, auto-measured from the plan (same method as beams) — **confirm/correct it**. "
        "`length_confidence` near 1.0 = trustworthy; low = please verify."
    )
    tbs = data.get("schedules", {}).get("tie_beam", {}).get("tie_beams", [])
    if tbs:
        low = [t.get("type") for t in tbs
               if (t.get("length_confidence") is not None and t.get("length_confidence", 0) < 0.6)
               or not t.get("length_m")]
        if low:
            st.warning(f" Verify measured length for: {', '.join(str(m) for m in low if m)}")
        tb_df    = pd.DataFrame(tbs)
        edited_t = st.data_editor(
            tb_df, hide_index=True, use_container_width=True,
            num_rows="dynamic", key="tb_editor",
            column_config={
                "length_m":          st.column_config.NumberColumn(
                    "length_m (TOTAL run)", format="%.2f",
                    help="Total length of all segments of this tie-beam mark, in metres."),
                "length_confidence": st.column_config.NumberColumn(
                    "confidence (1.0=best)", format="%.2f", disabled=True),
            },
        )
        data["schedules"].setdefault("tie_beam", {})["tie_beams"] = edited_t.to_dict("records")
    else:
        st.warning("No tie beams extracted.")

    # ── Section 4: Columns ────────────────────────────────────────────────────
    st.markdown("### 4️⃣ Columns | الأعمدة")
    cols = data.get("schedules", {}).get("column_schedule", {}).get("columns", [])
    if cols:
        c_df     = pd.DataFrame(cols)
        edited_c = st.data_editor(
            c_df, hide_index=True, use_container_width=True,
            num_rows="dynamic", key="cols_editor",
        )
        data["schedules"].setdefault("column_schedule", {})["columns"] = edited_c.to_dict("records")
    else:
        st.warning("No column schedule extracted (hardcoded fallback in use).")

    # ── Section 5: Slab beams (1F, 2F, Roof) ──────────────────────────────────
    st.markdown("### 5️⃣ Slab Beams | كمرات الأسقف")
    st.caption(
        "Beam concrete = **length × width × depth** (not × count). `length_m` is the "
        "TOTAL run length per mark, auto-measured from the plan — **confirm or correct it**. "
        "`length_confidence` near 1.0 = trustworthy; low / 0 = please verify."
    )
    for slab_key, label in [("slab_1f", "1st Floor"), ("slab_2f", "2nd Floor"), ("slab_roof", "Roof")]:
        beams = data.get("schedules", {}).get(slab_key, {}).get("beams", [])
        if not beams:
            continue
        # Flag low-confidence / unmeasured beams so the user knows what to check.
        low = [b.get("mark") for b in beams
               if (b.get("length_confidence") is not None and b.get("length_confidence", 0) < 0.6)
               or not b.get("length_m")]
        st.markdown(f"**{label}**")
        if low:
            st.warning(f" Verify measured length for: {', '.join(str(m) for m in low if m)}")
        b_df     = pd.DataFrame(beams)
        edited_b = st.data_editor(
            b_df, hide_index=True, use_container_width=True,
            num_rows="dynamic", key=f"beams_{slab_key}",
            column_config={
                "length_m":          st.column_config.NumberColumn(
                    "length_m (TOTAL run)", format="%.2f",
                    help="Total length of all beams of this mark, in metres."),
                "length_confidence": st.column_config.NumberColumn(
                    "confidence (1.0=best)", format="%.2f", disabled=True),
            },
        )
        data["schedules"].setdefault(slab_key, {})["beams"] = edited_b.to_dict("records")

    # ── Section 6: Doors & Windows ────────────────────────────────────────────
    st.markdown("### 6️⃣ Doors & Windows | الأبواب والنوافذ")
    openings = data.get("openings", {})
    col_d, col_w = st.columns(2)
    with col_d:
        st.markdown("**Doors**")
        doors = openings.get("doors", [])
        if doors:
            d_df     = pd.DataFrame(doors)
            edited_d = st.data_editor(
                d_df, hide_index=True, use_container_width=True,
                num_rows="dynamic", key="doors_editor",
            )
            data["openings"]["doors"] = edited_d.to_dict("records")
        else:
            st.caption("No doors extracted")
    with col_w:
        st.markdown("**Windows**")
        wins = openings.get("windows", [])
        if wins:
            w_df     = pd.DataFrame(wins)
            edited_w = st.data_editor(
                w_df, hide_index=True, use_container_width=True,
                num_rows="dynamic", key="windows_editor",
            )
            data["openings"]["windows"] = edited_w.to_dict("records")
        else:
            st.caption("No windows extracted")

    # Re-compute opening totals
    if "openings" in data:
        doors_l = data["openings"].get("doors", [])
        wins_l  = data["openings"].get("windows", [])
        data["openings"]["totals"] = {
            "door_count":     sum(int(d.get("count") or 0) for d in doors_l),
            "window_count":   sum(int(w.get("count") or 0) for w in wins_l),
            "door_area_m2":   round(sum(
                (float(d.get("width_mm") or 0)/1000) *
                (float(d.get("height_mm") or 0)/1000) *
                int(d.get("count") or 0)
                for d in doors_l), 2),
            "window_area_m2": round(sum(
                (float(w.get("width_mm") or 0)/1000) *
                (float(w.get("height_mm") or 0)/1000) *
                int(w.get("count") or 0)
                for w in wins_l), 2),
        }

    # ── Section 7: Wall lengths ───────────────────────────────────────────────
    st.markdown("### 7️⃣ Wall Lengths | أطوال الجدران")
    walls = data.get("walls", {})
    if walls:
        rows = []
        for fk, w in walls.items():
            rows.append({
                "Floor":             fk,
                "Internal (m)":      w.get("internal_total_m"),
                "External (m)":      w.get("external_total_m"),
                "Source":            w.get("source", "ai"),
                "AI Notes":          w.get("ai_notes", "")[:80],
            })
        w_df = pd.DataFrame(rows)
        edited_w = st.data_editor(
            w_df, hide_index=True, use_container_width=True,
            disabled=["Floor", "AI Notes"],
            key="walls_editor",
        )
        # Push edits back
        for _, r in edited_w.iterrows():
            fk = r["Floor"]
            if fk in data["walls"]:
                if r["Internal (m)"] is not None:
                    data["walls"][fk]["internal_total_m"] = float(r["Internal (m)"])
                if r["External (m)"] is not None:
                    data["walls"][fk]["external_total_m"] = float(r["External (m)"])
                if r["Source"] != data["walls"][fk].get("source"):
                    data["walls"][fk]["source"] = "manual"

        # Sync into floors block
        for fk, w in data["walls"].items():
            if fk in data.get("floors", {}):
                data["floors"][fk]["wall_internal"] = w.get("internal_total_m")
                data["floors"][fk]["wall_external"] = w.get("external_total_m")
    else:
        st.caption("No wall data extracted yet.")

    # ── Section 8: Sanity panel ───────────────────────────────────────────────
    st.markdown("### 8️⃣ Sanity Check")
    warns = _sanity_warnings(data)
    if not warns:
        st.success("✓ All values within expected UAE villa ranges.")
    else:
        for w in warns:
            st.warning(w)

    # ── Section 9: Approve gate ───────────────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns([3, 1])
    with c1:
        approve = st.checkbox(
            "I have reviewed all schedules above and confirm the values are correct.",
            key="approve_check",
        )
    with c2:
        if st.button(" Save", key="save_btn"):
            _save(data)
            st.toast("Saved to _project_data.json", icon="✓")

    if approve:
        data["_approved"] = True
        _save(data)
        st.success(
            " Schedules approved. You can now run the BOQ tab."
        )
        st.session_state["schedules_approved"] = True
    else:
        data["_approved"] = False
        st.info(" Tick the box above when you're ready to lock the inputs.")
        st.session_state["schedules_approved"] = False
