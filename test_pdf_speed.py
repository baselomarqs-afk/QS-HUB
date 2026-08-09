import time
import fitz
import sys

def test_speed(pdf_path):
    t0 = time.time()
    doc = fitz.open(pdf_path)
    print(f"Opened in {time.time() - t0:.3f}s, {len(doc)} pages")
    
    t_render = 0
    t_text = 0
    
    pages_to_test = min(5, len(doc))
    for i in range(pages_to_test):
        page = doc[i]
        
        t1 = time.time()
        text = page.get_text()
        t_text += (time.time() - t1)
        
        t2 = time.time()
        rect = page.rect
        scale = min(1200.0 / max(rect.width, rect.height), 1.5) if max(rect.width, rect.height) > 0 else 1.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB, alpha=False)
        jpg = pix.tobytes("jpg", jpg_quality=90)
        t_render += (time.time() - t2)
        
    print(f"Text extraction ({pages_to_test} pages): {t_text:.3f}s")
    print(f"Rendering ({pages_to_test} pages): {t_render:.3f}s")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_speed(sys.argv[1])
    else:
        print("Provide a pdf path")
