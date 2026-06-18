import sys, json, os, asyncio
sys.path.append(r'c:\Users\basel\Downloads\New folder (3)\QTO -- WEB')
from utils.db import get_connection
from workflow.step3_extract import extract_page
import fitz
import numpy as np

async def re_extract_schedules():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT id, state_data FROM qto_projects WHERE id = 810001')
            r = cur.fetchone()
            pid = r['id'] if isinstance(r, dict) else r[0]
            data = r['state_data'] if isinstance(r, dict) else r[1]
            if isinstance(data, str): data = json.loads(data)
            
            ext_res = data.get('extraction_results', {})
            pdf_path = r'c:\Users\basel\Downloads\villas\Tender for Mr Adel AlBalooshi\Tender for Mr Adel AlBalooshi\ARCH\arch1766554442032.pdf'
            if not os.path.exists(pdf_path):
                print('PDF not found.')
                return
                
            doc = fitz.open(pdf_path)
            updated_pages = 0
            
            for p_id, p in ext_res.items():
                if not isinstance(p, dict): continue
                dtype = p.get('drawing_type')
                if dtype in ['arch_doors', 'arch_windows']:
                    idx = p.get('page_index')
                    if idx is not None:
                        print(f'Re-extracting page {idx+1} ({dtype})')
                        page = doc[idx]
                        pix = page.get_pixmap(dpi=200)
                        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        text = page.get_text()
                        
                        # run extraction (pass user_id = 0 for local)
                        res = extract_page(img_arr, dtype, text, 0)
                        
                        # preserve meta
                        res['pdf'] = p.get('pdf')
                        res['page_index'] = p.get('page_index')
                        res['page_num'] = p.get('page_num')
                        res['image_url'] = p.get('image_url')
                        res['drawing_type'] = dtype
                        res['detected_type'] = p.get('detected_type')
                        
                        ext_res[p_id] = res
                        updated_pages += 1
            doc.close()
            
            if updated_pages > 0:
                print('Running BOQ bridge to update totals...')
                from api.routers.data_review import reconstruct_project_inputs
                # reconstruct_project_inputs directly modifies state_data and sums everything
                reconstruct_project_inputs(data)
                
                from engine.project_boq_bridge import build_boq_dataframe_from_project
                import math
                c = data.get('confirmed_auto_data', {})
                try:
                    df, meta = build_boq_dataframe_from_project(c)
                    def clean_float(val):
                        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)): return 0.0
                        return val
                    boq_items = []
                    for _, row in df.iterrows():
                        item = row.to_dict()
                        boq_items.append({k: clean_float(v) for k, v in item.items()})
                    data['boq_items'] = boq_items
                    data['boq_meta'] = meta
                    print('BOQ recalculated successfully!')
                except Exception as boq_e:
                    print('Failed to recalculate BOQ:', boq_e)
                    
                cur.execute('UPDATE qto_projects SET state_data = %s WHERE id = %s', (json.dumps(data), pid))
                conn.commit()
                print('DB updated with re-extracted schedules successfully.')
            else:
                print('No arch_doors or arch_windows pages found to re-extract.')

if __name__ == '__main__':
    asyncio.run(re_extract_schedules())
