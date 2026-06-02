"""
Reads footing schedule, tie beam schedule, and beam schedule
from scanned STR drawing pages using Claude Vision API.

Usage:
    py _read_schedules.py sk-ant-api-key-here
    or set ANTHROPIC_API_KEY in env and just run: py _read_schedules.py
"""
import sys, os, io, re, base64, json, fitz
import anthropic
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── API key ───────────────────────────────────────────────────────────────────
API_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ANTHROPIC_API_KEY', '')
if not API_KEY:
    print("ERROR: No API key found.")
    print("  Usage: py _read_schedules.py sk-ant-XXXXX")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STR_PATH = r'B:\work\2 villas\New folder\STR-002.pdf'
OUT_DIR  = os.path.join(ROOT_DIR, '_schedule_images')
os.makedirs(OUT_DIR, exist_ok=True)

# ── Render a PDF page to a high-res PNG ───────────────────────────────────────
def render_page(pdf_path, page_index, dpi=200):
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat  = fitz.Matrix(dpi/72, dpi/72)
    pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img  = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img

def img_to_b64(img: Image.Image, max_px=2800) -> str:
    w, h = img.size
    if max(w, h) > max_px:
        scale = max_px / max(w, h)
        img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.standard_b64encode(buf.getvalue()).decode()

def ask_claude(b64_img: str, prompt: str) -> str:
    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type":       "image",
                    "source": {
                        "type":       "base64",
                        "media_type": "image/png",
                        "data":       b64_img,
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return msg.content[0].text

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ASSIGNMENTS
# S-00 (page 1)  = Foundation layout  → footing schedule (F1-F12 sizes)
# S-04 (page 5)  = Tie beam layout    → TB schedule (TB1, TB2 b×d)
# S-05 (page 6)  = 1st floor slab     → beam schedule (B1...) + slab thickness
# S-06 (page 7)  = Roof slab layout   → roof beam schedule + slab thickness
# ═══════════════════════════════════════════════════════════════════════════════

PAGES_TO_READ = {
    'foundation': {
        'page_index': 0,
        'save_name':  'S00_foundation_layout.png',
        'prompt': """
This is an engineering drawing of a foundation layout for a UAE villa.
There is a "SCHEDULE OF FOOTINGS" table on this drawing.

Please extract ALL rows from that schedule table and return ONLY this JSON (no extra text):
{
  "footings": [
    {
      "type":    "F1",
      "length_mm": 1200,
      "width_mm":  1200,
      "depth_mm":  500,
      "count": 8
    },
    ...
  ]
}

Rules:
- If dimensions are in cm, convert to mm (e.g. 120cm → 1200mm)
- "count" = number of footings of that type shown in the layout drawing
- Include ALL footing types (F1, F2, F3, F4, CF1, CF2, CF3, CF4, CF5, CF6, etc.)
- If you cannot read a value clearly, write null
- Return ONLY the JSON object, nothing else
"""
    },
    'tie_beam': {
        'page_index': 4,
        'save_name':  'S04_tie_beam_layout.png',
        'prompt': """
This is an engineering drawing of a tie beam layout for a UAE villa.
There is a "SCHEDULE OF TIE BEAMS" table showing beam cross-sections (b × d).

Please extract ALL tie beam types and return ONLY this JSON (no extra text):
{
  "tie_beams": [
    {
      "type":     "TB1",
      "width_mm":  400,
      "depth_mm":  600,
      "count_segments": 43
    },
    {
      "type":     "TB2",
      "width_mm":  300,
      "depth_mm":  500,
      "count_segments": 12
    }
  ],
  "wall_footings": [
    {
      "type":     "WF1",
      "width_mm":  200,
      "depth_mm":  400,
      "total_length_m": null
    }
  ],
  "slab_on_grade_thickness_mm": 100
}

Rules:
- Dimensions are usually in cm in UAE drawings — convert to mm
- count_segments = number of times that beam type label appears in the layout
- Return ONLY the JSON object, nothing else
"""
    },
    'slab_1f': {
        'page_index': 5,
        'save_name':  'S05_slab_1F.png',
        'prompt': """
This is a 1st floor slab/beam layout drawing for a UAE villa.
Extract the beam schedule and slab information.

Return ONLY this JSON (no extra text):
{
  "slab_thickness_mm": 200,
  "slab_area_m2": null,
  "beams": [
    {
      "mark":      "B1",
      "width_mm":   300,
      "depth_mm":   600,
      "span_m":     5.3,
      "count":      4
    }
  ],
  "notes": "any important notes you see"
}

Rules:
- Dimensions in UAE drawings are usually in mm or cm — check the scale
- count = number of beams of that mark/size
- Return ONLY the JSON, nothing else
"""
    },
    'slab_roof': {
        'page_index': 6,
        'save_name':  'S06_slab_roof.png',
        'prompt': """
This is a roof slab/beam layout drawing for a UAE villa.
Extract the beam schedule and slab information.

Return ONLY this JSON (no extra text):
{
  "slab_thickness_mm": 200,
  "slab_area_m2": null,
  "beams": [
    {
      "mark":      "B1",
      "width_mm":   300,
      "depth_mm":   600,
      "span_m":     5.3,
      "count":      4
    }
  ],
  "notes": "any important notes"
}

Rules:
- Return ONLY the JSON, nothing else
"""
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
results = {}

for name, cfg in PAGES_TO_READ.items():
    print(f"\n{'─'*70}")
    print(f"  Reading: {name.upper()}  (STR page {cfg['page_index']+1})")
    print(f"{'─'*70}")

    # Render
    img   = render_page(STR_PATH, cfg['page_index'], dpi=200)
    fname = os.path.join(OUT_DIR, cfg['save_name'])
    img.save(fname)
    print(f"  Saved image → {fname}")

    # Ask Claude
    b64 = img_to_b64(img)
    print(f"  Sending to Claude Vision...", end='', flush=True)
    try:
        raw = ask_claude(b64, cfg['prompt'])
        print(f" OK")

        # Strip markdown code fences if present
        clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`').strip()
        # Find the first { to the last }
        start = clean.find('{')
        end   = clean.rfind('}')
        if start >= 0 and end > start:
            clean = clean[start:end+1]

        parsed = json.loads(clean)
        results[name] = parsed
        print(f"  Parsed OK ✓")
        print(f"  {json.dumps(parsed, indent=4)}")

    except json.JSONDecodeError as e:
        print(f"\n  JSON parse error: {e}")
        print(f"  Raw response:\n{raw}")
        results[name] = {'_raw': raw, '_error': str(e)}
    except Exception as e:
        print(f"\n  ERROR: {e}")
        results[name] = {'_error': str(e)}

# ═══════════════════════════════════════════════════════════════════════════════
# Save results to JSON for use by _live_test.py
OUT_JSON = os.path.join(ROOT_DIR, '_schedule_data.json')
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*70}")
print(f"  All schedule data saved → {OUT_JSON}")
print(f"  Images saved           → {OUT_DIR}")
print(f"\n  Now run:  py _live_test_ai.py")
print(f"  to recalculate the BOQ using the exact schedule dimensions.")
print(f"{'='*70}")
