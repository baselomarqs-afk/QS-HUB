"""
Reads footing / tie-beam / beam schedules from scanned STR drawings
using Google AI Vision API.

Usage:
    py _read_schedules_ai.py AIzaSy...
"""
import sys, os, io, re, json, fitz
from PIL import Image
import google.genai as genai
from google.genai import types

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── API key ───────────────────────────────────────────────────────────────────
API_KEY = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GOOGLE_API_KEY', '')
if not API_KEY:
    print("ERROR: No Google API key.  Usage: py _read_schedules_ai.py AIzaSy...")
    sys.exit(1)

client = genai.Client(api_key=API_KEY)
MODEL  = "gemini-2.5-flash"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STR_PATH = os.environ.get('STR_PDF_PATH', r'B:\work\2 villas\New folder\STR-002.pdf')
OUT_DIR  = os.path.join(ROOT_DIR, '_schedule_images')
OUT_JSON = os.path.join(ROOT_DIR, '_schedule_data.json')
CLASS_JSON = os.path.join(ROOT_DIR, '_page_classification.json')
os.makedirs(OUT_DIR, exist_ok=True)


def resolve_page_index(name: str, default: int | None) -> int | None:
    """
    Resolve the PDF page index for a given schedule name.
    Priority:
      1. The 'page_index' value in PAGES dict (if not None) — explicit override.
      2. Lookup in _page_classification.json under the matching type.
      3. None  → caller will skip.
    """
    if default is not None:
        return default
    # type aliases: schedule name → classifier page_type
    aliases = {
        'foundation':       'foundation',
        'tie_beam':         'tie_beam',
        'column_schedule':  'column_schedule',
        'slab_1f':          'slab_1f',
        'slab_2f':          'slab_2f',
        'slab_roof':        'slab_roof',
    }
    page_type = aliases.get(name)
    if not page_type or not os.path.exists(CLASS_JSON):
        return None
    try:
        with open(CLASS_JSON, encoding='utf-8') as f:
            cls = json.load(f)
        pdf_cls = cls.get(STR_PATH, {})
        # Pick the highest-confidence match
        best, best_conf = None, 0
        for idx_str, info in pdf_cls.items():
            if info.get('type') == page_type and info.get('confidence', 0) > best_conf:
                best, best_conf = int(idx_str), info['confidence']
        return best
    except Exception:
        return None

# ── Helpers ───────────────────────────────────────────────────────────────────
def render_page(pdf_path, page_index, dpi=220):
    doc  = fitz.open(pdf_path)
    page = doc[page_index]
    mat  = fitz.Matrix(dpi/72, dpi/72)
    pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img  = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img

def ask_ai(img: Image.Image, prompt: str, retries: int = 4) -> str:
    import time
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    image_bytes = buf.read()
    for attempt in range(retries):
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type='image/png')
            response   = client.models.generate_content(
                model=MODEL,
                contents=[image_part, prompt],
            )
            return response.text
        except Exception as e:
            if '503' in str(e) and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"\n  503 busy — retrying in {wait}s (attempt {attempt+1}/{retries})...",
                      end='', flush=True)
                time.sleep(wait)
            else:
                raise

def parse_json(raw: str) -> dict:
    clean = re.sub(r'```(?:json)?', '', raw).strip().strip('`').strip()
    start = clean.find('{')
    end   = clean.rfind('}')
    if start >= 0 and end > start:
        return json.loads(clean[start:end+1])
    raise ValueError("No JSON object found in response")


def count_beams_fitz(pdf_path: str, page_index: int, marks: list[str]) -> dict[str, int]:
    """
    Count beam label occurrences on a drawing page using fitz text extraction.
    AI Vision gives unreliable (often round) numbers for label counts;
    fitz reads the actual text tokens in the PDF, which is authoritative.

    Args:
        pdf_path:   Path to the STR PDF.
        page_index: 0-based page number.
        marks:      List of beam mark strings to count, e.g. ['B1','B2','HB1'].

    Returns:
        dict mapping mark → count, e.g. {'B1': 16, 'B2': 8, 'HB1': 2}
    """
    counts = {m.upper(): 0 for m in marks}
    try:
        doc  = fitz.open(pdf_path)
        page = doc[page_index]
        words = page.get_text("words")   # each entry: (x0,y0,x1,y1, word, ...)
        doc.close()
        for w in words:
            token = w[4].strip().upper()
            if token in counts:
                counts[token] += 1
    except Exception as e:
        print(f"  [fitz count] ERROR on page {page_index}: {e}")
    return counts

# ═══════════════════════════════════════════════════════════════════════════════
PAGES = {
    'foundation': {
        'page_index': 0,
        'save_name':  'S00_foundation_layout.png',
        'prompt': """You are a highly experienced Quantity Surveyor (QS) in the UAE. This is an engineering structural drawing of a FOUNDATION LAYOUT for a UAE villa.
Your task is to accurately extract data from the "SCHEDULE OF FOOTINGS" table.
The drawing might be blurry, have watermarks, or contain mixed Arabic/English text. Read carefully.

Return ONLY this exact JSON format (no explanation, no markdown tags):
{
  "footings": [
    {"type":"F1","long_mm":1200,"short_mm":1200,"depth_mm":500,"count":8},
    {"type":"F2","long_mm":1500,"short_mm":1500,"depth_mm":500,"count":4}
  ]
}

Strict Rules:
- Look for columns labeled "Length", "Width", "Depth" / "Thickness", and "No." / "Qty".
- long_mm / short_mm = plan dimensions of the footing pad in mm. If written as cm (e.g. 120), convert to mm (1200). If written in meters (e.g. 1.2), convert to mm (1200).
- depth_mm = thickness/height of the footing in mm.
- count = number of that footing type shown in the layout plan.
- Include ALL types mentioned (e.g. F1, F2, CF1, CF2, Strip Footing).
- If a value is unreadable or empty, write null. Do NOT guess.
- Return ONLY valid JSON, nothing else."""
    },
    'tie_beam': {
        'page_index': 4,
        'save_name':  'S04_tie_beam_layout.png',
        'prompt': """You are a highly experienced Quantity Surveyor (QS) in the UAE. This is an engineering structural drawing of a TIE BEAM LAYOUT for a UAE villa.
Locate the "SCHEDULE OF TIE BEAMS" table and any wall footing details.

Return ONLY this JSON format (no explanation, no markdown):
{
  "tie_beams": [
    {"type":"TB1","width_mm":400,"depth_mm":600},
    {"type":"TB2","width_mm":300,"depth_mm":500}
  ],
  "wall_footings": [
    {"type":"WF1","width_mm":200,"depth_mm":300}
  ]
}

Strict Rules:
- width_mm = beam width (horizontal, 'b' dimension).
- depth_mm = beam depth (vertical, 'd' dimension).
- Dimensions in UAE drawings are usually in cm or meters — YOU MUST convert to mm (e.g., 40cm → 400mm, 0.6m → 600mm).
- Return ONLY valid JSON, nothing else."""
    },
    'column_schedule': {
        'page_index': None,
        'save_name':  'S_column_schedule.png',
        'prompt': """You are a highly experienced Quantity Surveyor (QS) in the UAE. This is a structural drawing showing the SCHEDULE OF COLUMNS for a UAE villa.
This table is complex. It usually maps Column Marks (C1, C2) to different floor levels (e.g., Foundation to GF, GF to 1st, 1st to Roof).

Extract ALL columns from the schedule table and return ONLY this JSON (no markdown):
{
  "columns": [
    {"mark":"C1","width_mm":200,"depth_mm":400,
     "height_gf_mm":3500,"count_gf":12,
     "height_1f_mm":3300,"count_1f":12,
     "height_2f_mm":null,"count_2f":null,
     "height_roof_mm":1000,"count_roof":4}
  ]
}

Strict Rules:
- width_mm × depth_mm = column cross-section in mm. Convert cm to mm (e.g., 20x40 → 200x400).
- height_<floor>_mm = floor-to-floor height in mm. Look at the elevation notes on the side of the table.
- count_<floor> = how many columns of this mark exist on that floor level.
- If a column section changes size on a higher floor, note it.
- If a column stops at a certain floor, use null for height and count on higher floors.
- Include ALL column marks: C1, C2, SC, RC, Neck Columns, etc.
- Return ONLY valid JSON, nothing else."""
    },
    'slab_1f': {
        'page_index': 5,
        'save_name':  'S05_slab_1F.png',
        'prompt': """You are an expert QS. This is a structural drawing of the 1ST FLOOR SLAB LAYOUT for a UAE villa.
Find the "SCHEDULE OF 1st FLOOR BEAMS" table and the typical slab thickness note.

Return ONLY this JSON (no explanation, no markdown):
{
  "slab_thickness_mm": 200,
  "beams": [
    {"mark":"B1","width_mm":300,"depth_mm":600},
    {"mark":"HB1","width_mm":400,"depth_mm":700}
  ]
}

Strict Rules:
- slab_thickness_mm = overall solid slab thickness (often found in general notes on the page, e.g., "All slabs are 20cm thick unless noted"). Convert to mm.
- width_mm = beam web width (b dimension) in mm.
- depth_mm = total beam depth (d dimension) in mm.
- Include ALL marks shown in the table (B1, B2, HB1, DB1, CB1).
- DO NOT include counts.
- Return ONLY valid JSON."""
    },
    'slab_roof': {
        'page_index': 6,
        'save_name':  'S06_slab_roof.png',
        'prompt': """You are an expert QS. This is a structural drawing of the ROOF SLAB LAYOUT for a UAE villa.
Find the "SCHEDULE OF ROOF FLOOR BEAMS" table.

Return ONLY this JSON (no explanation, no markdown):
{
  "slab_thickness_mm": 200,
  "beams": [
    {"mark":"B1","width_mm":300,"depth_mm":600},
    {"mark":"HB1","width_mm":400,"depth_mm":700}
  ]
}

Strict Rules:
- slab_thickness_mm = overall slab thickness in mm.
- width_mm = beam web width in mm.
- depth_mm = total beam depth in mm.
- Convert all cm/m to mm.
- DO NOT include counts.
- Return ONLY valid JSON."""
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# Load any previously-extracted data so we skip already-done pages
results = {}
if os.path.exists(OUT_JSON):
    with open(OUT_JSON, encoding='utf-8') as f:
        try:
            existing = json.load(f)
            for k, v in existing.items():
                if '_error' not in v and '_raw' not in v:
                    results[k] = v
                    print(f"  Loaded from cache: {k}")
        except Exception:
            pass

for name, cfg in PAGES.items():
    if name in results:
        print(f"  Skipping {name} (already extracted)")
        continue

    # Auto-resolve page index from classifier when default is None
    pidx = resolve_page_index(name, cfg.get('page_index'))
    if pidx is None:
        print(f"\n  {name.upper()}: page not found in classification — skipping")
        continue
    cfg['page_index'] = pidx

    print(f"\n{'='*72}")
    print(f"  {name.upper()}  —  STR page {pidx+1}  ({cfg['save_name']})")
    print(f"{'='*72}")

    img   = render_page(STR_PATH, pidx, dpi=220)
    fpath = os.path.join(OUT_DIR, cfg['save_name'])
    img.save(fpath)
    w, h = img.size
    print(f"  Image: {w}×{h} px")

    print(f"  Asking AI Vision...", end='', flush=True)
    try:
        raw    = ask_ai(img, cfg['prompt'])
        print(f"  done")
        parsed = parse_json(raw)
        results[name] = parsed
        print(f"  Parsed OK")
        # Pretty-print key counts
        if name == 'foundation' and 'footings' in parsed:
            total_vol = 0
            for ft in parsed['footings']:
                l = (ft.get('long_mm')  or 0) / 1000
                s = (ft.get('short_mm') or 0) / 1000
                d = (ft.get('depth_mm') or 0) / 1000
                c = ft.get('count') or 0
                v = l * s * d * c
                total_vol += v
                print(f"    {ft['type']:5s}  {ft.get('long_mm','?')}×{ft.get('short_mm','?')}×{ft.get('depth_mm','?')}mm  ×{c}  = {v:.2f} m³")
            print(f"    ───────────────────────────────")
            print(f"    TOTAL FOOTINGS = {total_vol:.2f} m³")
        elif name == 'tie_beam' and 'tie_beams' in parsed:
            for tb in parsed['tie_beams']:
                print(f"    {tb['type']:5s}  {tb.get('width_mm','?')}×{tb.get('depth_mm','?')} mm")
            # ── Measure-assist: tie-beam run length from vector geometry ──────
            # Same method as slab beams — measured, not estimated.
            try:
                from _beam_length_from_plan import measure_tie_beams
                tbm = measure_tie_beams(STR_PATH, cfg['page_index'])
                print(f"  [measure] Tie-beam lengths on page {cfg['page_index']+1}:")
                for tb in parsed['tie_beams']:
                    mk = (tb.get('type') or '').upper()
                    m  = tbm.get(mk)
                    if m:
                        tb['length_m']          = m['measured_m']
                        tb['length_source']     = 'measured_vector'
                        tb['length_confidence'] = m['confidence']
                        print(f"    {mk:5s} → {m['measured_m']:.2f} m (conf {m['confidence']:.0%})")
                    else:
                        tb['length_m']      = 0.0
                        tb['length_source'] = 'not_found'
                        print(f"    {mk:5s} → not found (will fall back to estimate)")
            except Exception as e:
                print(f"  [measure] tie-beam skipped ({e})")
        elif 'beams' in parsed:
            for b in parsed['beams']:
                print(f"    {b['mark']:5s}  {b.get('width_mm','?')}×{b.get('depth_mm','?')}mm  ×{b.get('count','?')}")
            print(f"    Slab thickness: {parsed.get('slab_thickness_mm','?')} mm")

        # ── Fitz beam-count override for slab pages ───────────────────────
        if name in ('slab_1f', 'slab_2f', 'slab_roof') and 'beams' in parsed:
            marks  = [b['mark'] for b in parsed['beams'] if 'mark' in b]
            fitz_c = count_beams_fitz(STR_PATH, cfg['page_index'], marks)
            print(f"\n  [fitz] Beam label counts on page {cfg['page_index']+1}:")
            for b in parsed['beams']:
                mk  = b.get('mark', '').upper()
                cnt = fitz_c.get(mk, 0)
                old = b.get('count', '—')
                b['count']        = cnt
                b['count_source'] = 'fitz_text_extract'
                flag = '' if old == '—' else f'  (was {old} from AI)'
                print(f"    {mk:5s} → {cnt}{flag}")

            # ── Measure-assist: beam total length from vector geometry ─────
            # Beam concrete = length × width × depth (NOT × count). We measure
            # the run length per mark off the plan; the user confirms it in
            # Schedule Review. Values carry a confidence for low-trust flagging.
            try:
                from _beam_length_from_plan import measure_page
                meas = measure_page(STR_PATH, cfg['page_index'])
                print(f"  [measure] Beam lengths on page {cfg['page_index']+1}:")
                for b in parsed['beams']:
                    mk = b.get('mark', '').upper()
                    m  = meas.get(mk)
                    if m:
                        b['length_m']          = m['measured_m']
                        b['length_source']     = 'measured_vector'
                        b['length_confidence'] = m['confidence']
                        print(f"    {mk:5s} → {m['measured_m']:.2f} m "
                              f"(conf {m['confidence']:.0%})")
                    else:
                        b['length_m']      = 0.0
                        b['length_source'] = 'not_found'
                        print(f"    {mk:5s} → not found (confirm in review)")
            except Exception as e:
                print(f"  [measure] skipped ({e})")

        # ── Fitz column-count cross-check across floor pages ──────────────
        # Column marks (C1, C2, ...) appear on every floor layout page.
        # We count occurrences across foundation + slab pages and compare
        # against AI's schedule counts.
        if name == 'column_schedule' and 'columns' in parsed:
            marks = [c['mark'] for c in parsed['columns'] if 'mark' in c]
            # Map floor key → page_index from classifier results
            floor_pages = {}
            try:
                if os.path.exists(CLASS_JSON):
                    with open(CLASS_JSON, encoding='utf-8') as f:
                        cls = json.load(f).get(STR_PATH, {})
                    for idx, info in cls.items():
                        t = info.get('type')
                        if t in ('foundation', 'slab_1f', 'slab_2f', 'slab_roof'):
                            floor_pages[t] = int(idx)
            except Exception:
                pass
            # Map page_type → JSON key (which floor count to overwrite)
            page_to_floor = {
                'foundation': 'gf',
                'slab_1f':    '1f',
                'slab_2f':    '2f',
                'slab_roof':  'roof',
            }
            print(f"\n  [fitz] Column label counts (cross-floor):")
            for pt, pi in floor_pages.items():
                cf = count_beams_fitz(STR_PATH, pi, marks)
                fkey = page_to_floor[pt]
                for c in parsed['columns']:
                    mk = c.get('mark', '').upper()
                    n  = cf.get(mk, 0)
                    if n > 0:
                        old = c.get(f'count_{fkey}', '—')
                        c[f'count_{fkey}']        = n
                        c[f'count_{fkey}_source'] = 'fitz_text_extract'
                        print(f"    {mk:5s} {fkey:4s} → {n}  (was {old})")

    except json.JSONDecodeError as e:
        print(f"\n  JSON ERROR: {e}")
        print(f"  Raw:\n{raw[:800]}")
        results[name] = {'_raw': raw, '_error': str(e)}
    except Exception as e:
        print(f"\n  ERROR: {e}")
        results[name] = {'_error': str(e)}

# ── Save ─────────────────────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n{'='*72}")
print(f"  Schedule data saved → {OUT_JSON}")
print(f"  Run next:  py _live_test_ai.py")
print(f"{'='*72}")
