"""
صفحة مقارنة وتراكب المخططات (Plan Comparison Page)
تسمح بمقارنة نسختين من المخطط بصرياً وإظهار الإضافات باللون الأخضر والتعديلات المحذوفة باللون الأحمر.
"""
import os
import streamlit as st
from utils.i18n import t, get_lang, is_rtl
from utils.plan_comparer import compare_plans
from pdf_engine.pdf_loader import page_to_pil
import tempfile

def render_plan_comparison():
    ar = (get_lang() == "ar")
    rtl = is_rtl()
    text_align = "right" if rtl else "left"
    
    title = "Visual Plan Comparison Overlay | مقارنة المخططات بصرياً" if ar else "Visual Plan Comparison Overlay"
    desc = (
        "قارن نسختين من المخطط المعماري أو الإنشائي لإظهار التعديلات والإضافات هندسياً. "
        "يتم تمييز العناصر المحذوفة باللون الأحمر، والعناصر المضافة باللون الأخضر."
        if ar else
        "Compare two versions of architectural or structural drawings to show edits. "
        "Deleted elements are highlighted in Red, and new additions in Green."
    )
    
    st.markdown(f"""
        <div style="text-align:{text_align}; margin-bottom:20px;">
            <h1 style="color:#3b82f6; margin:0; font-size:2.2rem; font-weight:800;">{title}</h1>
            <p style="color:#64748b; font-size:1.0rem; margin-top:5px;">{desc}</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    # ── Upload Section ──
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 📁 Version 1: Old Drawing (النسخة السابقة/القديمة)")
        pdf_1 = st.file_uploader(
            "Upload Old PDF", type=["pdf"], key="comp_pdf_1", label_visibility="collapsed"
        )
    with col2:
        st.markdown("##### 📁 Version 2: New Drawing (النسخة الجديدة/المعدلة)")
        pdf_2 = st.file_uploader(
            "Upload New PDF", type=["pdf"], key="comp_pdf_2", label_visibility="collapsed"
        )
        
    st.write("")
    
    # Options
    st.markdown("##### ⚙️ Comparison Settings | إعدادات المقارنة")
    c_opts1, c_opts2 = st.columns(2)
    with c_opts1:
        page_num = st.number_input(
            "Page Number (1-indexed) | رقم الصفحة", min_value=1, value=1, step=1, key="comp_page_num"
        )
    with c_opts2:
        dpi = st.slider(
            "Rendering Quality (DPI) | جودة الرسم", min_value=72, max_value=300, value=150, step=10, key="comp_dpi"
        )
        
    st.write("")
    
    if st.button(
        "🔍 Run Visual Comparison | ابدأ المقارنة البصرية",
        type="primary",
        use_container_width=True,
        disabled=not (pdf_1 and pdf_2)
    ):
        with st.spinner("Processing plans & generating overlay comparison..." if not ar else "جاري معالجة المخططات وتوليد تراكب المقارنة البصرية..."):
            try:
                # Save uploaded PDFs to temporary files
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp1:
                    tmp1.write(pdf_1.getbuffer())
                    path1 = tmp1.name
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp2:
                    tmp2.write(pdf_2.getbuffer())
                    path2 = tmp2.name
                
                # Check page indices (PyMuPDF is 0-indexed)
                import fitz
                doc1 = fitz.open(path1)
                doc2 = fitz.open(path2)
                p_idx = page_num - 1
                
                if p_idx >= doc1.page_count:
                    st.error(f"Error: Version 1 PDF only has {doc1.page_count} pages." if not ar else f"خطأ: النسخة الأولى تحتوي فقط على {doc1.page_count} صفحات.")
                    doc1.close()
                    doc2.close()
                    os.remove(path1)
                    os.remove(path2)
                    return
                if p_idx >= doc2.page_count:
                    st.error(f"Error: Version 2 PDF only has {doc2.page_count} pages." if not ar else f"خطأ: النسخة الثانية تحتوي فقط على {doc2.page_count} صفحات.")
                    doc1.close()
                    doc2.close()
                    os.remove(path1)
                    os.remove(path2)
                    return
                    
                doc1.close()
                doc2.close()
                
                # Output overlay path
                output_path = os.path.join(tempfile.gettempdir(), f"plan_comparison_diff_{page_num}.png")
                
                # Compare
                success = compare_plans(path1, path2, page_num=p_idx, output_path=output_path)
                
                # Cleanup uploaded temp files
                os.remove(path1)
                os.remove(path2)
                
                if success and os.path.exists(output_path):
                    st.session_state["comparison_output"] = output_path
                    st.success("Comparison completed successfully!" if not ar else "تمت المقارنة البصرية بنجاح!")
                else:
                    st.error("Error generating comparison image. Please check the PDFs." if not ar else "خطأ أثناء توليد صورة المقارنة. يرجى التحقق من الملفات.")
            except Exception as e:
                st.error(f"Error during comparison: {str(e)}")
                
    # Show comparison result if available
    comp_img_path = st.session_state.get("comparison_output")
    if comp_img_path and os.path.exists(comp_img_path):
        st.divider()
        st.markdown("### 🗺️ Visual Comparison Output | تراكب المقارنة البصرية")
        
        # Legend
        st.markdown(
            f"""
            <div style="display:flex; gap:20px; align-items:center; justify-content:center; margin-bottom:15px; font-weight:600;">
                <div style="display:flex; align-items:center; gap:6px;">
                    <div style="width:18px; height:18px; background-color:#ef4444; border-radius:4px;"></div>
                    <span>{"Deletions (items removed)" if not ar else "العناصر المحذوفة (السابقة)"}</span>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <div style="width:18px; height:18px; background-color:#22c55e; border-radius:4px;"></div>
                    <span>{"Additions (new elements)" if not ar else "العناصر المضافة (الجديدة)"}</span>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <div style="width:18px; height:18px; background-color:#cbd5e1; border-radius:4px; border:1px solid #94a3b8;"></div>
                    <span>{"Unchanged elements" if not ar else "العناصر غير المعدلة"}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Load and display
        st.image(comp_img_path, use_container_width=True, caption=f"Page {page_num} comparison diff")
        
        # Add download button for the diff image
        with open(comp_img_path, "rb") as f:
            btn_bytes = f.read()
        st.download_button(
            label="⬇️ Download Visual Diff Image | تحميل صورة الفروقات البصرية",
            data=btn_bytes,
            file_name=f"plan_comparison_page_{page_num}.png",
            mime="image/png",
            use_container_width=True
        )
