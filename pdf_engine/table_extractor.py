import os
import csv
import io

def extract_tables_as_csv(pdf_path: str, local_page_idx: int) -> str:
    """
    Attempts to extract structural/architectural tables from a specific PDF page using pdfplumber.
    Returns the tables formatted as a single CSV string.
    If no tables are found (e.g. raster/scanned PDF), returns an empty string.
    """
    if not os.path.exists(pdf_path):
        return ""
        
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if local_page_idx >= len(pdf.pages):
                return ""
                
            page = pdf.pages[local_page_idx]
            
            # Using custom settings to aggressively find grid-based tables
            table_settings = {
                "vertical_strategy": "lines", 
                "horizontal_strategy": "lines",
                "intersection_y_tolerance": 5,
            }
            
            tables = page.extract_tables(table_settings=table_settings)
            
            if not tables:
                # Fallback to text strategy if no strict lines found
                tables = page.extract_tables()
                
            if not tables:
                return ""
                
            output = io.StringIO()
            writer = csv.writer(output)
            
            for table_idx, table in enumerate(tables):
                writer.writerow([f"--- TABLE {table_idx + 1} ---"])
                for row in table:
                    # Clean up the row strings (replace newlines inside cells)
                    cleaned_row = []
                    for cell in row:
                        if cell is None:
                            cleaned_row.append("")
                        else:
                            cleaned_row.append(str(cell).replace("\n", " ").strip())
                    writer.writerow(cleaned_row)
                writer.writerow([])
                
            return output.getvalue().strip()
            
    except Exception as e:
        print(f"Error in extract_tables_as_csv: {e}")
        return ""
