import pdfplumber
import json
import os

ST_PDF = r'C:\Users\basel\Downloads\villas\Tender for Mr Adel AlBalooshi\Tender for Mr Adel AlBalooshi\ST\str_22_01_20261769077313996.pdf'
ARCH_PDF = r'C:\Users\basel\Downloads\villas\Tender for Mr Adel AlBalooshi\Tender for Mr Adel AlBalooshi\ARCH\arch1766554442032.pdf'

def extract_tables(pdf_path):
    tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_tables = page.extract_tables()
                for table in page_tables:
                    cleaned_table = []
                    for row in table:
                        cleaned_row = [str(cell).strip().replace('\n', ' ') if cell else '' for cell in row]
                        if any(cleaned_row):
                            cleaned_table.append(cleaned_row)
                    if cleaned_table:
                        tables.append({
                            "page": page_num + 1,
                            "data": cleaned_table
                        })
    except Exception as e:
        print(f"Error: {e}")
    return tables

st_tables = extract_tables(ST_PDF)
with open('st_tables.json', 'w', encoding='utf-8') as f:
    json.dump(st_tables, f, indent=2, ensure_ascii=False)

arch_tables = extract_tables(ARCH_PDF)
with open('arch_tables.json', 'w', encoding='utf-8') as f:
    json.dump(arch_tables, f, indent=2, ensure_ascii=False)

print("Tables extracted and saved to JSON files.")
