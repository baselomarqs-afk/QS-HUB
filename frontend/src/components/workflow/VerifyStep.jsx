import React from 'react';

export default function VerifyStep({
  currentStep,
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
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '25px' }}>
          {isArabic 
            ? 'يرجى تدقيق القيم التي استخرجها الذكاء الاصطناعي وتعديل أي قيم غير دقيقة قبل حساب جداول الحصر.'
            : 'Inspect the parameters extracted by AI. Correct any dimensions before running engineering calculations.'}
        </p>

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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px' }}>
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

          {/* Engineering Assumptions Section */}
          <div style={{ marginTop: '20px', borderTop: '1px solid #e5e7eb', paddingTop: '20px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⚙️ {isArabic ? 'الافتراضات الهندسية (أبعاد ونسب تقديرية قابلة للتعديل)' : 'Engineering Assumptions & Estimators (Editable)'}
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
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
