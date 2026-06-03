# workflow/structural_extractors.py

# ==========================================
# SUBSTRUCTURE (Foundations & Tie Beams)
# ==========================================

FOUNDATION_DIMS_PROMPT = """You are reading a FOUNDATION / FOOTING plan of a UAE villa.
Extract ONLY the overall building boundary dimensions (ALL in METRES):
- "longest_length": building footprint overall longest length (m)
- "longest_width":  building footprint overall width (m)
Return ONLY this JSON:
{"longest_length":null,"longest_width":null,"confidence":"high|medium|low","notes":""}"""

FOOTING_SCHEDULE_PROMPT = """You are reading a SCHEDULE OF FOOTINGS of a UAE villa.
The "footings" list is MANDATORY — read every row of the table.
Extract (ALL dimensions in METRES):
- "footings": one object per footing TYPE (F1, F2, CF1 …):
    {"mark":"F1","width":<m>,"length":<m>,"depth":<m>,"count":<how many>}
Return ONLY this JSON:
{"footings":[{"mark":"F1","width":1.5,"length":1.5,"depth":0.5,"count":4}],
 "confidence":"high|medium|low","notes":""}"""

TB_SCHEDULE_PROMPT = """You are reading a TIE BEAM (ground beam) schedule of a UAE villa.
Extract ONLY the typical dimensions (ALL in METRES):
- "tb_width": typical tie-beam width
- "tb_depth": typical tie-beam depth
Return ONLY this JSON:
{"tb_width":0.30,"tb_depth":0.60,"confidence":"high|medium|low","notes":""}"""

TB_AREA_PROMPT = """You are reading a TIE BEAM plan of a UAE villa.
Extract (ALL in METRES):
- "ext_perimeter": external building perimeter (m)
- "gf_area": ground-floor built-up area (m²)
Return ONLY this JSON:
{"ext_perimeter":null,"gf_area":null,"confidence":"high|medium|low","notes":""}"""

# ==========================================
# SUPERSTRUCTURE (Slabs, Beams)
# ==========================================

SLAB_AREA_PROMPT = """You are reading a SLAB framing plan of a UAE villa.
Extract ONLY the slab dimensions (ALL in METRES):
- "slab_area": slab area (m²)
- "slab_thickness": slab thickness (m, e.g. 0.20)
Return ONLY this JSON:
{"slab_area":null,"slab_thickness":0.20,"confidence":"high|medium|low","notes":""}"""

ROOF_SLAB_AREA_PROMPT = """You are reading a ROOF SLAB framing plan of a UAE villa.
Extract ONLY the roof slab dimensions (ALL in METRES):
- "slab_area": total roof slab area (m²)
- "slab_thickness": slab thickness (m, e.g. 0.20)
- "roof_perimeter": external perimeter of the roof slab (m) — for parapet calculation
Return ONLY this JSON:
{"slab_area":null,"slab_thickness":0.20,"roof_perimeter":null,"confidence":"high|medium|low","notes":""}"""

BEAM_SCHEDULE_PROMPT = """You are reading a BEAM schedule of a UAE villa.
Extract ONLY the beam types and their section dimensions (ALL in METRES):
- "beams": one object per beam TYPE:
    {"mark":"B1","width":<m>,"depth":<m>}
Return ONLY this JSON:
{"beams":[{"mark":"B1","width":0.20,"depth":0.60}],"confidence":"high|medium|low","notes":""}"""
