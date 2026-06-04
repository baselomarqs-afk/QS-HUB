import math

def perform_floor_plan_sanity_checks(data: dict) -> list[str]:
    """
    Perform mathematical and geometric sanity checks on extracted architectural data.
    Returns a list of warning strings for any suspicious extractions.
    """
    warnings = []
    
    gf_area = data.get("gf_area", 0) or 0
    if gf_area <= 0:
        return warnings
        
    int_walls = data.get("int_walls_10cm_m", 0) + data.get("int_walls_20cm_m", 0)
    ext_perim = data.get("ext_perimeter", 0)
    
    # Check 1: Internal Walls vs Floor Area Ratio
    if int_walls > 0:
        ratio = int_walls / gf_area
        if ratio < 0.3:
            warnings.append(f"Internal walls length ({int_walls}m) seems very low for the floor area ({gf_area}m²). Ratio is {ratio:.2f} (typical is 0.5-2.0). The AI may have missed some segments.")
        elif ratio > 5.0:
            warnings.append(f"Internal walls length ({int_walls}m) seems very high for the floor area ({gf_area}m²). Ratio is {ratio:.2f} (typical is 0.5-2.0). The AI may have double-counted.")
            
    # Check 2: External Perimeter vs Floor Area
    if ext_perim > 0:
        # A perfectly square building has perimeter = 4 * sqrt(area)
        # Most buildings are slightly more complex, so 4 to 6 times sqrt(area) is normal.
        expected_min = 3.5 * math.sqrt(gf_area)
        expected_max = 7.0 * math.sqrt(gf_area)
        
        if ext_perim < expected_min:
            warnings.append(f"External perimeter ({ext_perim}m) is suspiciously small for the floor area ({gf_area}m²). Expected minimum: ~{expected_min:.1f}m.")
        elif ext_perim > expected_max:
            warnings.append(f"External perimeter ({ext_perim}m) is suspiciously large for the floor area ({gf_area}m²). Expected maximum: ~{expected_max:.1f}m.")
            
    # Check 3: Room Validation
    rooms = data.get("rooms", [])
    if not rooms and gf_area > 20:
        warnings.append("No rooms were detected, but the floor area is > 20m².")
        
    for r in rooms:
        r_name = r.get("name", "Unknown Room")
        r_area = r.get("area_m2", 0) or 0
        r_l = r.get("length_m", 0) or 0
        r_w = r.get("width_m", 0) or 0
        
        if r_l > 0 and r_w > 0:
            calc_area = r_l * r_w
            if r_area > 0:
                diff = abs(calc_area - r_area) / r_area
                if diff > 0.2:  # 20% tolerance for non-rectangular rooms
                    warnings.append(f"Room '{r_name}' dimensions ({r_l}m x {r_w}m = {calc_area:.1f}m²) don't match the extracted area ({r_area}m²).")
            
    return warnings

def perform_structural_sanity_checks(data: dict, drawing_type: str) -> list[str]:
    """
    Sanity checks for structural elements.
    """
    warnings = []
    
    if drawing_type in ["foundation_plan", "tie_beam"]:
        l = data.get("longest_length", 0) or 0
        w = data.get("longest_width", 0) or 0
        if l > 0 and w > 0:
            if l < 5 or w < 5:
                warnings.append(f"Overall dimensions ({l}m x {w}m) seem too small for a villa. Are they in meters?")
                
        if drawing_type == "tie_beam":
            tb_len = data.get("tb_total_length", 0) or 0
            if tb_len > 0 and l > 0 and w > 0:
                approx_perim = (l + w) * 2
                if tb_len < approx_perim * 0.8:
                    warnings.append(f"Tie beam total length ({tb_len}m) is less than the building perimeter (~{approx_perim}m). Missing internal tie beams?")
                    
    elif drawing_type in ["ground_floor_plan", "roof_slab", "slab_plan"]:
        slab_thickness = data.get("slab_thickness", 0) or 0
        if slab_thickness > 0:
            if slab_thickness < 0.10:
                warnings.append(f"Slab thickness ({slab_thickness}m) is extremely thin (<10cm).")
            elif slab_thickness > 0.50:
                warnings.append(f"Slab thickness ({slab_thickness}m) is extremely thick (>50cm). Is this a raft foundation?")
                
    return warnings
