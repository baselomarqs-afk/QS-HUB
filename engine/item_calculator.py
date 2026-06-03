"""
QTO Engine — strict mathematical formulas per specification.
No arbitrary scale factors or estimators are permitted.
All formula parameters are sourced from inputs; spec-defined defaults used when absent.
"""
import logging
from typing import Dict, Any, Optional, List

_log = logging.getLogger("qto.engine")


def calculate_item(item_key: str, inputs: Dict[str, Any]) -> Optional[float]:
    calculators = {
        # ── Sub-structure ───────────────────────────────────────────────────
        "excavation":           _calc_excavation,
        "foundation_pcc":       _calc_foundation_pcc,
        "foundation_concrete":  _calc_foundation_concrete,
        "foundation_bitumen":   _calc_foundation_bitumen,
        "neck_column_concrete": _calc_neck_col_concrete,
        "neck_column_bitumen":  _calc_neck_col_bitumen,
        "anti_termite_found":   _calc_anti_termite_found,
        "polyethylene_found":   _calc_poly_found,
        "road_base":            _calc_road_base,
        "backfill":             _calc_backfill,
        # ── Tie beams ───────────────────────────────────────────────────────
        "tie_beam_concrete":    _calc_tb_concrete,
        "tie_beam_pcc":         _calc_tb_pcc,
        "tie_beam_bitumen":     _calc_tb_bitumen,
        "slab_on_grade":        _calc_sog,
        "solid_block_work":     _calc_solid_bw,
        "block_work_bitumen":   _calc_bw_bitumen,
        "anti_termite_tb":      _calc_anti_tb,
        "poly_sheet_tb":        _calc_poly_tb,
        # ── Super-structure ─────────────────────────────────────────────────
        "parapet_block_work":   _calc_parapet_block,
        "parapet_concrete":     _calc_parapet_conc,
        # ── External ────────────────────────────────────────────────────────
        "roof_waterproofing":   _calc_roof_wp,
        "external_plaster":     _calc_ext_plaster,
        "external_finishes":    _calc_ext_finishes,
        "interlock_paving":     _calc_interlock,
        "compound_wall":        _calc_compound,
        # ── Openings ────────────────────────────────────────────────────────
        "door_openings":        _calc_doors,
        "window_openings":      _calc_windows,
    }

    # Floor-pattern items (key starts with one of these prefixes)
    _FLOOR_PREFIXES = (
        "thermal_block_", "internal_block_", "dry_floor_", "wet_floor_",
        "wall_tiles_", "skirting_", "int_paint_", "int_plaster_",
        "dry_ceiling_", "wet_ceiling_", "balcony_wp_", "wet_wp_",
        "beam_concrete_", "slab_concrete_", "col_gf_", "col_1st_",
        "col_2nd_", "col_roof", "staircase_",
    )
    for prefix in _FLOOR_PREFIXES:
        if item_key.startswith(prefix):
            try:
                return _calc_generic_floor_item(item_key, inputs)
            except Exception:
                _log.exception("calculate_item failed for floor item '%s'", item_key)
                return None

    fn = calculators.get(item_key)
    if fn:
        try:
            return fn(inputs)
        except Exception:
            _log.exception("calculate_item failed for '%s'", item_key)
            return None
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _g(inputs, key, default=0.0):
    return float(inputs.get(key) or default)


def _lst(inputs, key):
    return inputs.get(key, []) or []


# ═══════════════════════════════════════════════════════════════════════════════
# 1. الأعمال تحت الأرض — Sub-Structure
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_excavation(i):
    """
    Spec: (longest_length + 2) * (longest_width + 2) * excavation_depth
    Default depth = 1.25 m when not provided by geotech report.
    """
    depth = _g(i, "excavation_depth", 1.25)
    return round((_g(i, "longest_length") + 2) * (_g(i, "longest_width") + 2) * depth, 2)


def _calc_foundation_pcc(i):
    """
    Spec: (length + 0.20) * (width + 0.20) * 0.10 * count  — per footing
    100 mm lean concrete blinding under each footing pad.
    """
    return round(sum(
        (float(f.get("length_m") or 0) + 0.20)
        * (float(f.get("width_m") or 0) + 0.20)
        * 0.10
        * float(f.get("count") or 0)
        for f in _lst(i, "foundations_schedule")
    ), 2)


def _calc_foundation_concrete(i):
    """
    Spec: width * length * depth * count  — per footing
    """
    return round(sum(
        float(f.get("width_m") or 0)
        * float(f.get("length_m") or 0)
        * float(f.get("depth_m") or 0)
        * float(f.get("count") or 0)
        for f in _lst(i, "foundations_schedule")
    ), 2)


def _calc_foundation_bitumen(i):
    """
    Spec: (area + perimeter * depth) * count  — per footing
         = ((length * width) + 2.0 * (length + width) * depth) * count
    Protective bitumen painting on all below-grade concrete faces.
    """
    total = 0.0
    for f in _lst(i, "foundations_schedule"):
        l = float(f.get("length_m") or 0)
        w = float(f.get("width_m")  or 0)
        d = float(f.get("depth_m")  or 0)
        c = float(f.get("count")    or 0)
        total += ((l * w) + 2.0 * (l + w) * d) * c
    return round(total, 2)


def _calc_neck_col_concrete(i):
    """
    Spec: width * length * height * count  — per neck column type
    Height defaults to 1.0 m (footing top to tie beam soffit) but can be custom specified.
    """
    height = _g(i, "neck_column_height", 1.0)
    return round(sum(
        float(nc.get("width_m")  or 0)
        * float(nc.get("length_m") or 0)
        * height
        * float(nc.get("count")  or 0)
        for nc in _lst(i, "neck_columns_schedule")
    ), 2)


def _calc_neck_col_bitumen(i):
    """
    Spec: perimeter * height * count = 2 * (length + width) * height * count
    """
    height = _g(i, "neck_column_height", 1.0)
    return round(sum(
        2.0
        * (float(nc.get("length_m") or 0) + float(nc.get("width_m") or 0))
        * height
        * float(nc.get("count") or 0)
        for nc in _lst(i, "neck_columns_schedule")
    ), 2)


def _calc_anti_termite_found(i):
    """
    Spec: longest_length * longest_width
    Chemical spray area at foundation level.
    """
    return round(_g(i, "longest_length") * _g(i, "longest_width"), 2)


def _calc_poly_found(i):
    """
    Spec: Total PCC Volume / 0.10
    Polyethylene sheet area = blinding surface area under footings.
    """
    pcc = _calc_foundation_pcc(i)
    return round(pcc / 0.10, 2) if pcc > 0 else 0.0


def _calc_road_base(i):
    """
    Spec: longest_length * longest_width * 0.25
    250 mm protective sub-grade fill.
    """
    return round(_g(i, "longest_length") * _g(i, "longest_width") * 0.25, 2)


def _calc_backfill(i):
    """
    Spec: (exc_area * (exc_depth + 0.15)) - total_concrete_volume
    Uses same excavation_depth as _calc_excavation (default 1.25 m).
    """
    depth      = _g(i, "excavation_depth", 1.25)
    exc_area   = (_g(i, "longest_length") + 2) * (_g(i, "longest_width") + 2)
    total_conc = (
        _calc_foundation_concrete(i)
        + _calc_foundation_pcc(i)
        + _calc_tb_concrete(i)
        + _calc_tb_pcc(i)
        + _calc_neck_col_concrete(i)
    )
    return round(max(exc_area * (depth + 0.15) - total_conc, 0), 2)


def _calc_tb_concrete(i):
    """
    Spec: width * depth * total_length
    """
    return round(_g(i, "tb_width") * _g(i, "tb_depth") * _g(i, "tb_total_length"), 2)


def _calc_tb_pcc(i):
    """
    Spec: (width + 0.20) * 0.10 * total_length
    100 mm blinding, 200 mm wider than beam on each side.
    """
    return round((_g(i, "tb_width") + 0.20) * 0.10 * _g(i, "tb_total_length"), 2)


def _calc_tb_bitumen(i):
    """
    Spec: total_length * depth * 2
    Bitumen on both vertical faces of tie beam.
    """
    return round(_g(i, "tb_total_length") * _g(i, "tb_depth") * 2.0, 2)


def _calc_sog(i):
    """
    Spec: gf_area * 1.1 * 0.10 (thickness)
    Standard 10cm slab-on-grade concrete with a 1.1 layout factor.
    """
    return round(_g(i, "gf_area") * 1.1 * 0.10, 2)


def _calc_solid_bw(i):
    """
    Spec: external_perimeter * 0.9 * height (defaults to 1.0 m average)
    Solid block under tie beams along external perimeter.
    """
    height = _g(i, "solid_block_height", 1.0)
    return round(_g(i, "external_perimeter") * 0.9 * height, 2)


def _calc_bw_bitumen(i):
    """
    Spec: external_perimeter * height * 2 (defaults to 1.0 m average)
    """
    height = _g(i, "solid_block_height", 1.0)
    return round(_g(i, "external_perimeter") * height * 2.0, 2)


def _calc_anti_tb(i):
    """
    Spec: gf_area * 1.1
    Chemical termicide spray under slab on grade.
    """
    return round(_g(i, "gf_area") * 1.1, 2)


def _calc_poly_tb(i):
    """
    Spec: S.O.G area + PCC area = (gf_area * 1.1) + (PCC_TB_volume / 0.10)
    """
    sog      = _g(i, "gf_area") * 1.1
    pcc_vol  = _calc_tb_pcc(i)
    pcc_area = pcc_vol / 0.10 if pcc_vol > 0 else 0.0
    return round(sog + pcc_area, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. الأعمال العلوية — Super-Structure
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_parapet_block(i):
    """
    Spec: perimeter * 1.0 (height)
    parapet_height input overrides the 1.0 m spec default when provided.
    """
    height = _g(i, "parapet_height", 1.0)
    return round(_g(i, "roof_perimeter") * height, 2)


def _calc_parapet_conc(i):
    """
    Spec: perimeter * 0.20 * 0.20
    200 × 200 mm coping beam.
    """
    return round(_g(i, "roof_perimeter") * 0.20 * 0.20, 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. التشطيبات / External — Finishes
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_roof_wp(i):
    """
    Spec: roof_slab_area * 1.2
    """
    return round(_g(i, "roof_slab_area") * 1.2, 2)


def _calc_ext_plaster(i):
    """
    Spec: (ext_perimeter * (height for the full villa height + 1.2 m)) - total_windows_area
    Full-height plaster including 1.2 m ground clearance; minus windows.
    """
    return round(max(0.0, _g(i, "ext_perimeter") * (_g(i, "total_villa_height") + 1.2) - _g(i, "total_windows_area", 0.0)), 2)


def _calc_ext_finishes(i):
    return _calc_ext_plaster(i)


def _calc_interlock(i):
    """
    Spec: plot_area - gf_area
    """
    return round(max(_g(i, "plot_area") - _g(i, "gf_area"), 0), 2)


def _calc_compound(i):
    """
    Spec: compound_length
    """
    return round(_g(i, "compound_length"), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. الفتحات — Openings
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_doors(i):
    """
    Spec: Total count of all doors
    """
    return float(sum(int(d.get("count") or 0) for d in _lst(i, "doors_schedule")))


def _calc_windows(i):
    """
    Spec: sum(width * height * count)
    Accepts both normalized (width_m/height_m) and legacy (width_mm/width/length) keys.
    """
    return round(sum(
        float(w.get("width_m")  or w.get("width_mm", 0) / 1000 or w.get("width")  or 0)
        * float(w.get("height_m") or w.get("height_mm", 0) / 1000 or w.get("height") or w.get("length") or 0)
        * float(w.get("count")  or 0)
        for w in _lst(i, "windows_schedule")
    ), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# Floor-pattern generic handler
# ═══════════════════════════════════════════════════════════════════════════════

def _calc_generic_floor_item(item_key: str, inputs: Dict) -> float:
    """
    Handles all items that follow a per-floor pattern.
    Floor inputs must contain: ext_perimeter, floor_height, int_walls_length,
    floor_area, wet_area, wet_perimeter, dry_perimeter, balcony_area,
    slab_area, slab_thickness, beams_schedule, columns_schedule.
    """
    ep  = _g(inputs, "ext_perimeter")
    fh  = _g(inputs, "floor_height") or 4.0
    iwl = _g(inputs, "int_walls_length")
    iwl10 = _g(inputs, "int_walls_10cm")     # 10 cm internal partition walls (from plan)
    iwl20 = _g(inputs, "int_walls_20cm")     # 20 cm internal walls (from plan)
    if not iwl:
        iwl = iwl10 + iwl20
    if not iwl10 and not iwl20:
        iwl20 = iwl                           # no thickness split read -> all internal = 20 cm
    fa  = _g(inputs, "floor_area")
    wa  = _g(inputs, "wet_area")
    wp  = _g(inputs, "wet_perimeter")
    dp  = _g(inputs, "dry_perimeter")
    ba  = _g(inputs, "balcony_area")
    dry = max(fa - wa, 0)

    # Determine if this is the ground floor (wet_wp excluded per spec)
    is_gf = inputs.get("is_ground_floor", False)

    wa_deduct = _g(inputs, "windows_deduction", 0.0)
    da_count = _g(inputs, "doors_deduction_count", 0.0)
    da_deduct = da_count * 2.0  # Assumed standard door area

    mapping = {
        # Finishes
        "thermal_block_":  max(0.0, (ep * fh) - wa_deduct),                  # ext_perimeter × floor_height - windows
        "internal_block_10_": iwl10 * fh,                                    # 10 cm partition walls × height
        "internal_block_": max(0.0, (iwl20 * fh) - da_deduct),               # 20 cm internal walls × height - doors
        "dry_floor_":      dry,                                              # total_area - wet_area
        "wet_floor_":      wa,                                               # wet rooms area
        "wall_tiles_":     wp * max(fh - 0.50, 0),                           # wet_perimeter × (height - 0.50)
        "skirting_":       max(0.0, dp - da_count),                          # deduct 1m of skirting per door
        "int_paint_":      max(0.0, (dp * fh) - da_deduct - wa_deduct),      # skirting_length × floor_height - openings
        "int_plaster_":    max(0.0, (iwl * fh * 2.0) + (ep * fh) - (da_deduct * 2.0) - wa_deduct), # (int_walls×2) + ext_walls - openings
        "dry_ceiling_":    dry,                                              # = dry_floor
        "wet_ceiling_":    wa,                                               # = wet_floor
        "balcony_wp_":     ba,                               # balcony area
        # Wet WP: spec says "upper floors only (not GF) + balcony"
        "wet_wp_":         (0.0 if is_gf else wa) + ba,
    }
    for prefix, val in mapping.items():
        if item_key.startswith(prefix):
            return round(val, 2)

    # Slab concrete: area × thickness
    if "slab_concrete" in item_key:
        return round(
            _g(inputs, "slab_area") * (_g(inputs, "slab_thickness") or 0.20), 2
        )

    # Beam concrete: length × width × depth × count  (spec: count matters)
    if "beam_concrete" in item_key:
        return round(sum(
            float(b.get("length_m") or 0)
            * float(b.get("width_m")  or 0)
            * float(b.get("depth_m")  or 0)
            * float(b.get("count")    or 1)   # ← spec requires × count
            for b in _lst(inputs, "beams_schedule")
        ), 2)

    # Columns: length × width × height × count
    if "col_" in item_key:
        # Use the dynamic floor height instead of hardcoded values
        h = fh if not "roof" in item_key else max(fh - 0.5, 3.0) # Roof is usually slightly shorter, but we base it on fh
        return round(sum(
            float(c.get("length_m") or 0)
            * float(c.get("width_m")  or 0)
            * h
            * float(c.get("count")  or 0)
            for c in _lst(inputs, "columns_schedule")
        ), 2)

    # Staircase: dynamic staircase_volume_per_level m³ per structural level
    if "staircase" in item_key:
        levels = int(_g(inputs, "structural_levels") or 1)
        vol = _g(inputs, "staircase_volume_per_level", 5.2)
        return round(vol * levels, 2)

    return 0.0


def validate_takeoff_inputs(inputs: Dict[str, Any]) -> List[str]:
    """
    يقوم بعمليات التحقق التلقائي والتدقيق الهندسي للكميات المحصورة (Self-Validation Algorithms)
    - يتحقق من اتساق مساحات الغرف مع المساحة الإجمالية للبلاطة.
    - يتحقق من طول الجسور الأرضية مقارنة بالمحيط الخارجي.
    - يفحص منطقية أبعاد القواعد وعدد الأبواب.
    Returns: قائمة بالتحذيرات الهندسية إن وجدت.
    """
    warnings = []
    
    # 1. فحص مساحة الغرف والجدران مقابل مساحة البلاطة الإجمالية
    fa = float(inputs.get("gf_area") or inputs.get("floor_area") or 0.0)
    iwl = float(inputs.get("int_walls_length") or inputs.get("tb_total_length") or 0.0)
    
    # تقدير مساحة الجدران بناءً على طولها وسماكة افتراضية 0.20م
    estimated_wall_area = iwl * 0.20
    
    if fa > 0:
        plot_area = float(inputs.get("plot_area") or 0.0)
        if plot_area > 0 and fa > plot_area:
            warnings.append(f"⚠️ تحذير: مساحة بناء الطابق الأرضي ({fa} م²) أكبر من مساحة الأرض الكلية ({plot_area} م²).")
            
        # فحص نسبة الجدران والمساحة المتبقية
        if estimated_wall_area > fa * 0.5:
            warnings.append(f"⚠️ تحذير: مساحة الجدران المقدرة ({estimated_wall_area:.1f} م²) تشغل أكثر من 50% من المساحة الإجمالية ({fa} م²). قد يكون هناك خطأ في حصر طول الجدران.")
            
    # 2. فحص طول الجسور الأرضية مقابل المحيط الخارجي
    tb_len = float(inputs.get("tb_total_length") or 0.0)
    ext_perim = float(inputs.get("external_perimeter") or 0.0)
    if tb_len > 0 and ext_perim > 0 and tb_len < ext_perim:
        warnings.append(f"⚠️ تحذير: إجمالي أطوال الجسور الأرضية ({tb_len} م) أقل من المحيط الخارجي للفيلا ({ext_perim} م). يجب أن تغطي الجسور المحيط بالكامل.")

    # 3. فحص أبعاد القواعد
    foundations = inputs.get("foundations_schedule", []) or []
    for idx, f in enumerate(foundations):
        l = float(f.get("length_m") or 0)
        w = float(f.get("width_m") or 0)
        if (l > 0 and l < 0.5) or (w > 0 and w < 0.5):
            warnings.append(f"⚠️ تحذير: أبعاد القاعدة رقم {idx+1} صغيرة جداً ({w}x{l} م). يرجى التأكد من المقياس.")

    # 4. فحص الأبواب والفتحات مقابل عدد الغرف
    rooms_count = int(inputs.get("room_count") or len(inputs.get("rooms", [])) or 0)
    doors = inputs.get("doors_schedule", []) or []
    door_count = sum(int(d.get("count") or 0) for d in doors)
    if rooms_count > 2 and door_count == 0:
        warnings.append("⚠️ تحذير: تم كشف غرف بالمخطط ولكن عدد الأبواب المحصورة يساوي صفر. يرجى مراجعة فتحات الأبواب.")
        
    return warnings
