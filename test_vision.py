import asyncio
import os
from utils.key_manager import KeyManager
from workflow.step3_extract import _ask_ai_with_retry

prompt = """Analyze this door and window schedule table image. Output a JSON array with door types, dimensions, and EXACT quantities. 
If the quantity says 'PER DWG', say so. Look very carefully. 
Output ONLY JSON: {"doors": [{"type": "D1", "quantity": "..."}]}"""

async def main():
    km = KeyManager()
    km.load_keys()
    pdf_path = r"C:\Users\basel\Downloads\TY022-9132634-YOUSUF MOHAMMAD MAKKI HASSAN MAKKI\PDF\SCHDULES.pdf"
    
    # We must convert PDF to image first for Gemini to process it efficiently if step3_extract doesn't handle it directly.
    # step3_extract handles pdf paths directly!
    res = await _ask_ai_with_retry(pdf_path, prompt, km)
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
