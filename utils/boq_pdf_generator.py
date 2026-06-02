"""
مستخرج تقارير BOQ بصيغة PDF (Professional PDF BOQ Generator)
يولد تقارير هندسية معربة ومنسقة لجدول الكميات مسحوبة بمخططات رسومية لتوزيع التكاليف باستخدام Matplotlib و PyMuPDF.
"""
import os
import matplotlib.pyplot as plt
import fitz  # PyMuPDF
import numpy as np
from typing import List, Dict, Any


def generate_boq_charts(boq_items: List[Dict[str, Any]], chart_output_path: str) -> Dict[str, float]:
    """
    Generates cost distribution charts using matplotlib.
    Saves the pie chart to chart_output_path.
    Returns: category totals.
    """
    categories = {
        "Sub-structure (الأعمال تحت الأرض)": 0.0,
        "Super-structure (الأعمال العلوية)": 0.0,
        "Finishes & External (التشطيبات)": 0.0,
        "Openings (الأبواب والنوافذ)": 0.0
    }
    
    for item in boq_items:
        total = float(item.get("total_aed", 0.0))
        cat = item.get("category", "finishing").lower()
        
        if cat in ["excavation", "concrete_sub", "substructure", "foundation", "tie_beam"]:
            categories["Sub-structure (الأعمال تحت الأرض)"] += total
        elif cat in ["superstructure", "concrete_super", "beams", "columns", "slabs"]:
            categories["Super-structure (الأعمال العلوية)"] += total
        elif cat in ["finishes", "finishing", "external", "paint", "tiles"]:
            categories["Finishes & External (التشطيبات)"] += total
        else:
            categories["Openings (الأبواب والنوافذ)"] += total

    # Remove zero categories
    labels = [k for k, v in categories.items() if v > 0]
    values = [v for k, v in categories.items() if v > 0]
    
    if sum(values) == 0:
        # Fallback values for visualization in empty runs
        labels = ["No Data (لا توجد بيانات)"]
        values = [1.0]

    plt.figure(figsize=(6, 4))
    colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
    plt.pie(values, labels=labels, autopct=lambda p: '{:.1f}%'.format(p) if p > 0 else '', startangle=140, colors=colors[:len(values)])
    plt.title("Cost Distribution Breakdown (توزيع تكاليف البناء)")
    plt.tight_layout()
    
    os.makedirs(os.path.dirname(os.path.abspath(chart_output_path)), exist_ok=True)
    plt.savefig(chart_output_path, dpi=150)
    plt.close()
    
    return categories


def create_boq_pdf(
    project_name: str,
    boq_items: List[Dict[str, Any]],
    output_pdf_path: str,
    project_info: Dict[str, Any] = None
):
    """
    Creates a beautiful PDF report containing project summary, Matplotlib cost pie chart,
    and a structured BOQ itemized table using PyMuPDF.
    """
    project_info = project_info or {}
    chart_path = "tmp/boq_cost_distribution.png"
    
    # 1. Generate the cost distribution chart image
    cat_totals = generate_boq_charts(boq_items, chart_path)
    total_project_cost = sum(cat_totals.values())
    
    # 2. Create a new PDF document
    doc = fitz.open()
    
    # ── Page 1: Cover Page & Cost Distribution Charts ──
    page1 = doc.new_page(width=595, height=842) # A4 page
    
    # Draw header banner
    page1.draw_rect(fitz.Rect(0, 0, 595, 80), color=(0.23, 0.51, 0.96), fill=(0.23, 0.51, 0.96))
    page1.insert_text(fitz.Point(30, 48), "Q.S HUB — VILLA QUANTITY TAKEOFF REPORT", fontsize=18, color=(1, 1, 1), fontname="helvetica-bold")
    
    # Project Summary Section
    page1.insert_text(fitz.Point(30, 110), f"Project Name (اسم المشروع): {project_name}", fontsize=12, color=(0.1, 0.1, 0.1), fontname="helvetica-bold")
    page1.insert_text(fitz.Point(30, 130), f"Date Generated (تاريخ التقرير): {fitz.get_pdf_now()[:8]}", fontsize=10, color=(0.3, 0.3, 0.3))
    
    # Specifications parameters
    page1.insert_text(fitz.Point(30, 160), "Key Takeoff Specifications:", fontsize=11, fontname="helvetica-bold")
    page1.insert_text(fitz.Point(40, 180), f"- Plot Area: {project_info.get('plot_area', 'N/A')} m²", fontsize=10)
    page1.insert_text(fitz.Point(40, 195), f"- Ground Floor Area: {project_info.get('gf_area', 'N/A')} m²", fontsize=10)
    page1.insert_text(fitz.Point(40, 210), f"- Total Perimeter: {project_info.get('ext_perimeter', 'N/A')} m", fontsize=10)
    page1.insert_text(fitz.Point(40, 225), f"- Total Cost (الإجمالي): {total_project_cost:,.2f} AED", fontsize=10, fontname="helvetica-bold")
    
    # Insert Matplotlib Cost Breakdown Chart
    if os.path.exists(chart_path):
        page1.insert_image(fitz.Rect(30, 250, 565, 520), filename=chart_path)
        
    page1.insert_text(fitz.Point(30, 800), "Generated automatically by Q.S Hub. All market rates conform to current UAE Price Indexes.", fontsize=8, color=(0.5, 0.5, 0.5))
    
    # ── Page 2+: Itemized BOQ Table ──
    page_num = 2
    page = doc.new_page(width=595, height=842)
    
    # Header for itemized table
    page.draw_rect(fitz.Rect(0, 0, 595, 50), color=(0.23, 0.51, 0.96), fill=(0.23, 0.51, 0.96))
    page.insert_text(fitz.Point(30, 30), f"BOQ Itemized Specifications — Page {page_num}", fontsize=14, color=(1, 1, 1), fontname="helvetica-bold")
    
    y = 90
    # Draw table headers
    page.insert_text(fitz.Point(35, y), "Code", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(100, y), "Item Description", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(350, y), "Unit", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(400, y), "Qty", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(460, y), "Rate (AED)", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(520, y), "Total (AED)", fontsize=9, fontname="helvetica-bold")
    
    page.draw_line(fitz.Point(30, y+10), fitz.Point(565, y+10), color=(0,0,0), width=1)
    y += 25
    
    for idx, item in enumerate(boq_items):
        # Handle page overflow
        if y > 780:
            page.insert_text(fitz.Point(30, 810), f"Q.S Hub BOQ Report — Page {page_num}", fontsize=8, color=(0.5,0.5,0.5))
            page_num += 1
            page = doc.new_page(width=595, height=842)
            
            # Draw header on new page
            page.draw_rect(fitz.Rect(0, 0, 595, 50), color=(0.23, 0.51, 0.96), fill=(0.23, 0.51, 0.96))
            page.insert_text(fitz.Point(30, 30), f"BOQ Itemized Specifications — Page {page_num}", fontsize=14, color=(1, 1, 1), fontname="helvetica-bold")
            
            y = 90
            page.insert_text(fitz.Point(35, y), "Code", fontsize=9, fontname="helvetica-bold")
            page.insert_text(fitz.Point(100, y), "Item Description", fontsize=9, fontname="helvetica-bold")
            page.insert_text(fitz.Point(350, y), "Unit", fontsize=9, fontname="helvetica-bold")
            page.insert_text(fitz.Point(400, y), "Qty", fontsize=9, fontname="helvetica-bold")
            page.insert_text(fitz.Point(460, y), "Rate (AED)", fontsize=9, fontname="helvetica-bold")
            page.insert_text(fitz.Point(520, y), "Total (AED)", fontsize=9, fontname="helvetica-bold")
            page.draw_line(fitz.Point(30, y+10), fitz.Point(565, y+10), color=(0,0,0), width=1)
            y += 25
            
        code = str(item.get("code") if item.get("code") is not None else f"ITEM-{idx+1}")
        desc = str(item.get("desc_en") or item.get("name") or "N/A")
        if len(desc) > 38:
            desc = desc[:35] + "..."
            
        unit = str(item.get("unit") or "unit")
        qty = float(item.get("qty", 0.0))
        rate = float(item.get("rate_aed", 0.0))
        total = float(item.get("total_aed", 0.0))
        
        page.insert_text(fitz.Point(35, y), code, fontsize=8)
        page.insert_text(fitz.Point(100, y), desc, fontsize=8)
        page.insert_text(fitz.Point(350, y), unit, fontsize=8)
        page.insert_text(fitz.Point(400, y), f"{qty:,.2f}", fontsize=8)
        page.insert_text(fitz.Point(460, y), f"{rate:,.2f}", fontsize=8)
        page.insert_text(fitz.Point(520, y), f"{total:,.2f}", fontsize=8)
        
        # Zebra striping/lines
        page.draw_line(fitz.Point(30, y+8), fitz.Point(565, y+8), color=(0.9, 0.9, 0.9), width=0.5)
        y += 18
        
    # Draw summary line at the end
    if y > 760:
        page.insert_text(fitz.Point(30, 810), f"Q.S Hub BOQ Report — Page {page_num}", fontsize=8, color=(0.5,0.5,0.5))
        page = doc.new_page(width=595, height=842)
        y = 60
    else:
        y += 10
        
    page.draw_line(fitz.Point(30, y), fitz.Point(565, y), color=(0.23, 0.51, 0.96), width=1.5)
    y += 15
    page.insert_text(fitz.Point(300, y), "GRAND TOTAL PROJECT COST (إجمالي التكلفة المقدرة):", fontsize=9, fontname="helvetica-bold")
    page.insert_text(fitz.Point(500, y), f"{total_project_cost:,.2f} AED", fontsize=10, fontname="helvetica-bold", color=(0.23, 0.51, 0.96))
    
    # Save PDF
    os.makedirs(os.path.dirname(os.path.abspath(output_pdf_path)), exist_ok=True)
    doc.save(output_pdf_path)
    doc.close()
    
    # Cleanup temp chart
    if os.path.exists(chart_path):
        try:
            os.remove(chart_path)
        except Exception:
            pass
            
    return True
