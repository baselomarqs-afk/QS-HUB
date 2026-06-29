import React from 'react';
import { ZoomIn, ZoomOut, Plus, Trash2, Info } from 'lucide-react';

export default function ClassifyStep({
  classifiedPages,
  setClassifiedPages,
  selectedPageIndex,
  setSelectedPageIndex,
  zoom,
  setZoom,
  isArabic,
  handleSaveClassifications,
  loading
}) {
  const handleDuplicate = (e, idx) => {
    e.stopPropagation();
    const updated = [...classifiedPages];
    const newPage = { ...updated[idx], detected_type: 'unknown' };
    updated.splice(idx + 1, 0, newPage);
    setClassifiedPages(updated);
  };

  const handleRemove = (e, idx, pageNum) => {
    e.stopPropagation();
    const count = classifiedPages.filter(p => p.page_num === pageNum).length;
    if (count > 1) {
      const updated = [...classifiedPages];
      updated.splice(idx, 1);
      setClassifiedPages(updated);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
      {/* Step Instructions */}
      <div style={{ padding: '15px 20px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
        <div style={{ color: '#3b82f6', marginTop: '2px' }}><Info size={20} /></div>
        <div>
          <h4 style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', fontSize: '0.95rem' }}>
            {isArabic ? (
              <>ما المطلوب في هذه الخطوة؟ <span style={{color: 'var(--error, red)'}}>(المراجعة اليدوية لتصنيف الصفحات إلزامية)</span></>
            ) : (
              <>What to do in this step? <span style={{color: 'var(--error, red)'}}>(manual checking the pages classification is must )</span></>
            )}
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, lineHeight: '1.5' }}>
            {isArabic 
              ? 'قام الذكاء الاصطناعي بمحاولة التعرف على صفحات المخطط وتصنيفها. المطلوب منك هو مراجعة هذه القائمة بالنظر للصفحة على اليسار، وتأكيد نوع المخطط (قواعد، أعمدة، معماري... إلخ) أو تغييره من القائمة المنسدلة إذا كان غير صحيح. يمكنك تكرار الصفحة لتصنيفها بأكثر من نوع بالضغط على (+).'
              : 'The AI has attempted to automatically classify your drawings. Please review the list on the right while looking at the preview on the left. Correct any misclassified pages using the dropdown menu. You can also duplicate a page using (+) if it contains multiple schedules.'}
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '25px', height: 'calc(100vh - 230px)' }}>
      {/* Left Page Image Viewer */}
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ padding: '12px 18px', borderBottom: '1px solid var(--border-color)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontWeight: 700 }}>
            {isArabic ? 'معاينة المخطط' : 'Drawing Preview'} (Page {selectedPageIndex + 1})
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary" onClick={() => setZoom(prev => Math.max(0.5, prev - 0.2))} style={{ padding: '6px' }}><ZoomOut size={16} /></button>
            <button className="btn btn-secondary" onClick={() => setZoom(prev => Math.min(3, prev + 0.2))} style={{ padding: '6px' }}><ZoomIn size={16} /></button>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'auto', backgroundColor: '#334155', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '15px' }}>
          {classifiedPages[selectedPageIndex] && (
            <img 
              src={`${classifiedPages[selectedPageIndex].image_url}`}
              alt="Page preview"
              style={{ transform: `scale(${zoom})`, transformOrigin: 'center center', maxWidth: '100%', height: 'auto', transition: 'transform 0.1s ease', borderRadius: '4px' }}
            />
          )}
        </div>
      </div>

      {/* Right Classify Options */}
      <div className="glass-panel" style={{ padding: '25px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '5px' }}>
          {isArabic ? '2. نتائج التصنيف التلقائي للصفحات' : '2. Page Classification Results'}
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '20px' }}>
          {isArabic 
            ? 'يرجى مراجعة وتأكيد تصنيف الصفحات. اختر الصفحة لمشاهدة المخطط على اليسار وتعديل نوعه.'
            : 'Review classifications. Select a page, review its image on the left, and adjust the category if needed.'}
        </p>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
          {classifiedPages.map((page, idx) => (
            <div 
              key={idx}
              onClick={() => setSelectedPageIndex(idx)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: '8px',
                border: '1px solid var(--border-color)',
                backgroundColor: idx === selectedPageIndex ? 'var(--primary-glow)' : 'var(--bg-secondary)',
                cursor: 'pointer'
              }}
            >
              <div>
                <span style={{ fontWeight: 700, fontSize: '0.88rem' }}>
                  {page.pdf === 'structural' ? (isArabic ? 'إنشائي' : 'Structural') : (isArabic ? 'معماري' : 'Architectural')} P{page.page_num}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <select
                  className="form-input"
                  value={page.detected_type}
                  onChange={(e) => {
                    const updated = [...classifiedPages];
                    updated[idx].detected_type = e.target.value;
                    setClassifiedPages(updated);
                  }}
                  style={{ width: '160px', padding: '6px 10px', fontSize: '0.85rem' }}
                >
                  <option value="unknown">{isArabic ? 'غير مصنف' : 'Unknown'}</option>
                  <option value="foundations">{isArabic ? 'جدول القواعد (Foundations)' : 'Foundations Schedule'}</option>
                  <option value="tie_beam">{isArabic ? 'الميدات وبلاطة الأرضي (Tie Beams & S.O.G)' : 'Tie Beams & Slab on Grade'}</option>
                  <option value="upper_columns">{isArabic ? 'جدول الأعمدة (Columns Schedule)' : 'Columns Schedule'}</option>
                  <option value="neck_columns">{isArabic ? 'أعمدة الرقاب/القبو (Neck Columns)' : 'Neck Columns'}</option>
                  <option value="columns_1f">{isArabic ? 'أعمدة الأول (1st Floor Columns)' : '1st Floor Columns'}</option>
                  <option value="columns_2f">{isArabic ? 'أعمدة الثاني (2nd Floor Columns)' : '2nd Floor Columns'}</option>
                  <option value="columns_roof">{isArabic ? 'أعمدة السطح (Roof Columns)' : 'Roof Columns'}</option>
                  <option value="slab_1st">{isArabic ? 'سقف الأول (1st Floor Slab)' : '1st Floor Slab'}</option>
                  <option value="slab_2nd">{isArabic ? 'سقف الثاني (2nd Floor Slab)' : '2nd Floor Slab'}</option>
                  <option value="roof_slab">{isArabic ? 'سقف الملحق/السطح (Roof Slab)' : 'Roof Slab'}</option>
                  <option value="elevations">{isArabic ? 'الواجهات والمقاطع (Elevations / Sections)' : 'Elevations / Sections'}</option>
                  <option value="ground_floor_plan">{isArabic ? 'معماري الأرضي (Ground Floor Plan)' : 'Ground Floor Plan'}</option>
                  <option value="first_floor_plan">{isArabic ? 'معماري الأول (First Floor Plan)' : 'First Floor Plan'}</option>
                  <option value="second_floor_plan">{isArabic ? 'معماري الثاني (Second Floor Plan)' : 'Second Floor Plan'}</option>
                  <option value="roof_floor_plan">{isArabic ? 'معماري السطح (Roof Floor Plan)' : 'Roof Floor Plan'}</option>
                  <option value="arch_doors">{isArabic ? 'جدول الأبواب (Doors Schedule)' : 'Doors Schedule'}</option>
                  <option value="arch_windows">{isArabic ? 'جدول النوافذ (Windows Schedule)' : 'Windows Schedule'}</option>
                  <option value="sections">{isArabic ? 'مقاطع (Sections)' : 'Sections'}</option>
                  <option value="setting_out">{isArabic ? 'مخطط التوقيع (Setting Out)' : 'Setting Out'}</option>
                </select>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button type="button" onClick={(e) => handleDuplicate(e, idx)} title={isArabic ? 'إضافة تصنيف آخر لهذه الصفحة' : 'Add another classification for this page'} style={{ background: '#3b82f6', color: 'white', border: 'none', borderRadius: '4px', padding: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                    <Plus size={14} />
                  </button>
                  {classifiedPages.filter(p => p.page_num === page.page_num).length > 1 && (
                    <button type="button" onClick={(e) => handleRemove(e, idx, page.page_num)} title={isArabic ? 'حذف هذا التصنيف' : 'Remove classification'} style={{ background: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', padding: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        <button className="btn btn-primary" onClick={handleSaveClassifications} style={{ width: '100%' }} disabled={loading}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <div className="spin-anim" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
              <span>{isArabic ? 'جاري الحفظ...' : 'Saving & Proceeding...'}</span>
            </div>
          ) : (
            isArabic ? 'حفظ وتأكيد التصنيفات' : 'Save & Proceed to Extraction'
          )}
        </button>
      </div>
    </div>
    </div>
  );
}
