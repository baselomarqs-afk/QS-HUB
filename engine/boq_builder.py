"""
يجمع كل النتائج في جدول BOQ نهائي محدد بـ 64 بنداً بالترتيب والمسميات القياسية
"""
import pandas as pd
from typing import Dict, Any


def build_boq_dataframe(
    sub_results: Dict,
    super_results: Dict,
    finish_results: Dict,
    opening_results: Dict,
    num_floors: int,
    setting_out: Dict,
) -> pd.DataFrame:
    """يبني DataFrame جاهز للعرض والتصدير مطابق تماماً للبنود الـ 64 المطلوبة"""

    rows = []
    item_num = 1

    def add_section(title: str):
        rows.append({
            "#": "",
            "Description (English)": f"▌ {title}",
            "البيان": "",
            "Unit": "",
            "Quantity": "",
            "_is_header": True,
        })

    def add_item(en: str, ar: str, unit: str, qty: float):
        nonlocal item_num
        rows.append({
            "#": item_num,
            "Description (English)": en,
            "البيان": ar,
            "Unit": unit,
            "Quantity": round(float(qty or 0), 2),
            "_is_header": False,
        })
        item_num += 1

    # 1. Foundations | الأساسات
    add_section("Foundations | الأساسات")
    add_item("Excavation", "الحفر", "m³", sub_results.get("excavation", (0.0,))[0])
    add_item("Foundation PCC (Blinding)", "بيتون عادي الأساسات", "m³", sub_results.get("found_pcc", (0.0,))[0])
    add_item("Foundation Concrete", "خرسانة الأساسات", "m³", sub_results.get("found_concrete", (0.0,))[0])
    add_item("Foundation Bitumen", "بيتومين الأساسات", "m²", sub_results.get("found_bitumen", (0.0,))[0])
    add_item("Neck Column Concrete", "خرسانة أعمدة الرقبة", "m³", sub_results.get("neck_concrete", (0.0,))[0])
    add_item("Neck Column Bitumen", "بيتومين أعمدة الرقبة", "m²", sub_results.get("neck_bitumen", (0.0,))[0])
    add_item("Anti-Termite (Foundations)", "مبيد حشرات الأساسات", "m²", sub_results.get("anti_termite_f", (0.0,))[0])
    add_item("Polyethylene Sheet (Foundations)", "نايلون الأساسات", "m²", sub_results.get("poly_found", (0.0,))[0])
    add_item("Road Base (Sub-Grade Fill)", "الرمل المدموك", "m³", sub_results.get("road_base", (0.0,))[0])
    add_item("Backfill", "الردم", "m³", sub_results.get("backfill", (0.0,))[0])

    # 2. Tie Beam | الميدة
    add_section("Tie Beam | الميدة")
    add_item("Tie Beam Concrete", "خرسانة الميدة", "m³", sub_results.get("tb_concrete", (0.0,))[0])
    add_item("Tie Beam PCC (Blinding)", "بيتون عادي الميدة", "m³", sub_results.get("tb_pcc", (0.0,))[0])
    add_item("Tie Beam Bitumen", "بيتومين الميدة", "m²", sub_results.get("tb_bitumen", (0.0,))[0])
    add_item("Slab on Grade Concrete", "خرسانة بلاطة الأرضية", "m³", sub_results.get("sog", (0.0,))[0])
    add_item("Solid Block Work (Sub-Grade)", "بلوك مصمت تحت الأرض", "m³", sub_results.get("solid_bw", (0.0,))[0])
    add_item("Block Work Bitumen", "بيتومين البلوك", "m²", sub_results.get("bw_bitumen", (0.0,))[0])
    add_item("Anti-Termite (Tie Beam)", "مبيد حشرات الميدة", "m²", sub_results.get("anti_termite_tb", (0.0,))[0])
    add_item("Polyethylene Sheet (Tie Beam)", "نايلون الميدة", "m²", sub_results.get("poly_tb", (0.0,))[0])

    # 3. Columns (All Floors) | الأعمدة
    add_section("Columns (All Floors) | الأعمدة")
    add_item("Column Concrete (GF → 1st Floor)", "خرسانة أعمدة الأرضي", "m³", super_results.get("cols_gf", (0.0,))[0])
    add_item("Column Concrete (1st → 2nd Floor)", "خرسانة أعمدة الأول", "m³", super_results.get("cols_f1", (0.0,))[0])
    add_item("Column Concrete (Roof)", "خرسانة أعمدة السطح", "m³", super_results.get("cols_roof", (0.0,))[0])

    # 4. 1st Floor Slab | بلاطة الدور الأول
    add_section("1st Floor Slab | بلاطة الدور الأول")
    add_item("Beam Concrete (1st Floor)", "خرسانة كمرات الأول", "m³", super_results.get("beams_gf", (0.0,))[0])
    add_item("Slab Concrete (1st Floor)", "خرسانة بلاطة الأول", "m³", super_results.get("slab_gf", (0.0,))[0])
    add_item("Staircase Concrete", "خرسانة الدرج", "m³", super_results.get("staircase", (0.0,))[0])

    # 5. 2nd Floor Slab | بلاطة الدور الثاني
    add_section("2nd Floor Slab | بلاطة الدور الثاني")
    add_item("Beam Concrete (2nd Floor)", "خرسانة كمرات الثاني", "m³", super_results.get("beams_f1", (0.0,))[0])
    add_item("Slab Concrete (2nd Floor)", "خرسانة بلاطة الثاني", "m³", super_results.get("slab_f1", (0.0,))[0])

    # 6. Roof Slab | بلاطة السطح
    add_section("Roof Slab | بلاطة السطح")
    add_item("Slab Concrete (Roof)", "خرسانة بلاطة السطح", "m³", super_results.get("slab_roof", (0.0,))[0])
    add_item("Beam Concrete (Roof)", "خرسانة كمرات السطح", "m³", super_results.get("beams_roof", (0.0,))[0])
    add_item("Parapet Block Work", "بلوك الباربيت", "m²", super_results.get("parapet_block", (0.0,))[0])
    add_item("Parapet Concrete Coping", "كمرة الباربيت", "m³", super_results.get("parapet_concrete", (0.0,))[0])

    # 7. Ground Floor Plan | مسقط الدور الأرضي
    add_section("Ground Floor Plan | مسقط الدور الأرضي")
    gf_res = finish_results.get("gf", {})
    add_item("Thermal Block External (GF)", "بلوك حراري خارجي أرضي", "m²", gf_res.get("thermal_block", 0.0))
    add_item("Internal Block Work (GF)", "بلوك داخلي أرضي", "m²", gf_res.get("int_block", 0.0))
    add_item("Dry Area Flooring (GF)", "بلاط الأرضي الجاف", "m²", gf_res.get("dry_floor", 0.0))
    add_item("Wet Area Flooring (GF)", "بلاط الأرضي الرطب", "m²", gf_res.get("wet_floor", 0.0))
    add_item("Wall Tiles (GF Wet Areas)", "بلاط جدران رطب أرضي", "m²", gf_res.get("wall_tiles", 0.0))
    add_item("Skirting (GF)", "قرنيش أرضي الأرضي", "m", gf_res.get("skirting", 0.0))
    add_item("Internal Paint (GF)", "دهان داخلي أرضي", "m²", gf_res.get("int_paint", 0.0))
    add_item("Internal Plaster (GF)", "لياسة داخلية أرضي", "m²", gf_res.get("int_plaster", 0.0))
    add_item("Dry Area Ceiling (GF)", "أسقف جافة أرضي", "m²", gf_res.get("dry_ceiling", 0.0))
    add_item("Wet Area Ceiling (GF)", "أسقف رطبة أرضي", "m²", gf_res.get("wet_ceiling", 0.0))
    add_item("Balcony Waterproofing (GF)", "عزل البلكونة أرضي", "m²", gf_res.get("balcony_wp", 0.0))

    # 8. 1st Floor Plan | مسقط الدور الأول
    add_section("1st Floor Plan | مسقط الدور الأول")
    f1_res = finish_results.get("f1", {})
    add_item("Thermal Block External (1F)", "بلوك حراري خارجي أول", "m²", f1_res.get("thermal_block", 0.0))
    add_item("Internal Block Work (1F)", "بلوك داخلي أول", "m²", f1_res.get("int_block", 0.0))
    add_item("Dry Area Flooring (1F)", "بلاط الأول الجاف", "m²", f1_res.get("dry_floor", 0.0))
    add_item("Wet Area Flooring (1F)", "بلاط الأول الرطب", "m²", f1_res.get("wet_floor", 0.0))
    add_item("Wall Tiles (1F Wet Areas)", "بلاط جدران رطب أول", "m²", f1_res.get("wall_tiles", 0.0))
    add_item("Wet Area Waterproofing (1F)", "عزل المناطق الرطبة أول", "m²", finish_results.get("wet_waterproofing", 0.0))
    add_item("Balcony Waterproofing (1F)", "عزل البلكونة أول", "m²", f1_res.get("balcony_wp", 0.0))
    add_item("Internal Plaster (1F)", "لياسة داخلية أول", "m²", f1_res.get("int_plaster", 0.0))
    add_item("Internal Paint (1F)", "دهان داخلي أول", "m²", f1_res.get("int_paint", 0.0))

    # 9. 2nd Floor Plan | مسقط الدور الثاني
    add_section("2nd Floor Plan | مسقط الدور الثاني")
    f2_res = finish_results.get("f2", {})
    add_item("Thermal Block External (2F)", "بلوك حراري خارجي ثاني", "m²", f2_res.get("thermal_block", 0.0))
    add_item("Internal Block Work (2F)", "بلوك داخلي ثاني", "m²", f2_res.get("int_block", 0.0))
    add_item("Dry Area Flooring (2F)", "بلاط الثاني الجاف", "m²", f2_res.get("dry_floor", 0.0))
    add_item("Wet Area Flooring (2F)", "بلاط الثاني الرطب", "m²", f2_res.get("wet_floor", 0.0))
    add_item("Wet Area Waterproofing (2F)", "عزل رطب ثاني", "m²", finish_results.get("wet_waterproofing", 0.0) if num_floors >= 3 else 0.0)
    add_item("Wall Tiles (2F)", "بلاط جدران رطب ثاني", "m²", f2_res.get("wall_tiles", 0.0))
    add_item("Internal Plaster (2F)", "لياسة داخلية ثاني", "m²", f2_res.get("int_plaster", 0.0))

    # 10. Roof Floor Plan | مسقط السطح
    add_section("Roof Floor Plan | مسقط السطح")
    add_item("Roof Waterproofing", "عزل السطح", "m²", finish_results.get("roof_waterproofing", 0.0))

    # 11. Elevations | الواجهات
    add_section("Elevations | الواجهات")
    add_item("External Plaster", "لياسة خارجية", "m²", finish_results.get("external_plaster", 0.0))
    add_item("External Finishes", "تشطيب خارجي", "m²", finish_results.get("external_finishes", 0.0))

    # 12. Setting Out / Site Plan | مخطط الموقع
    add_section("Setting Out / Site Plan | مخطط الموقع")
    add_item("Interlock Paving", "رصف إنترلوك", "m²", setting_out.get("interlock", 0.0))
    add_item("Compound Wall", "سور الموقع", "m", setting_out.get("compound_wall", 0.0))

    # 13. Door & Window Schedules | جداول الأبواب والنوافذ
    add_section("Door & Window Schedules | جداول الأبواب والنوافذ")
    add_item("Door Openings", "الأبواب", "Nr", opening_results.get("doors", {}).get("total_doors", 0.0) if isinstance(opening_results.get("doors"), dict) else opening_results.get("doors", 0.0))
    add_item("Window Openings", "النوافذ", "m²", opening_results.get("windows", {}).get("total_windows_area", 0.0) if isinstance(opening_results.get("windows"), dict) else opening_results.get("windows", 0.0))

    df = pd.DataFrame(rows)
    return df
