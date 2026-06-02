"""
مقارنة المخططات هندسياً وتراكب النسخ (Plan Overlay Comparison)
يقارن نسختين من المخطط ويظهر التعديلات بالألوان (الأحمر للحذف، الأخضر للإضافة)
"""
import cv2
import numpy as np
import fitz  # PyMuPDF
import os


def render_pdf_page(pdf_path: str, page_num: int = 0, dpi: int = 150) -> np.ndarray:
    """Renders a PDF page to a numpy BGR image array."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert pixmap to numpy array
    img_data = np.frombuffer(pix.samples, dtype=np.uint8)
    if pix.alpha:
        img_array = img_data.reshape((pix.height, pix.width, 4))
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    else:
        img_array = img_data.reshape((pix.height, pix.width, 3))
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
    doc.close()
    return img_array


def compare_plans(pdf_path_1: str, pdf_path_2: str, page_num: int = 0, output_path: str = None) -> bool:
    """
    Compares two PDF pages visually.
    - Highlights deletions (items present in version 1 but not in version 2) in Red.
    - Highlights additions (items present in version 2 but not in version 1) in Green.
    - Fades unchanged layout lines to light gray.
    Saves the resulting image to output_path.
    """
    try:
        # Render both PDF pages
        img1 = render_pdf_page(pdf_path_1, page_num)
        img2 = render_pdf_page(pdf_path_2, page_num)
        
        # Resize version 1 to match version 2's size
        h2, w2 = img2.shape[:2]
        img1 = cv2.resize(img1, (w2, h2))
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # Binary threshold (invert lines to white/255, background to black/0)
        _, thresh1 = cv2.threshold(gray1, 200, 255, cv2.THRESH_BINARY_INV)
        _, thresh2 = cv2.threshold(gray2, 200, 255, cv2.THRESH_BINARY_INV)
        
        # Additions: line pixel present in version 2 but missing in version 1
        additions = cv2.bitwise_and(thresh2, cv2.bitwise_not(thresh1))
        
        # Deletions: line pixel present in version 1 but missing in version 2
        deletions = cv2.bitwise_and(thresh1, cv2.bitwise_not(thresh2))
        
        # Create a faded grayscale background using version 2 (the current plan)
        # Unchanged elements look light gray
        bg_gray = cv2.cvtColor(gray2, cv2.COLOR_GRAY2BGR)
        bg_faded = cv2.addWeighted(bg_gray, 0.25, np.full_like(bg_gray, 255), 0.75, 0)
        
        # Draw additions in Green (BGR: 0, 180, 0)
        bg_faded[additions > 50] = [0, 180, 0]
        
        # Draw deletions in Red (BGR: 0, 0, 220)
        bg_faded[deletions > 50] = [0, 0, 220]
        
        # Save output image
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            cv2.imwrite(output_path, bg_faded)
            
        return True
    except Exception as e:
        print(f"[Plan Comparer Error] {e}")
        return False
