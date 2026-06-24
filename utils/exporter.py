"""
تصدير BOQ إلى Excel احترافي مع ملخص المواد والافتراضات الهندسية

Supports an optional pricing layer: if the DataFrame carries "Unit Price" and
"Total" columns, two extra money columns + a grand-total row are written.
Now includes:
- Worksheet 1: "BOQ" (Itemized takeoff and pricing)
- Worksheet 2: "Material Summary" (Aggregated concrete, steel, blocks counts and totals)
- Worksheet 3: "Assumptions & Estimators" (Detailed layout and geo variables documentation)
"""
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import date
import io


SECTION_FILL  = PatternFill("solid", fgColor="2D6A9F")
ALT_FILL      = PatternFill("solid", fgColor="F0F4F8")
WHITE_FILL    = PatternFill("solid", fgColor="FFFFFF")
TOTAL_FILL    = PatternFill("solid", fgColor="1A3C5E")
HEADER_FILL   = PatternFill("solid", fgColor="1A3C5E")
WHITE_FONT    = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
HEADER_FONT   = Font(color="FFFFFF", bold=True, name="Calibri", size=12)
TOTAL_FONT    = Font(color="FFFFFF", bold=True, name="Calibri", size=12)
BODY_FONT     = Font(name="Calibri", size=11)
CENTER        = Alignment(horizontal="center", vertical="center")
RIGHT         = Alignment(horizontal="right", vertical="center")
LEFT          = Alignment(horizontal="left",  vertical="center")
THIN          = Side(style="thin", color="CCCCCC")
BORDER        = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def export_boq_to_excel(df: pd.DataFrame, project_name: str,
                        currency: str = "AED", project_meta: dict = None) -> bytes:
    """
    Build a styled BOQ workbook with Material Summary and Assumptions sheets.

    If `df` has "Unit Price" + "Total" columns, the sheet includes pricing and
    a grand-total row; otherwise it's a quantity-only BOQ.
    """
    priced = ("Unit Price" in df.columns) and ("Total" in df.columns)

    if priced:
        cols      = ["#", "Description (English)", "البيان", "Unit", "Quantity",
                     "Unit Price", "Total"]
        headers   = ["#", "Description (English)", "البيان", "Unit", "Quantity",
                     f"Unit Price ({currency})", f"Total ({currency})"]
        col_widths = [8, 42, 30, 8, 12, 16, 18]
    else:
        cols      = ["#", "Description (English)", "البيان", "Unit", "Quantity"]
        headers   = ["#", "Description (English)", "البيان", "Unit", "Quantity"]
        col_widths = [8, 45, 35, 8, 14]

    ncol     = len(cols)
    last_col = get_column_letter(ncol)

    wb = Workbook()
    
    # ── Sheet 1: BOQ ──────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = "BOQ"

    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Title
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = f"Bill of Quantities — {project_name}"
    ws["A1"].font      = Font(bold=True, size=16, color="1A3C5E", name="Calibri")
    ws["A1"].alignment = CENTER
    ws.row_dimensions[1].height = 30

    # Date
    ws.merge_cells(f"A2:{last_col}2")
    ws["A2"] = f"Date: {date.today().strftime('%d %B %Y')}"
    ws["A2"].font      = Font(italic=True, size=11, color="666666", name="Calibri")
    ws["A2"].alignment = CENTER
    ws.row_dimensions[3].height = 8

    # Column headers
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    ws.row_dimensions[4].height = 22

    money_cols = {6, 7} if priced else set()
    qty_col    = 5
    row_idx    = 5
    alt        = False
    grand_total = 0.0

    for r in df.to_dict("records"):
        is_header = bool(r.get("_is_header", False))
        ws.row_dimensions[row_idx].height = 18

        if is_header:
            ws.merge_cells(f"A{row_idx}:{last_col}{row_idx}")
            title = str(r.get("Description (English)", "")).replace("▌ ", "")
            cell = ws.cell(row=row_idx, column=1, value=title)
            cell.fill, cell.font, cell.alignment, cell.border = SECTION_FILL, WHITE_FONT, LEFT, BORDER
            alt = False
        else:
            fill = ALT_FILL if alt else WHITE_FILL
            for c, key in enumerate(cols, 1):
                # Force Unit Price to 0.0 and Total to Formula
                if key == "Unit Price":
                    val = 0.0
                elif key == "Total":
                    # Excel formula: Quantity (Col E) * Unit Price (Col F)
                    val = f"=E{row_idx}*F{row_idx}"
                else:
                    val = r.get(key, "")
                    
                cell = ws.cell(row=row_idx, column=c, value=val)
                cell.fill, cell.font, cell.border = fill, BODY_FONT, BORDER
                if c == qty_col or c in money_cols:
                    cell.alignment = RIGHT
                    if c in money_cols and key != "Total":
                        cell.number_format = "#,##0.00"
                    elif key == "Total":
                        cell.number_format = "#,##0.00"
                elif c in (1, 4):
                    cell.alignment = CENTER
                else:
                    cell.alignment = LEFT
            if priced:
                # We can't sum formulas easily in openpyxl without a string formula for the grand total
                pass
            alt = not alt
        row_idx += 1

    # Grand total row
    if priced:
        ws.merge_cells(f"A{row_idx}:{get_column_letter(ncol-1)}{row_idx}")
        lbl = ws.cell(row=row_idx, column=1, value=f"GRAND TOTAL ({currency})")
        lbl.fill, lbl.font, lbl.alignment, lbl.border = TOTAL_FILL, TOTAL_FONT, RIGHT, BORDER
        # Grand total formula: SUM(G5:G{row_idx-1})
        tot = ws.cell(row=row_idx, column=ncol, value=f"=SUM(G5:G{row_idx-1})")
        tot.fill, tot.font, tot.alignment, tot.border = TOTAL_FILL, TOTAL_FONT, RIGHT, BORDER
        tot.number_format = "#,##0.00"
        ws.row_dimensions[row_idx].height = 24

    ws.freeze_panes = "A5"

    # ── Sheet 2: Material Summary ─────────────────────────────────────────────
    ws_mat = wb.create_sheet(title="Material Summary")
    ws_mat.column_dimensions["A"].width = 8
    ws_mat.column_dimensions["B"].width = 35
    ws_mat.column_dimensions["C"].width = 10
    ws_mat.column_dimensions["D"].width = 14
    ws_mat.column_dimensions["E"].width = 16
    ws_mat.column_dimensions["F"].width = 18

    # Title
    ws_mat.merge_cells("A1:F1")
    ws_mat["A1"] = f"Villa Material Aggregates Summary — {project_name}"
    ws_mat["A1"].font = Font(bold=True, size=14, color="1A3C5E", name="Calibri")
    ws_mat["A1"].alignment = CENTER
    ws_mat.row_dimensions[1].height = 28

    # Headers
    headers_mat = ["#", "Material Description", "Unit", "Quantity", "Rate (AED)", "Total (AED)"]
    for c, h in enumerate(headers_mat, 1):
        cell = ws_mat.cell(row=3, column=c, value=h)
        cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
    ws_mat.row_dimensions[3].height = 22

    # Calculate quantities
    pcc_qty = 0.0
    rc_qty = 0.0
    block_8_m2 = 0.0
    block_6_m2 = 0.0
    solid_block_m3 = 0.0
    
    # Steel calculation inputs
    footings_conc = 0.0
    cols_conc = 0.0
    beams_conc = 0.0
    slabs_conc = 0.0

    for r in df.to_dict("records"):
        if r.get("_is_header"):
            continue
        nrm = str(r.get("#", ""))
        qty = float(r.get("Quantity", 0.0) or 0.0)
        
        # PCC blinding
        if nrm.startswith("D.1") or nrm.startswith("D.2"):
            pcc_qty += qty
        # RC Concrete
        elif nrm.startswith("D."):
            rc_qty += qty
            if nrm == "D.3":
                footings_conc += qty
            elif nrm.startswith("D.4") or nrm.startswith("D.7"):
                cols_conc += qty
            elif nrm.startswith("D.5") or nrm.startswith("D.8") or nrm == "D.11":
                beams_conc += qty
            elif nrm == "D.6" or nrm.startswith("D.9") or nrm == "D.10":
                slabs_conc += qty
        # Blocks 8"
        elif nrm.startswith("E.2") or nrm == "E.4":
            block_8_m2 += qty
        # Blocks 6"
        elif nrm.startswith("E.3"):
            block_6_m2 += qty
        # Solid Block
        elif nrm == "E.1":
            solid_block_m3 += qty

    block_8_pcs = round(block_8_m2 * 12.5)
    block_6_pcs = round(block_6_m2 * 12.5)
    solid_block_pcs = round(solid_block_m3 / 0.016) if solid_block_m3 > 0 else 0

    steel_kg = (footings_conc * 80.0) + (cols_conc * 140.0) + (beams_conc * 120.0) + (slabs_conc * 100.0)
    steel_tons = round(steel_kg / 1000.0, 2)

    # Rates
    pcc_rate = 295.0
    rc_rate = 350.0
    block_8_rate = 3.40
    block_6_rate = 2.90
    solid_block_rate = 3.40
    steel_rate = 2668.0

    # Query DB rates for Dubai/project location if possible
    try:
        from utils.db import safe_query
        df_db = safe_query("SELECT item_name, rate_aed FROM qto_market_prices")
        if not df_db.empty:
            prices = dict(zip(df_db["item_name"], df_db["rate_aed"]))
            emirate = "Dubai"
            if project_meta:
                emirate = project_meta.get("emirate") or "Dubai"
            em_suffix = "Abu Dhabi" if "abu" in emirate.lower() else ("Sharjah" if "sharjah" in emirate.lower() else ("Ajman" if "ajman" in emirate.lower() else "Dubai"))
            
            pcc_rate = float(prices.get(f"Ready Mix C20/25 ({em_suffix})", pcc_rate) or 0.0)
            rc_rate = float(prices.get(f"Ready Mix C30/37 ({em_suffix})", rc_rate) or 0.0)
            block_8_rate = float(prices.get(f"Hollow Block 8\" ({em_suffix})", block_8_rate) or 0.0)
            block_6_rate = float(prices.get(f"Hollow Block 6\" ({em_suffix})", block_6_rate) or 0.0)
            solid_block_rate = float(prices.get(f"Hollow Block 8\" ({em_suffix})", solid_block_rate) or 0.0)
            steel_rate = float(prices.get(f"Rebar 12mm (Grade 60) ({em_suffix})", steel_rate) or 0.0)
    except Exception:
        pass

    material_rows = [
        ("M.1", "Reinforcement Steel Rebar (Grade 60)", "ton", float(steel_tons), float(steel_rate)),
        ("M.2", f"Structural Concrete (Grade {project_meta.get('concrete_grade', 'C30/37') if project_meta else 'C30/37'})", "m³", float(round(rc_qty, 2)), float(rc_rate)),
        ("M.3", "Lean PCC Blinding Concrete (C20/25)", "m³", float(round(pcc_qty, 2)), float(pcc_rate)),
        ("M.4", f"8\" External Hollow Blocks ({project_meta.get('block_thickness', '200mm') if project_meta else '200mm'})", "pc", float(block_8_pcs), float(block_8_rate)),
        ("M.5", "6\" Internal Hollow Blocks (150mm)", "pc", float(block_6_pcs), float(block_6_rate)),
        ("M.6", "Solid Blocks (Sub-structure Walls)", "pc", float(solid_block_pcs), float(solid_block_rate)),
    ]

    mat_row_idx = 4
    mat_alt = False
    mat_total = 0.0
    for code_m, desc_m, unit_m, qty_m, _ in material_rows:
        fill_m = ALT_FILL if mat_alt else WHITE_FILL
        rate_m = 0.0
        # Excel formula: Quantity (Col D) * Rate (Col E)
        total_m_formula = f"=D{mat_row_idx}*E{mat_row_idx}"
        
        ws_mat.cell(row=mat_row_idx, column=1, value=code_m).fill = fill_m
        ws_mat.cell(row=mat_row_idx, column=1).font = BODY_FONT
        ws_mat.cell(row=mat_row_idx, column=1).alignment = CENTER
        ws_mat.cell(row=mat_row_idx, column=1).border = BORDER
        
        ws_mat.cell(row=mat_row_idx, column=2, value=desc_m).fill = fill_m
        ws_mat.cell(row=mat_row_idx, column=2).font = BODY_FONT
        ws_mat.cell(row=mat_row_idx, column=2).alignment = LEFT
        ws_mat.cell(row=mat_row_idx, column=2).border = BORDER
        
        ws_mat.cell(row=mat_row_idx, column=3, value=unit_m).fill = fill_m
        ws_mat.cell(row=mat_row_idx, column=3).font = BODY_FONT
        ws_mat.cell(row=mat_row_idx, column=3).alignment = CENTER
        ws_mat.cell(row=mat_row_idx, column=3).border = BORDER
        
        c_qty = ws_mat.cell(row=mat_row_idx, column=4, value=qty_m)
        c_qty.fill, c_qty.font, c_qty.alignment, c_qty.border = fill_m, BODY_FONT, RIGHT, BORDER
        if isinstance(qty_m, (int, float)):
            c_qty.number_format = "#,##0.00"
            
        c_rate = ws_mat.cell(row=mat_row_idx, column=5, value=rate_m)
        c_rate.fill, c_rate.font, c_rate.alignment, c_rate.border = fill_m, BODY_FONT, RIGHT, BORDER
        c_rate.number_format = "#,##0.00"
        
        c_tot = ws_mat.cell(row=mat_row_idx, column=6, value=total_m_formula)
        c_tot.fill, c_tot.font, c_tot.alignment, c_tot.border = fill_m, BODY_FONT, RIGHT, BORDER
        c_tot.number_format = "#,##0.00"
        
        ws_mat.row_dimensions[mat_row_idx].height = 18
        mat_alt = not mat_alt
        mat_row_idx += 1

    # Grand total for material summary
    ws_mat.merge_cells(f"A{mat_row_idx}:E{mat_row_idx}")
    lbl_m = ws_mat.cell(row=mat_row_idx, column=1, value="TOTAL ESTIMATED MATERIAL COST (AED)")
    lbl_m.fill, lbl_m.font, lbl_m.alignment, lbl_m.border = TOTAL_FILL, TOTAL_FONT, RIGHT, BORDER
    
    # Grand total formula: SUM(F4:F{mat_row_idx-1})
    tot_m = ws_mat.cell(row=mat_row_idx, column=6, value=f"=SUM(F4:F{mat_row_idx-1})")
    tot_m.fill, tot_m.font, tot_m.alignment, tot_m.border = TOTAL_FILL, TOTAL_FONT, RIGHT, BORDER
    tot_m.number_format = "#,##0.00"
    ws_mat.row_dimensions[mat_row_idx].height = 24

    # ── Sheet 3: Assumptions Sheet ────────────────────────────────────────────
    ws_ass = wb.create_sheet(title="Assumptions & Estimators")
    ws_ass.column_dimensions["A"].width = 28
    ws_ass.column_dimensions["B"].width = 45

    # Title
    ws_ass.merge_cells("A1:B1")
    ws_ass["A1"] = f"Engineering Assumptions & Takeoff Parameters"
    ws_ass["A1"].font = Font(bold=True, size=14, color="1A3C5E", name="Calibri")
    ws_ass["A1"].alignment = CENTER
    ws_ass.row_dimensions[1].height = 28

    # Headers
    ws_ass.cell(row=3, column=1, value="Parameter").fill = HEADER_FILL
    ws_ass.cell(row=3, column=1).font = HEADER_FONT
    ws_ass.cell(row=3, column=1).alignment = CENTER
    ws_ass.cell(row=3, column=1).border = BORDER
    
    ws_ass.cell(row=3, column=2, value="Value / Setting").fill = HEADER_FILL
    ws_ass.cell(row=3, column=2).font = HEADER_FONT
    ws_ass.cell(row=3, column=2).alignment = CENTER
    ws_ass.cell(row=3, column=2).border = BORDER
    ws_ass.row_dimensions[3].height = 22

    params = [
        ("▌ MEASUREMENT STANDARD & METHODOLOGY", ""),
        ("Standard", "Quantities measured NET IN PLACE (POMI / SMM principles)"),
        ("Concrete & Blockwork", "By volume (m³) / area (m²); no waste, laps or wastage allowance"),
        ("Item Coding", "Hierarchical codes (e.g. C.1, D.5) grouped by work section"),
        ("Reinforcement & Formwork", "NOT measured here — require a separate detailed takeoff"),
        ("Status", "Indicative automated takeoff — review & verify before tendering"),
        ("", ""),
        ("Project Name", project_name),
        ("Export Date", date.today().strftime('%d %B %Y')),
        ("Base Currency", currency),
    ]

    if project_meta:
        params.extend([
            ("Number of Villa Floors", str(project_meta.get("num_floors", 2))),
            ("Ground Floor Height", f"{project_meta.get('gf_height', 4.0)} m"),
            ("1st Floor Height", f"{project_meta.get('f1_height', 4.0)} m"),
            ("2nd Floor Height", f"{project_meta.get('f2_height', 4.0)} m"),
            ("Soil Excavation Depth", f"{project_meta.get('excavation_depth', 1.25)} m"),
            ("Concrete Grade", str(project_meta.get("concrete_grade", "C30/37"))),
            ("Block Thickness", str(project_meta.get("block_thickness", "200mm"))),
            ("Included Road Base", "Yes" if project_meta.get("include_road_base", True) else "No"),
        ])
        
        estimates_list = project_meta.get("boq_meta", {}).get("estimates", [])
        if estimates_list:
            params.append(("", ""))
            params.append(("▌ AUTOMATED ESTIMATES & ASSUMPTIONS", ""))
            for idx, est in enumerate(estimates_list, 1):
                params.append((f"Estimate #{idx}", est))
                
        needs_input_list = project_meta.get("boq_meta", {}).get("needs_input", [])
        if needs_input_list:
            params.append(("", ""))
            params.append(("▌ MISSING DRAWING INPUTS", ""))
            for idx, inp in enumerate(needs_input_list, 1):
                params.append((f"Missing Field #{idx}", inp))
    else:
        params.extend([
            ("Number of Villa Floors", "2 (Default)"),
            ("Soil Excavation Depth", "1.25 m (Default)"),
            ("Concrete Grade", "C30/37 (Default)"),
            ("Block Thickness", "200mm (Default)"),
        ])

    ass_row_idx = 4
    for key_a, val_a in params:
        if not key_a and not val_a:
            ws_ass.row_dimensions[ass_row_idx].height = 10
            ass_row_idx += 1
            continue
            
        if val_a == "" and key_a.startswith("▌"):
            ws_ass.merge_cells(f"A{ass_row_idx}:B{ass_row_idx}")
            cell = ws_ass.cell(row=ass_row_idx, column=1, value=key_a)
            cell.fill, cell.font, cell.alignment, cell.border = SECTION_FILL, WHITE_FONT, LEFT, BORDER
            ws_ass.row_dimensions[ass_row_idx].height = 20
            ass_row_idx += 1
            continue

        ws_ass.cell(row=ass_row_idx, column=1, value=key_a).fill = WHITE_FILL
        ws_ass.cell(row=ass_row_idx, column=1).font = Font(name="Calibri", bold=True, size=10)
        ws_ass.cell(row=ass_row_idx, column=1).alignment = LEFT
        ws_ass.cell(row=ass_row_idx, column=1).border = BORDER
        
        ws_ass.cell(row=ass_row_idx, column=2, value=val_a).fill = WHITE_FILL
        ws_ass.cell(row=ass_row_idx, column=2).font = BODY_FONT
        ws_ass.cell(row=ass_row_idx, column=2).alignment = LEFT
        ws_ass.cell(row=ass_row_idx, column=2).border = BORDER
        
        ws_ass.row_dimensions[ass_row_idx].height = 18
        ass_row_idx += 1

    # ── Doors and Windows Schedules ───────────────────────────────────────────
    if project_meta:
        openings = project_meta.get("confirmed_auto_data", {}).get("openings", {})
        doors = openings.get("doors", [])
        windows = openings.get("windows", [])
        
        def write_schedule(sheet_title, items):
            ws_sched = wb.create_sheet(sheet_title)
            
            ws_sched.merge_cells("A1:F1")
            ws_sched["A1"] = f"{sheet_title} — {project_name}"
            ws_sched["A1"].font = Font(bold=True, size=14, color="1A3C5E", name="Calibri")
            ws_sched["A1"].alignment = CENTER
            ws_sched.row_dimensions[1].height = 28
            
            headers = ["#", "Mark", "Width (m)", "Height (m)", "Count", "Total Area (m²)"]
            col_widths = [8, 20, 15, 15, 12, 18]
            for i, w in enumerate(col_widths, 1):
                ws_sched.column_dimensions[get_column_letter(i)].width = w
                
            for c, h in enumerate(headers, 1):
                cell = ws_sched.cell(row=3, column=c, value=h)
                cell.fill, cell.font, cell.alignment, cell.border = HEADER_FILL, HEADER_FONT, CENTER, BORDER
            ws_sched.row_dimensions[3].height = 22
            
            row_idx = 4
            grand_total_area = 0.0
            grand_total_count = 0
            for idx, item in enumerate(items, 1):
                mark = item.get("mark") or f"Type {idx}"
                width = item.get("width_m") or item.get("width") or item.get("width_mm") or 0.0
                height = item.get("height_m") or item.get("height") or item.get("height_mm") or 0.0
                count = item.get("count_in_plans") or item.get("count") or 0
                
                try:
                    w_val = float(str(width).strip() or 0)
                    h_val = float(str(height).strip() or 0)
                    if width == item.get("width_mm") and w_val > 100: w_val /= 1000.0
                    if height == item.get("height_mm") and h_val > 100: h_val /= 1000.0
                    c_val = int(float(str(count).strip() or 0))
                except:
                    w_val, h_val, c_val = 0.0, 0.0, 0
                
                area = w_val * h_val * c_val
                grand_total_area += area
                grand_total_count += c_val
                
                ws_sched.cell(row=row_idx, column=1, value=idx).alignment = CENTER
                ws_sched.cell(row=row_idx, column=2, value=mark).alignment = CENTER
                ws_sched.cell(row=row_idx, column=3, value=w_val).alignment = CENTER
                ws_sched.cell(row=row_idx, column=4, value=h_val).alignment = CENTER
                ws_sched.cell(row=row_idx, column=5, value=c_val).alignment = CENTER
                ws_sched.cell(row=row_idx, column=6, value=round(area, 2)).alignment = RIGHT
                
                for c in range(1, 7):
                    ws_sched.cell(row=row_idx, column=c).border = BORDER
                
                row_idx += 1
                
            ws_sched.merge_cells(f"A{row_idx}:D{row_idx}")
            ws_sched.cell(row=row_idx, column=1, value="GRAND TOTAL").alignment = RIGHT
            ws_sched.cell(row=row_idx, column=1).font = TOTAL_FONT
            ws_sched.cell(row=row_idx, column=1).fill = TOTAL_FILL
            for c in range(1, 5):
                ws_sched.cell(row=row_idx, column=c).border = BORDER
                ws_sched.cell(row=row_idx, column=c).fill = TOTAL_FILL
                
            ws_sched.cell(row=row_idx, column=5, value=grand_total_count).alignment = CENTER
            ws_sched.cell(row=row_idx, column=5).font = TOTAL_FONT
            ws_sched.cell(row=row_idx, column=5).fill = TOTAL_FILL
            ws_sched.cell(row=row_idx, column=5).border = BORDER
            
            ws_sched.cell(row=row_idx, column=6, value=round(grand_total_area, 2)).alignment = RIGHT
            ws_sched.cell(row=row_idx, column=6).font = TOTAL_FONT
            ws_sched.cell(row=row_idx, column=6).fill = TOTAL_FILL
            ws_sched.cell(row=row_idx, column=6).border = BORDER

        if windows:
            write_schedule("Windows Schedule", windows)
        if doors:
            write_schedule("Doors Schedule", doors)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
