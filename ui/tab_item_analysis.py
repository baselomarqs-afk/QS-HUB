"""
التبويب الأهم — تحليل item-by-item لكل صفحة
"""
import streamlit as st
import anthropic
import base64
import json
import re
import io
import os
import numpy as np
from PIL import Image
import pandas as pd

from engine.item_detection_map  import DRAWING_ITEMS_MAP
from engine.item_calculator     import calculate_item
from engine.result_validator    import validate_quantity
from pdf_engine.pdf_loader      import page_to_pil


def _page_to_b64(arr: np.ndarray) -> str:
    rgb = arr[:, :, ::-1].copy()
    pil = Image.fromarray(rgb)
    w, h = pil.size
    if max(w, h) > 2000:
        s   = 2000 / max(w, h)
        pil = pil.resize((int(w * s), int(h * s)), Image.LANCZOS)
    buf = io.BytesIO()
    pil.save(buf, format="PNG", optimize=True)
    return base64.standard_b64encode(buf.getvalue()).decode()


def _get_anthropic_key() -> str:
    """Returns API key from env or session state."""
    return (os.environ.get("ANTHROPIC_API_KEY")
            or st.session_state.get("anthropic_api_key_input", ""))


def _ask_ai_for_item(page_b64: str, item: dict, drawing_type: str) -> dict:
    api_key = _get_anthropic_key()
    if not api_key:
        return {"_ok": False, "_error": "ANTHROPIC_API_KEY not set"}

    from engine.dimension_filter import DRAWING_REQUIRED_INPUTS
    client  = anthropic.Anthropic(api_key=api_key)
    needed  = item.get("inputs_needed", [])

    # Inputs this specific item's formula actually needs
    inputs_list = "\n".join(f"  - {inp}" for inp in needed)

    # What to ignore for this drawing type
    config  = DRAWING_REQUIRED_INPUTS.get(drawing_type, {})
    ignores = config.get("ignore_completely", [])
    ignore_list = ", ".join(i.replace("_", " ") for i in ignores)

    prompt = f"""You are a QTO engineer analyzing a {drawing_type.replace('_', ' ').upper()} drawing.

ITEM TO CALCULATE: {item['name_en']} ({item['name_ar']})
FORMULA: {item['formula_str']}

EXTRACT ONLY these inputs (nothing else):
{inputs_list}

IGNORE completely: {ignore_list}
Also ignore: dates, sheet numbers, revision marks, scale ratios (1:100 etc.), \
any dimension NOT in the list above.

For schedule lists return:
{{"items": [{{"label": "F1", "length_m": 1.5, "width_m": 1.5, "depth_m": 0.6, "count": 4}}]}}

For single values return:
{{"longest_length": 22.0, "longest_width": 18.0}}

Return ONLY valid JSON. No markdown. No explanation. Use null if not found."""

    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": page_b64}},
                    {"type": "text",  "text": prompt},
                ],
            }],
        )
        raw  = re.sub(r"```json\s*|```", "", resp.content[0].text).strip()
        data = json.loads(raw)
        data["_ok"] = True
        return data
    except Exception as e:
        return {"_ok": False, "_error": str(e)}


def _map_to_inputs(item_key: str, ai_data: dict) -> dict:
    inputs = {}

    # Schedule lists
    if "items" in ai_data:
        lst = ai_data["items"]
        if "foundation" in item_key:
            inputs["foundations_schedule"] = lst
        elif "neck_col" in item_key:
            inputs["neck_columns_schedule"] = lst
        elif "beam" in item_key:
            inputs["beams_schedule"] = lst
        elif "col_" in item_key:
            inputs["columns_schedule"] = lst
        elif "door" in item_key:
            inputs["doors_schedule"] = lst
        elif "window" in item_key:
            inputs["windows_schedule"] = lst

    # Scalar mappings: standard_key → list of possible AI-returned keys
    _MAP = {
        "longest_length":     ["longest_length", "length", "l"],
        "longest_width":      ["longest_width",  "width",  "w"],
        "gf_area":            ["gf_area", "ground_floor_area", "total_area_m2", "area"],
        "ext_perimeter":      ["ext_perimeter", "external_perimeter_m", "perimeter"],
        "external_perimeter": ["ext_perimeter", "external_perimeter_m", "perimeter"],
        "tb_width":           ["tb_width", "tie_beam_width_m", "width_m"],
        "tb_depth":           ["tb_depth", "tie_beam_depth_m", "depth_m"],
        "tb_total_length":    ["tb_total_length", "tie_beam_total_length_m", "total_length_m"],
        "floor_area":         ["total_area_m2", "floor_area", "area"],
        "wet_area":           ["wet_area_m2", "wet_area", "total_wet_area"],
        "wet_perimeter":      ["wet_perimeter_m", "wet_perimeter"],
        "dry_perimeter":      ["dry_perimeter_m", "dry_perimeter"],
        "int_walls_length":   ["int_walls_length_m", "internal_walls_length", "int_walls"],
        "balcony_area":       ["balcony_area_m2", "balcony_area"],
        "floor_height":       ["floor_height_m", "floor_height", "height_m"],
        "roof_perimeter":     ["roof_perimeter_m", "roof_perimeter"],
        "roof_slab_area":     ["roof_area_m2", "roof_slab_area", "area"],
        "plot_area":          ["plot_area_m2", "plot_area"],
        "compound_length":    ["compound_wall_length_m", "compound_length"],
        "total_villa_height": ["total_villa_height_m", "total_height", "villa_height"],
        "slab_area":          ["slab_area_m2", "area"],
        "slab_thickness":     ["slab_thickness_m", "thickness", "thickness_m"],
        "structural_levels":  ["structural_levels", "levels", "floors"],
    }
    for std_key, aliases in _MAP.items():
        for alias in aliases:
            if alias in ai_data and ai_data[alias] is not None:
                try:
                    inputs[std_key] = float(ai_data[alias])
                    break
                except (ValueError, TypeError):
                    pass

    return inputs


def render_item_analysis_tab():
    st.header(" Item-by-Item Analysis | تحليل بند بند")
    st.caption("Each drawing → shows its items → AI extracts data for each item → calculates quantity")

    # ── API key check ─────────────────────────────────────────────────────────
    api_key = _get_anthropic_key()
    if not api_key:
        st.error(
            "**ANTHROPIC_API_KEY not found.**\n\n"
            "Get a key at https://console.anthropic.com/settings/keys then either:\n\n"
            "• Run `setx ANTHROPIC_API_KEY sk-ant-...` and restart the app\n\n"
            "• Or paste it temporarily below:"
        )
        st.text_input(
            "Anthropic API Key (session only, not saved)",
            type="password",
            key="anthropic_api_key_input",
            placeholder="sk-ant-...",
        )
        if not st.session_state.get("anthropic_api_key_input"):
            return {}

    classified = st.session_state.get("all_classified_pages", [])
    all_images = st.session_state.get("all_pages_images", {})

    if not classified:
        st.warning(" Upload and classify PDFs first in the PDF Upload tab.")
        return {}

    ready = [p for p in classified if p["detected_type"] in DRAWING_ITEMS_MAP]

    if not ready:
        st.warning(" No classified pages found. Go to PDF Upload tab and assign drawing types.")
        return {}

    # ── Drawing selector ──────────────────────────────────────────────────────
    drawing_options = {
        f"{p['pdf_name'].title()} — Page {p['page_number']} — "
        f"{DRAWING_ITEMS_MAP[p['detected_type']]['label_en']}": p
        for p in ready
    }

    selected_label = st.selectbox(
        "Select Drawing to Analyze | اختر المخطط",
        options=list(drawing_options.keys()),
        key="item_drawing_select",
    )
    selected_page  = drawing_options[selected_label]
    drawing_type   = selected_page["detected_type"]
    drawing_config = DRAWING_ITEMS_MAP[drawing_type]
    items          = drawing_config["items"]

    # ── Page image + item list side by side ───────────────────────────────────
    col_img, col_items = st.columns([3, 2])

    pages_src = all_images.get(selected_page["pdf_name"], [])
    page_arr  = (pages_src[selected_page["page_index"]]
                 if selected_page["page_index"] < len(pages_src) else None)

    with col_img:
        if page_arr is not None:
            st.image(
                page_to_pil(page_arr),
                caption=f"{drawing_config['label_en']} | {drawing_config['label_ar']}",
                use_container_width=True,
            )
        else:
            st.warning("Page image not available.")

    with col_items:
        st.markdown(f"###  {len(items)} Items in this drawing:")
        for idx, item in enumerate(items, 1):
            rk  = f"item_result_{drawing_type}_{item['key']}"
            qty = st.session_state.get(rk)
            if qty is not None:
                st.markdown(f"**{idx}. {item['name_en']}** — `{qty:.2f} {item['unit']}` ")
            else:
                st.markdown(f"{idx}. {item['name_en']} — *{item['unit']}*")

    st.markdown("---")

    # ── Action buttons ────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)
    with col_a:
        analyze_all = st.button(
            f" AI Analyze All {len(items)} Items | تحليل كل البنود",
            type="primary",
            use_container_width=True,
            key="btn_analyze_items",
        )
    with col_b:
        if st.button("️ Clear Results", use_container_width=True, key="btn_clear_items"):
            for item in items:
                for suffix in ("result", "inputs", "ai_raw"):
                    k = f"item_{suffix}_{drawing_type}_{item['key']}"
                    st.session_state.pop(k, None)
            st.rerun()

    # ── Run AI analysis ───────────────────────────────────────────────────────
    if analyze_all:
        if page_arr is None:
            st.error("Page image not found.")
            return {}

        page_b64 = _page_to_b64(page_arr)
        progress = st.progress(0)
        status   = st.empty()

        for idx, item in enumerate(items):
            status.info(f" [{idx+1}/{len(items)}] **{item['name_en']}**")

            ai_raw   = _ask_ai_for_item(page_b64, item, drawing_type)
            inputs   = _map_to_inputs(item["key"], ai_raw)
            quantity = calculate_item(item["key"], inputs)

            st.session_state[f"item_result_{drawing_type}_{item['key']}"] = quantity if quantity is not None else 0.0
            st.session_state[f"item_inputs_{drawing_type}_{item['key']}"] = inputs
            st.session_state[f"item_ai_raw_{drawing_type}_{item['key']}"] = ai_raw

            progress.progress((idx + 1) / len(items))

        status.success(f" All {len(items)} items analyzed!")
        progress.empty()
        st.rerun()

    # ── Results table ─────────────────────────────────────────────────────────
    results_exist = any(
        f"item_result_{drawing_type}_{item['key']}" in st.session_state
        for item in items
    )

    if not results_exist:
        st.info("Click the button above to start analysis.")
        return {}

    st.markdown("###  Results | النتائج")

    rows = []
    for item in items:
        qty = st.session_state.get(f"item_result_{drawing_type}_{item['key']}")
        if qty is not None:
            v       = validate_quantity(item["key"], qty)
            check   = v["label"]
        else:
            check = "—"
        rows.append({
            "#":                  items.index(item) + 1,
            "Item | البند":       f"{item['name_en']} | {item['name_ar']}",
            "Formula | المعادلة": item["formula_str"],
            "Quantity | الكمية":  round(qty, 2) if qty is not None else "—",
            "Unit | الوحدة":      item["unit"],
            "Validation":         check,
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, height=400, hide_index=True)

    # Debug expander — show AI raw responses
    with st.expander(" AI Raw Responses (debug)"):
        for item in items:
            raw = st.session_state.get(f"item_ai_raw_{drawing_type}_{item['key']}")
            if raw:
                ok = raw.get("_ok", False)
                st.markdown(f"**{item['name_en']}** — {'' if ok else '❌'}")
                if not ok:
                    st.caption(raw.get("_error", "unknown error"))
                else:
                    st.json({k: v for k, v in raw.items() if not k.startswith("_")})

    # ── Export / Send to BOQ ──────────────────────────────────────────────────
    col_boq, col_csv = st.columns(2)
    with col_boq:
        if st.button(" Add to BOQ | أضف للـ BOQ", type="primary", use_container_width=True):
            boq_items = st.session_state.get("boq_item_results", {})
            for item in items:
                qty = st.session_state.get(f"item_result_{drawing_type}_{item['key']}", 0.0)
                boq_items[item["key"]] = {
                    "name_en":  item["name_en"],
                    "name_ar":  item["name_ar"],
                    "unit":     item["unit"],
                    "quantity": qty,
                    "formula":  item["formula_str"],
                    "source":   f"AI — {drawing_config['label_en']}",
                }
            st.session_state["boq_item_results"] = boq_items
            st.success(f" {len(items)} items added to BOQ!")

    with col_csv:
        csv = pd.DataFrame(rows).to_csv(index=False)
        st.download_button(
            " Export CSV",
            data=csv,
            file_name=f"QTO_{drawing_type}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    return {}
