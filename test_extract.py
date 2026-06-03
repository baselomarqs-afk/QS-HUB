import numpy as np
from workflow.step3_extract import extract_page
import asyncio

# create a dummy image array (RGB)
page_arr = np.zeros((100, 100, 3), dtype=np.uint8)

try:
    print("Testing extract_page with ground_floor_plan...")
    data = extract_page(page_arr, "ground_floor_plan", "dummy text")
    print("SUCCESS!")
    print(data)
except Exception as e:
    import traceback
    traceback.print_exc()
