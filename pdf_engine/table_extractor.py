import os
import csv
import io

# Dense CAD sheets (hatches, door/window elevation symbols, title blocks) can contain
# 5,000-50,000+ vector line segments. Running pure-Python pdfplumber line-intersection
# on those pages hits O(N^3) CPU complexity and freezes low-CPU servers indefinitely.
_MAX_PDFPLUMBER_DRAWINGS = 1500


def _format_tables_csv(tables) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    written = 0
    for table in tables:
        if not table:
            continue
        cleaned_rows = []
        has_text = False
        for row in table:
            cleaned_row = []
            for cell in row:
                val = "" if cell is None else str(cell).replace("\n", " ").strip()
                if val:
                    has_text = True
                cleaned_row.append(val)
            if any(cleaned_row):
                cleaned_rows.append(cleaned_row)
        if not has_text or not cleaned_rows:
            continue
        written += 1
        writer.writerow([f"--- TABLE {written} ---"])
        for r in cleaned_rows:
            writer.writerow(r)
        writer.writerow([])
    return output.getvalue().strip()


def extract_tables_as_csv(pdf_path: str, local_page_idx: int) -> str:
    """
    Attempts to extract structural/architectural tables from a specific PDF page.
    1. Tries PyMuPDF's C-native `find_tables()` first (fast & safe on dense CAD pages).
    2. Falls back to `pdfplumber` ONLY when PyMuPDF finds nothing AND the page vector
       count is small enough to guarantee no O(N^3) CPU hang.
    Returns the tables formatted as a single CSV string, or "" if none found.
    """
    if not os.path.exists(pdf_path):
        return ""

    drawing_count = 0
    # 1. Fast C-native table detection via PyMuPDF (fitz)
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            if local_page_idx >= len(doc):
                return ""
            page = doc[local_page_idx]
            try:
                drawing_count = len(page.get_drawings())
            except Exception:
                drawing_count = 0

            # PyMuPDF find_tables is C-backed; skip only on extreme hatch-bomb sheets
            if hasattr(page, "find_tables") and drawing_count <= 15000:
                tf = page.find_tables()
                raw_tables = [t.extract() for t in (tf.tables if tf else [])]
                csv_text = _format_tables_csv(raw_tables)
                if csv_text:
                    return csv_text
    except Exception as e:
        print(f"PyMuPDF table extraction skipped: {e}")

    # 2. Guarded pdfplumber fallback:
    #    - Low-vector sheets (<= 1500 paths): full line-intersection strategy
    #    - Dense CAD sheets (> 1500 paths): text-alignment strategy only (no O(N^3) line hang)
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if local_page_idx >= len(pdf.pages):
                return ""

            page = pdf.pages[local_page_idx]

            if drawing_count <= _MAX_PDFPLUMBER_DRAWINGS:
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_y_tolerance": 5,
                }
                tables = page.extract_tables(table_settings=table_settings)
                if not tables:
                    tables = page.extract_tables()
            else:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                })
            if not tables:
                return ""

            return _format_tables_csv(tables)

    except Exception as e:
        print(f"Error in extract_tables_as_csv: {e}")
        return ""
