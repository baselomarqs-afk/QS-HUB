"""Quick crop script — extract just the plan view from S-04 to count TB labels."""
import fitz, io
from PIL import Image

STR_PATH = r'B:\work\2 villas\New folder\STR-002.pdf'
OUT_DIR  = r'C:\Users\basel\villa_qto\_schedule_images'

doc  = fitz.open(STR_PATH)
page = doc[4]
mat  = fitz.Matrix(300/72, 300/72)
pix  = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
img  = Image.open(io.BytesIO(pix.tobytes("png")))
doc.close()

w, h = img.size
print(f"Full page: {w}×{h}")

# Plan view occupies roughly left 55% of the page, full height minus bottom margin
plan = img.crop((0, int(h*0.03), int(w*0.56), int(h*0.77)))
plan.save(f'{OUT_DIR}/S04_plan_only.png')
print(f"Plan crop: {plan.size}")

# Also crop the right side which has wall footing details
right = img.crop((int(w*0.56), 0, int(w*0.85), int(h*0.77)))
right.save(f'{OUT_DIR}/S04_right_details.png')
print(f"Right crop: {right.size}")
