import React from 'react';
import { Trash2, Plus, Info } from 'lucide-react';

const ScheduleTableEditorModal = ({ isArabic, schedules, onSave, onClose }) => {
  const [footings, setFootings] = React.useState(schedules?.foundation?.footings || []);
  const [columns, setColumns] = React.useState(schedules?.superstructure?.columns || []);

  const handleUpdate = (state, setter, index, field, val) => {
    const updated = [...state];
    updated[index] = { ...updated[index], [field]: val };
    setter(updated);
  };

  const handleRemove = (state, setter, index) => {
    setter(state.filter((_, i) => i !== index));
  };

  const handleAdd = (setter, state, defaultPrefix) => {
    setter([...state, { type: `${defaultPrefix}${state.length + 1}`, length: 1.0, width: 1.0, count: 1 }]);
  };

  const renderTable = (title, state, setter, prefix) => (
    <div style={{ marginBottom: '25px', backgroundColor: '#1e293b', padding: '15px', borderRadius: '8px' }}>
      <h4 style={{ color: 'white', marginTop: 0, marginBottom: '10px', display: 'flex', justifyContent: 'space-between' }}>
        {title}
        <button type="button" onClick={() => handleAdd(setter, state, prefix)} style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '4px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Plus size={14} /> {isArabic ? 'إضافة صف' : 'Add Row'}
        </button>
      </h4>
      {state.length === 0 ? (
        <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{isArabic ? 'لا توجد بيانات مستخرجة.' : 'No data extracted.'}</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', color: 'white', fontSize: '0.85rem', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #334155' }}>
              <th style={{ padding: '8px 4px' }}>{isArabic ? 'النوع' : 'Type'}</th>
              <th style={{ padding: '8px 4px' }}>{isArabic ? 'الطول (م)' : 'Length (m)'}</th>
              <th style={{ padding: '8px 4px' }}>{isArabic ? 'العرض (م)' : 'Width (m)'}</th>
              <th style={{ padding: '8px 4px' }}>{isArabic ? 'العدد' : 'Count'}</th>
              <th style={{ padding: '8px 4px' }}></th>
            </tr>
          </thead>
          <tbody>
            {state.map((row, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #334155' }}>
                <td style={{ padding: '6px 4px' }}>
                  <input type="text" value={row.type || ''} onChange={(e) => handleUpdate(state, setter, i, 'type', e.target.value)} style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', color: 'white', padding: '4px', borderRadius: '4px' }} />
                </td>
                <td style={{ padding: '6px 4px' }}>
                  <input type="number" step="0.01" value={row.length || ''} onChange={(e) => handleUpdate(state, setter, i, 'length', parseFloat(e.target.value) || 0)} style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', color: 'white', padding: '4px', borderRadius: '4px' }} />
                </td>
                <td style={{ padding: '6px 4px' }}>
                  <input type="number" step="0.01" value={row.width || ''} onChange={(e) => handleUpdate(state, setter, i, 'width', parseFloat(e.target.value) || 0)} style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', color: 'white', padding: '4px', borderRadius: '4px' }} />
                </td>
                <td style={{ padding: '6px 4px' }}>
                  <input type="number" value={row.count || ''} onChange={(e) => handleUpdate(state, setter, i, 'count', parseInt(e.target.value) || 0)} style={{ width: '100%', background: '#0f172a', border: '1px solid #334155', color: 'white', padding: '4px', borderRadius: '4px' }} />
                </td>
                <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                  <button type="button" onClick={() => handleRemove(state, setter, i)} style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }} title={isArabic ? 'حذف' : 'Remove'}>
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.7)', zIndex: 9999, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
      <div style={{ background: 'var(--bg-primary)', padding: '25px', borderRadius: '12px', width: '100%', maxWidth: '800px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}>
        <h3 style={{ marginTop: 0, marginBottom: '15px', display: 'flex', justifyContent: 'space-between' }}>
          <span>{isArabic ? 'محرر الجداول الهندسية' : 'Engineering Schedules Editor'}</span>
          <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '1.2rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>&times;</button>
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>
          {isArabic 
            ? 'يمكنك هنا مراجعة وإضافة وتعديل بيانات القواعد والأعمدة يدوياً.' 
            : 'Review, add, or edit footings and columns data directly from the schedules.'}
        </p>
        
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px' }}>
          {renderTable(isArabic ? 'جدول القواعد (Footings)' : 'Footings Schedule', footings, setFootings, 'F')}
          {renderTable(isArabic ? 'جدول الأعمدة (Columns)' : 'Columns Schedule', columns, setColumns, 'C')}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
          <button type="button" onClick={onClose} className="btn" style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--border-color)' }}>
            {isArabic ? 'إلغاء' : 'Cancel'}
          </button>
          <button type="button" onClick={() => onSave({
            ...schedules,
            foundation: { ...(schedules?.foundation || {}), footings },
            superstructure: { ...(schedules?.superstructure || {}), columns }
          })} className="btn btn-primary" style={{ padding: '8px 16px' }}>
            {isArabic ? 'حفظ الجداول' : 'Save Schedules'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function VerifyStep({
  currentStep,
  projectId,
  token,
  confirmedData,
  extractionResults,
  sanityWarnings,
  updateConfirmedField,
  updateOpeningField,
  renderSourceBadge,
  hasEstimates,
  acknowledgedEstimates,
  setAcknowledgedEstimates,
  handleConfirmDataSubmit,
  calcParams,
  setCalcParams,
  handleRunCalculation,
  loading,
  isArabic
}) {
  const [markupImage, setMarkupImage] = React.useState(null);
  const [showTableEditor, setShowTableEditor] = React.useState(false);

  // Scale Calibration State
  const [calibPixel, setCalibPixel] = React.useState('');
  const [calibReal, setCalibReal] = React.useState('');
  const [calibStatus, setCalibStatus] = React.useState('');
  const [calibLoading, setCalibLoading] = React.useState(false);

  const handleCalibrate = async () => {
    if (!calibPixel || !calibReal || !projectId || !token) return;
    setCalibLoading(true);
    setCalibStatus('');
    try {
      const res = await fetch(`/api/projects/${projectId}/calibrate_scale`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          pixel_distance: parseFloat(calibPixel),
          real_distance: parseFloat(calibReal)
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Calibration failed');
      setCalibStatus(isArabic ? 'تم معايرة المقياس بنجاح. يمكنك الآن إعادة تشغيل استخراج الأبعاد.' : 'Scale calibrated successfully. You can now re-run extraction.');
      
      // Update local inputs with the new scale (just roughly)
      if (confirmedData.longest_length && data.scale_factor) {
         // This is a naive update, real calculation happens on the backend on re-extract
      }
    } catch (err) {
      setCalibStatus(isArabic ? `خطأ: ${err.message}` : `Error: ${err.message}`);
    } finally {
      setCalibLoading(false);
    }
  };

  if (currentStep === 4) {
    return (
      <div className="glass-panel" style={{ padding: '30px', maxWidth: '900px', margin: '0 auto', position: 'relative' }}>
        
        {/* Takeoff Viewer Modal */}
        {markupImage === 'show' && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', zIndex: 9999, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '20px' }}>
            <div style={{ background: '#1e293b', padding: '15px', borderRadius: '8px', width: '100%', maxWidth: '1200px', maxHeight: '95vh', display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <h3 style={{ color: 'white', margin: 0 }}>👁️ Auto-Coloring Takeoff Viewer (OpenCV)</h3>
                <button onClick={() => setMarkupImage(null)} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '8px 16px', borderRadius: '4px', cursor: 'pointer' }}>Close</button>
              </div>
              <div style={{ flex: 1, overflow: 'auto', background: '#000', borderRadius: '4px', display: 'flex', flexDirection: 'column', gap: '20px', padding: '20px' }}>
                {extractionResults && Object.keys(extractionResults).filter(k => extractionResults[k].markup_url).length > 0 ? (
                  Object.values(extractionResults).filter(res => res.markup_url).map((res, idx) => {
                    let imgUrl = res.markup_url;
                    if (imgUrl.includes('\\') || imgUrl.includes('C:')) {
                      const parts = imgUrl.split(/[\\/]/);
                      imgUrl = '/cache/' + parts[parts.length - 1];
                    }
                    return (
                      <div key={idx} style={{ border: '2px solid #333', borderRadius: '8px', padding: '10px', background: '#222' }}>
                        <h4 style={{ color: '#60a5fa', margin: '0 0 10px 0' }}>{res.detected_type || 'Markup'}</h4>
                        <img src={imgUrl} alt="Takeoff Markup" style={{ maxWidth: '100%', objectFit: 'contain' }} />
                      </div>
                    );
                  })
                ) : <div style={{ color: 'white', textAlign: 'center', marginTop: '20px' }}>No OpenCV Markups generated for this project.</div>}
              </div>
            </div>
          </div>
        )}
        <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{isArabic ? '4. مراجعة وتأكيد المقاسات المستخرجة' : '4. Confirm & Verify Extracted Parameters'}</span>
          <button 
            type="button"
            onClick={() => setMarkupImage('show')}
            style={{ fontSize: '0.9rem', background: '#3b82f6', color: 'white', padding: '6px 12px', borderRadius: '4px', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}
          >
            👁️ {isArabic ? 'عرض التلوين التلقائي' : 'View CV Takeoffs'}
          </button>
        </h3>
      <div style={{ padding: '15px 20px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '25px', textAlign: isArabic ? 'right' : 'left' }}>
        <div style={{ color: '#3b82f6', marginTop: '2px' }}><Info size={20} /></div>
        <div>
          <h4 style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', fontSize: '0.95rem' }}>
            {isArabic ? 'ما المطلوب في هذه الخطوة؟' : 'What to do in this step?'}
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, lineHeight: '1.5' }}>
            {isArabic 
              ? 'يرجى تدقيق القيم التي استخرجها الذكاء الاصطناعي وتعديل أي قيم غير دقيقة قبل حساب جداول الحصر النهائي. إذا كانت هناك قيم مفقودة يمكنك إضافتها يدوياً عبر محرر الجداول.'
              : 'Inspect the parameters extracted by AI. Correct any dimensions before running engineering calculations. If there are missing values, you can use the Schedules Editor to add them manually.'}
          </p>
        </div>
      </div>

        {/* Failed Extractions Warnings */}
        {extractionResults && Object.values(extractionResults).filter(res => res._ok === false).length > 0 && (
          <div style={{ backgroundColor: '#fff1f2', borderLeft: '4px solid #e11d48', padding: '15px', marginBottom: '20px', borderRadius: '4px', boxShadow: 'var(--shadow-sm)' }}>
            <h4 style={{ color: '#be123c', fontSize: '1rem', fontWeight: 700, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🚨 {isArabic ? 'تنبيه: انخفاض جودة بعض المخططات' : 'Alert: Low Clarity on Some Pages'}
            </h4>
            <p style={{ margin: '0 0 10px 0', color: '#9f1239', fontSize: '0.9rem' }}>
              {isArabic 
                ? 'لم يتمكن الذكاء الاصطناعي من قراءة الجداول من بعض المستندات. يمكنك الآن استخدام "محرر الجداول الهندسية" بالأسفل لإدخالها يدوياً بسهولة كبديل للبرامج المعقدة.'
                : 'The AI could not clearly read the schedules from some documents. You can now use the "Schedules Editor" below to easily input them manually instead of relying on external software.'}
            </p>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#881337', fontSize: '0.9rem', fontWeight: 500 }}>
              {Object.values(extractionResults).filter(res => res._ok === false).map((res, i) => (
                <li key={i} style={{ marginBottom: '6px' }}>
                  <strong>{res.detected_type || 'Unknown'} (Page {res.page_num || '?'})</strong>: {res._error || 'Unreadable format or missing tables.'}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Issue #19: Scanned PDF warning and Calibration */}
        {confirmedData && !confirmedData._vector_measured && (
          <div style={{ backgroundColor: '#fffbeb', borderLeft: '4px solid #f59e0b', padding: '15px', marginBottom: '20px', borderRadius: '4px', boxShadow: 'var(--shadow-sm)' }}>
            <h4 style={{ color: '#b45309', fontSize: '1rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⚠️ {isArabic ? 'هذا مخطط مصوّر — راجع الأبعاد يدوياً' : 'This is a scanned drawing - review dimensions manually'}
            </h4>
            <p style={{ margin: '8px 0 15px 0', color: '#92400e', fontSize: '0.9rem' }}>
              {isArabic 
                ? 'تعذر قراءة المقاسات الهندسية الدقيقة من المتجهات لأن الملف صورة وليس مخطط أوتوكاد. يرجى التحقق من الطول والعرض أدناه يدوياً.'
                : 'Exact vector measurements could not be read because the file is an image/scanned PDF, not a vector CAD export. Please verify the Length and Width below manually.'}
            </p>
            
            <div style={{ backgroundColor: '#fef3c7', padding: '15px', borderRadius: '6px', border: '1px solid #fde68a' }}>
              <h5 style={{ margin: '0 0 10px 0', color: '#b45309' }}>
                {isArabic ? 'معايرة مقياس الرسم (اختياري)' : 'Scale Calibration (Optional)'}
              </h5>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#92400e', marginBottom: '4px' }}>
                    {isArabic ? 'المسافة بالبكسل (من أداة القياس)' : 'Pixel Distance (from measure tool)'}
                  </label>
                  <input type="number" step="any" value={calibPixel} onChange={e => setCalibPixel(e.target.value)} style={{ padding: '6px', border: '1px solid #fcd34d', borderRadius: '4px', width: '200px' }} />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#92400e', marginBottom: '4px' }}>
                    {isArabic ? 'المسافة الحقيقية (بالمتر)' : 'Real Distance (m)'}
                  </label>
                  <input type="number" step="any" value={calibReal} onChange={e => setCalibReal(e.target.value)} style={{ padding: '6px', border: '1px solid #fcd34d', borderRadius: '4px', width: '200px' }} />
                </div>
                <button 
                  type="button" 
                  onClick={handleCalibrate}
                  disabled={calibLoading || !calibPixel || !calibReal}
                  style={{ background: '#d97706', color: 'white', border: 'none', padding: '7px 16px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                  {calibLoading ? (isArabic ? 'جاري...' : 'Loading...') : (isArabic ? 'تطبيق المعايرة' : 'Apply Calibration')}
                </button>
              </div>
              {calibStatus && (
                <p style={{ margin: '10px 0 0 0', fontSize: '0.85rem', color: calibStatus.includes(isArabic ? 'نجاح' : 'successfully') ? '#15803d' : '#dc2626' }}>
                  {calibStatus}
                </p>
              )}
            </div>
          </div>
        )}

        {sanityWarnings && sanityWarnings.length > 0 && (
          <div style={{ backgroundColor: '#fee2e2', borderLeft: '4px solid #ef4444', padding: '15px', marginBottom: '20px', borderRadius: '4px' }}>
            <h4 style={{ color: '#b91c1c', fontSize: '1rem', fontWeight: 700, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⚠️ {isArabic ? 'تحذيرات هندسية' : 'Engineering Warnings'}
            </h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#991b1b', fontSize: '0.9rem' }}>
              {sanityWarnings.map((warn, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{warn}</li>
              ))}
            </ul>
          </div>
        )}

        <form onSubmit={handleConfirmDataSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Form Grid */}
          <div className="grid-cols-3" style={{ gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'أطول طول للمبنى (متر)' : 'Longest Footprint Length (m)'}
                {renderSourceBadge('longest_length')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.longest_length ?? ''}
                onChange={(e) => updateConfirmedField('longest_length', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'أطول عرض للمبنى (متر)' : 'Longest Footprint Width (m)'}
                {renderSourceBadge('longest_width')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.longest_width ?? ''}
                onChange={(e) => updateConfirmedField('longest_width', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'مساحة الأرض (متر مربع)' : 'Plot Area (m²)'}
                {renderSourceBadge('plot_area')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.plot_area ?? ''}
                onChange={(e) => updateConfirmedField('plot_area', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'مساحة الدور الأرضي (متر مربع)' : 'Ground Floor Built Area (m²)'}
                {renderSourceBadge('gf_area')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.gf_area ?? ''}
                onChange={(e) => updateConfirmedField('gf_area', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'ارتفاع الدور الأرضي (متر)' : 'GF Height (m)'}
                {renderSourceBadge('gf_height')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.gf_height ?? 4.2}
                onChange={(e) => updateConfirmedField('gf_height', parseFloat(e.target.value) || 0)}
              />
            </div>
            {calcParams.num_floors >= 2 && (
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'ارتفاع الدور الأول (متر)' : '1F Height (m)'}
                {renderSourceBadge('f1_height')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.f1_height ?? 3.7}
                onChange={(e) => updateConfirmedField('f1_height', parseFloat(e.target.value) || 0)}
              />
            </div>
            )}
            {calcParams.num_floors >= 3 && (
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'ارتفاع الدور الثاني (متر)' : '2F Height (m)'}
                {renderSourceBadge('f2_height')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.f2_height ?? 3.7}
                onChange={(e) => updateConfirmedField('f2_height', parseFloat(e.target.value) || 0)}
              />
            </div>
            )}
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'المحيط الخارجي للمبنى (متر)' : 'External Perimeter (m)'}
                {renderSourceBadge('ext_perimeter')}
              </label>
                <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.ext_perimeter ?? ''}
                onChange={(e) => updateConfirmedField('ext_perimeter', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'الجدران الداخلية 20 سم (متر)' : 'Internal Walls 20cm Length (m)'}
                {renderSourceBadge('int_walls_20cm_m')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.int_walls_20cm_m ?? ''}
                onChange={(e) => updateConfirmedField('int_walls_20cm_m', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'الجدران الداخلية 10 سم (متر)' : 'Internal Walls 10cm Length (m)'}
                {renderSourceBadge('int_walls_10cm_m')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.int_walls_10cm_m ?? ''}
                onChange={(e) => updateConfirmedField('int_walls_10cm_m', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'محيط السقف (متر)' : 'Roof Perimeter (m)'}
                {renderSourceBadge('roof_perimeter')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.roof_perimeter ?? ''}
                onChange={(e) => updateConfirmedField('roof_perimeter', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'مساحة السقف (متر مربع)' : 'Roof Slab Area (m²)'}
                {renderSourceBadge('roof_slab_area')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.roof_slab_area ?? ''}
                onChange={(e) => updateConfirmedField('roof_slab_area', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'طول السور الخارجي (متر)' : 'Compound Wall Length (m)'}
                {confirmedData.compound_length_is_estimated && <span style={{ color: '#d97706', fontSize: '0.75rem', marginLeft: '5px' }}>{isArabic ? ' (تقديري)' : ' (Estimated)'}</span>}
                {renderSourceBadge('compound_length')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.compound_length ?? ''}
                onChange={(e) => updateConfirmedField('compound_length', parseFloat(e.target.value) || 0)}
                style={confirmedData.compound_length_is_estimated ? { borderColor: '#f59e0b', backgroundColor: '#fffbeb' } : {}}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'إجمالي عدد الأبواب' : 'Total Door Count (Nr)'}
                {confirmedData.openings?.totals?.door_count_is_estimated && <span style={{ color: '#d97706', fontSize: '0.75rem', marginLeft: '5px' }}>{isArabic ? ' (تقديري)' : ' (Estimated)'}</span>}
                {renderSourceBadge('door_count')}
              </label>
              <input
                type="number" step="1" className="form-input" required
                value={confirmedData.openings?.totals?.door_count ?? ''}
                onChange={(e) => updateOpeningField('door_count', parseInt(e.target.value) || 0)}
                style={confirmedData.openings?.totals?.door_count_is_estimated ? { borderColor: '#f59e0b', backgroundColor: '#fffbeb' } : {}}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                {isArabic ? 'إجمالي مساحة النوافذ (متر مربع)' : 'Total Window Area (m²)'}
                {confirmedData.openings?.totals?.window_area_is_estimated && <span style={{ color: '#d97706', fontSize: '0.75rem', marginLeft: '5px' }}>{isArabic ? ' (تقديري)' : ' (Estimated)'}</span>}
                {renderSourceBadge('window_area')}
              </label>
              <input
                type="number" step="0.01" className="form-input" required
                value={confirmedData.openings?.totals?.window_area ?? ''}
                onChange={(e) => updateOpeningField('window_area', parseFloat(e.target.value) || 0)}
                style={confirmedData.openings?.totals?.window_area_is_estimated ? { borderColor: '#f59e0b', backgroundColor: '#fffbeb' } : {}}
              />
            </div>
          </div>

          {/* Table Editor Button & Modal */}
          <div style={{ marginTop: '15px' }}>
            <button
              type="button"
              onClick={() => setShowTableEditor(true)}
              style={{ background: '#3b82f6', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '6px', fontSize: '0.95rem', cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', boxShadow: '0 4px 6px rgba(59, 130, 246, 0.3)' }}
            >
              📝 {isArabic ? 'محرر الجداول الهندسية (بديل الإدخال اليدوي)' : 'Engineering Schedules Editor (Manual Input)'}
            </button>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
              {isArabic ? 'استخدم هذا المحرر لإدخال جداول القواعد والأعمدة إذا فشل الذكاء الاصطناعي في التعرف عليها بدلاً من الاعتماد على الفرضيات.' : 'Use this editor to manually input footings and columns if AI extraction failed, instead of relying on assumptions.'}
            </p>
          </div>

          {showTableEditor && (
            <ScheduleTableEditorModal
              isArabic={isArabic}
              schedules={confirmedData.schedules}
              onClose={() => setShowTableEditor(false)}
              onSave={(newSchedules) => {
                updateConfirmedField('schedules', newSchedules);
                setShowTableEditor(false);
              }}
            />
          )}

          {/* Engineering Assumptions Section */}
          <div style={{ marginTop: '20px', borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⚙️ {isArabic ? 'الافتراضات الهندسية (أبعاد ونسب تقديرية قابلة للتعديل)' : 'Engineering Assumptions & Estimators (Editable)'}
            </h4>
            <div className="grid-cols-2" style={{ gap: '15px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'عمق الحفر الافتراضي (متر)' : 'Default Excavation Depth (m)'}
                  {renderSourceBadge('excavation_depth')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.excavation_depth ?? 1.25}
                  onChange={(e) => updateConfirmedField('excavation_depth', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'سماكة خرسانة الأرضية (متر)' : 'Slab on Grade Thickness (m)'}
                  {renderSourceBadge('sog_thickness')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.sog_thickness ?? 0.10}
                  onChange={(e) => updateConfirmedField('sog_thickness', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'ارتفاع الفيلا الكلي (متر)' : 'Total Villa Height (m)'}
                  {renderSourceBadge('total_villa_height')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.total_villa_height ?? ''}
                  onChange={(e) => updateConfirmedField('total_villa_height', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'ارتفاع رقاب الأعمدة (متر)' : 'Neck Column Height (m)'}
                  {renderSourceBadge('neck_column_height')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.neck_column_height ?? 1.0}
                  onChange={(e) => updateConfirmedField('neck_column_height', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'ارتفاع الطابوق المصمت تحت الميدة (متر)' : 'Solid Block Work Height (m)'}
                  {renderSourceBadge('solid_block_height')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.solid_block_height ?? 1.0}
                  onChange={(e) => updateConfirmedField('solid_block_height', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'حجم خرسانة الدرج لكل دور (م³)' : 'Staircase Concrete Volume per Floor (m³)'}
                  {renderSourceBadge('staircase_volume_per_level')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.staircase_volume_per_level ?? 5.2}
                  onChange={(e) => updateConfirmedField('staircase_volume_per_level', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'متوسط طول العمود الافتراضي (متر)' : 'Default Column Length (m)'}
                  {renderSourceBadge('default_col_length')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.default_col_length ?? 0.60}
                  onChange={(e) => updateConfirmedField('default_col_length', parseFloat(e.target.value) || 0)}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '0.85rem', fontWeight: 600 }}>
                  {isArabic ? 'متوسط عرض العمود الافتراضي (متر)' : 'Default Column Width (m)'}
                  {renderSourceBadge('default_col_width')}
                </label>
                <input
                  type="number" step="0.01" className="form-input" required
                  value={confirmedData.default_col_width ?? 0.20}
                  onChange={(e) => updateConfirmedField('default_col_width', parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
          </div>

          {hasEstimates ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
              <div style={{
                padding: '12px',
                backgroundColor: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '6px',
                color: '#b45309',
                fontSize: '0.85rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span>⚠️</span>
                <span>
                  {isArabic 
                    ? 'تم تقدير بعض القيم المميزة باللون الأصفر تلقائياً بناءً على قواعد هندسية تقريبية لعدم توفرها بالملفات. يرجى مراجعتها وتأكيدها.' 
                    : 'Some values highlighted in yellow have been estimated using standard QS heuristic rules because they were not found in the uploaded documents. Please review and confirm.'}
                </span>
              </div>
              
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '12px',
                backgroundColor: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '6px'
              }}>
                <input
                  type="checkbox"
                  id="ack-estimates"
                  checked={acknowledgedEstimates}
                  onChange={(e) => setAcknowledgedEstimates(e.target.checked)}
                  style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                />
                <label htmlFor="ack-estimates" style={{ fontSize: '0.9rem', color: '#1e40af', cursor: 'pointer', fontWeight: 600 }}>
                  {isArabic 
                    ? 'أقر بصحة هذه التقديرات أو قمت بتعديلها يدوياً للمطابقة.' 
                    : 'I verify these estimated values are correct or I have manually adjusted them.'}
                </label>
              </div>
            </div>
          ) : null}

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: '15px', padding: '12px' }} 
            disabled={loading || (hasEstimates && !acknowledgedEstimates)}
          >
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <div className="spin-anim" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
                <span>{isArabic ? 'جاري الحفظ والانتقال...' : 'Saving & Proceeding...'}</span>
              </div>
            ) : (
              isArabic ? 'تأكيد البيانات والانتقال لحساب الكميات' : 'Confirm Data & Open Calculations Panel'
            )}
          </button>
        </form>
      </div>
    );
  }

  if (currentStep === 5) {
    return (
      <div className="glass-panel" style={{ padding: '30px', maxWidth: '700px', margin: '0 auto' }}>
        <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>
          {isArabic ? '5. إعدادات حساب كميات الهيكل الإنشائي والتشطيبات' : '5. Structural & Finishes Calculation Settings'}
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '25px' }}>
          {isArabic 
            ? 'اضبط إعدادات الارتفاع وعدد الأدوار لتشغيل محرك الحسابات الهندسية.'
            : 'Adjust the height values, floor layers, and excavation depths to compute the takeoff sheet.'}
        </p>

        <form onSubmit={handleRunCalculation} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="grid-cols-2" style={{ gap: '20px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'عدد الأدوار الإجمالي' : 'Number of Villa Floors'}
              </label>
              <select 
                className="form-input"
                value={calcParams.num_floors}
                onChange={(e) => setCalcParams({ ...calcParams, num_floors: parseInt(e.target.value) || 2 })}
              >
                <option value={1}>{isArabic ? 'دور واحد (أرضي فقط)' : '1 Floor (Ground Only)'}</option>
                <option value={2}>{isArabic ? 'دورين (أرضي + أول)' : '2 Floors (Ground + 1st)'}</option>
                <option value={3}>{isArabic ? '3 أدوار (أرضي + أول + ثاني)' : '3 Floors (Ground + 1st + 2nd)'}</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'عمق الحفر الافتراضي (متر)' : 'Default Soil Excavation Depth (m)'}
              </label>
              <input
                type="number" step="0.05" className="form-input" required
                value={calcParams.excavation_depth}
                onChange={(e) => setCalcParams({ ...calcParams, excavation_depth: parseFloat(e.target.value) || 1.25 })}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'ارتفاع الدور الأرضي (متر)' : 'Ground Floor Height (m)'}
              </label>
              <input
                type="number" step="0.1" className="form-input" required
                value={calcParams.gf_height}
                onChange={(e) => setCalcParams({ ...calcParams, gf_height: parseFloat(e.target.value) || 4.0 })}
              />
            </div>

            {calcParams.num_floors >= 2 && (
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                  {isArabic ? 'ارتفاع الدور الأول (متر)' : '1st Floor Height (m)'}
                </label>
                <input
                  type="number" step="0.1" className="form-input" required
                  value={calcParams.f1_height}
                  onChange={(e) => setCalcParams({ ...calcParams, f1_height: parseFloat(e.target.value) || 4.0 })}
                />
              </div>
            )}

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'درجة الخرسانة الهيكلية' : 'Structural Concrete Grade'}
              </label>
              <select 
                className="form-input"
                value={calcParams.concrete_grade || 'C30/37'}
                onChange={(e) => setCalcParams({ ...calcParams, concrete_grade: e.target.value })}
              >
                <option value="C20/25">C20/25</option>
                <option value="C30/37">C30/37</option>
                <option value="C35/45">C35/45</option>
                <option value="C40/50">C40/50</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'سماكة البلوك المصمت (تحت الأرض)' : 'Substructure Solid Block'}
              </label>
              <select 
                className="form-input"
                value={calcParams.solid_block_thickness || '200mm'}
                onChange={(e) => setCalcParams({ ...calcParams, solid_block_thickness: e.target.value })}
              >
                <option value="150mm">150 mm (6")</option>
                <option value="200mm">200 mm (8")</option>
                <option value="250mm">250 mm (10")</option>
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'سماكة البلوك المعزول (خارجي)' : 'External Thermal Block'}
              </label>
              <select 
                className="form-input"
                value={calcParams.thermal_block_thickness || '200mm'}
                onChange={(e) => setCalcParams({ ...calcParams, thermal_block_thickness: e.target.value })}
              >
                <option value="150mm">150 mm (6")</option>
                <option value="200mm">200 mm (8")</option>
                <option value="250mm">250 mm (10")</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
                {isArabic ? 'سماكة البلوك المفرغ (داخلي)' : 'Internal Hollow Block'}
              </label>
              <select 
                className="form-input"
                value={calcParams.hollow_block_thickness || '100mm'}
                onChange={(e) => setCalcParams({ ...calcParams, hollow_block_thickness: e.target.value })}
              >
                <option value="100mm">100 mm (4")</option>
                <option value="150mm">150 mm (6")</option>
                <option value="200mm">200 mm (8")</option>
              </select>
            </div>
          </div>

          <div style={{ marginTop: '10px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontWeight: 600 }}>
              <input
                type="checkbox"
                checked={calcParams.include_road_base}
                onChange={(e) => setCalcParams({ ...calcParams, include_road_base: e.target.checked })}
                style={{ width: '18px', height: '18px' }}
              />
              {isArabic ? 'تضمين طبقة تحت الأساسات (Road Base)' : 'Include Sub-Structure Road Base Layer'}
            </label>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px', padding: '12px' }} disabled={loading}>
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <div className="spin-anim" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
                <span>{isArabic ? 'جاري حساب الكميات بالمعادلات الهندسية...' : 'Calculating concrete volumes...'}</span>
              </div>
            ) : (
              isArabic ? 'تشغيل حساب كميات الهيكل والتشطيبات' : 'Calculate & Generate Takeoff Bill'
            )}
          </button>
        </form>
      </div>
    );
  }

  return null;
}
