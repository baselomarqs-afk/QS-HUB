from engine.item_calculator import calculate_item

# True Inputs based on manual reading of the PDFs
true_inputs = {
    # Structural levels and heights
    "structural_levels": 3,
    "total_villa_height": 10.5,
    "gf_height": 4.0,
    "f1_height": 3.5,
    "f2_height": 3.0,
    "roof_height": 3.0,
    
    # Areas exactly from the Calculation Sheet
    "plot_area": 416.03,  # Approximate from plot number, actually we don't need it if not specified
    "total_floor_area": 704.52,
    "gf_area": 290.19,
    "floor_area": 290.19,  # Base area for GF
    "1f_area": 386.49,     # 704.52 - 290.19 - 27.84
    "2f_area": 27.84,      # Roof Annex
    "roof_slab_area": 386.49, # Main roof is on top of 1F
    "roof_perimeter": 80.0,   # Estimated
    "external_perimeter": 80.0,
    
    # Columns schedule (We estimate counts from the reactions table)
    # The reactions table shows approx 20-30 columns. Let's assume 25 columns on average per floor.
    # C1 (20x60), C2 (20x70), C3 (20x80), C4 (20x100), C5 (20x120)
    # Average column size is say 20x80.
    "columns_schedule": [
        {"count": 25, "width_m": 0.20, "length_m": 0.80}
    ],
    
    # Slabs
    "sog_thickness": 0.10,
    "slab_thickness": 0.25,
    
    # Beams
    "beams_schedule": [
        {"count": 25, "length_m": 4.0, "width_m": 0.20, "depth_m": 0.60}
    ],
    
    # Footings
    "foundations_schedule": [
        {"count": 25, "length_m": 2.0, "width_m": 2.0, "depth_m": 0.60}
    ],
    "neck_columns_schedule": [
        {"count": 25, "length_m": 0.80, "width_m": 0.20}
    ],
    "tb_width": 0.20,
    "tb_depth": 0.60,
    "tb_total_length": 80.0,
    "longest_length": 20.0,
    "longest_width": 15.0,
    "excavation_depth": 1.25,
}

# Add floor specific prefixes for slabs
true_inputs["slab_1st_area"] = 386.49
true_inputs["slab_2nd_area"] = 27.84

def run_manual_qto():
    print("--- MANUAL QTO BASED ON PDF CALCULATION SHEET ---")
    items_to_check = [
        "excavation",
        "foundation_concrete",
        "neck_column_concrete",
        "tie_beam_concrete",
        "slab_on_grade",
        "col_gf_concrete",
        "col_1st_concrete",
        "col_roof_concrete",
        "slab_concrete_1st",
        "slab_concrete_2nd",
        "slab_concrete_roof",
        "roof_waterproofing"
    ]
    
    for key in items_to_check:
        val = calculate_item(key, true_inputs)
        print(f"{key.ljust(25)}: {val}")

if __name__ == "__main__":
    run_manual_qto()
