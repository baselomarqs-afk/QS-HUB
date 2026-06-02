import React from 'react';
import { AlertTriangle, FileSpreadsheet, FileText } from 'lucide-react';

export default function BoqStep({
  currentStep,
  boqMeta,
  calculateGrandTotal,
  boqItems,
  handlePriceChange,
  handleQtyChange,
  handleSaveReview,
  setCurrentStep,
  downloadExcel,
  downloadPDF,
  onNavigate,
  isArabic
}) {
  if (currentStep === 6) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Meta Alerts & Warnings */}
        {(boqMeta.needs_input?.length > 0 || boqMeta.estimates?.length > 0) && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {boqMeta.needs_input?.length > 0 && (
              <div style={{ padding: '15px 20px', backgroundColor: 'rgba(239, 68, 68, 0.05)', borderLeft: isArabic ? 'none' : '4px solid var(--error)', borderRight: isArabic ? '4px solid var(--error)' : 'none', borderRadius: '8px' }}>
                <h5 style={{ fontWeight: 700, color: 'var(--error)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={16} />
                  {isArabic ? 'قيم مفقودة تتطلب مراجعة بشرية:' : 'Missing drawing values (needs verification):'}
                </h5>
                <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: '20px', paddingRight: '20px' }}>
                  {boqMeta.needs_input.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            )}
            {boqMeta.estimates?.length > 0 && (
              <div style={{ padding: '15px 20px', backgroundColor: 'rgba(245, 158, 11, 0.05)', borderLeft: isArabic ? 'none' : '4px solid var(--warning)', borderRight: isArabic ? '4px solid var(--warning)' : 'none', borderRadius: '8px' }}>
                <h5 style={{ fontWeight: 700, color: 'var(--warning)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertTriangle size={16} />
                  {isArabic ? 'تنبيه: قيم تم تقديرها تلقائياً:' : 'Automatically estimated averages:'}
                </h5>
                <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: '20px', paddingRight: '20px' }}>
                  {boqMeta.estimates.map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* BOQ Table Sheet */}
        <div className="glass-panel" style={{ padding: '25px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>
              {isArabic ? '6. مراجعة وتعديل الكميات (كل القيم قابلة للتعديل اليدوي)' : '6. Review & Edit Quantities (every value is editable)'}
            </h3>
          </div>

          <div className="premium-table-container" style={{ maxHeight: '550px', overflowY: 'auto' }}>
            <table className="premium-table">
              <thead>
                <tr>
                  <th style={{ width: '6%' }}>#</th>
                  <th style={{ width: '30%' }}>{isArabic ? 'البيان بالإنجليزية' : 'Description (English)'}</th>
                  <th style={{ width: '20%' }}>{isArabic ? 'البيان بالعربية' : 'البيان (العربية)'}</th>
                  <th style={{ width: '8%' }}>{isArabic ? 'الوحدة' : 'Unit'}</th>
                  <th style={{ width: '12%' }}>{isArabic ? 'الكمية (للتعديل)' : 'Qty (edit)'}</th>
                  <th style={{ width: '12%' }}>{isArabic ? 'السعر (للتعديل)' : 'Price (edit)'}</th>
                  <th style={{ width: '12%' }}>{isArabic ? 'الإجمالي' : 'Total'}</th>
                </tr>
              </thead>
              <tbody>
                {boqItems.map((item, idx) => {
                  if (item._is_header) {
                    return (
                      <tr key={idx} className="header-row">
                        <td colSpan={7}>{item["Description (English)"]}</td>
                      </tr>
                    );
                  }
                  return (
                    <tr key={idx}>
                      <td>{item["#"]}</td>
                      <td>{item["Description (English)"]}</td>
                      <td style={{ textAlign: 'right' }}>{item["البيان"]}</td>
                      <td>{item["Unit"]}</td>
                      <td style={item.has_error ? { backgroundColor: '#fee2e2' } : {}}>
                        <input
                          type="number"
                          step="0.01"
                          className="form-input"
                          value={item.has_error ? '' : (item["Quantity"] ?? '')}
                          onChange={(e) => handleQtyChange(idx, e.target.value)}
                          placeholder={item.has_error ? '⚠️ Err' : '0.00'}
                          style={{ width: '100%', padding: '5px', fontSize: '0.9rem', fontWeight: 600,
                                   color: item.has_error ? '#ef4444' : 'var(--text-primary)' }}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="form-input"
                          value={item["Unit Price"] ?? ''}
                          onChange={(e) => handlePriceChange(idx, e.target.value)}
                          placeholder="0.00"
                          style={{ width: '100%', padding: '5px', fontSize: '0.9rem', fontWeight: 600 }}
                        />
                      </td>
                      <td style={{ fontWeight: 'bold', color: 'var(--primary)' }}>
                        {((parseFloat(item["Quantity"]) || 0) * (parseFloat(item["Unit Price"]) || 0)).toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '25px', display: 'flex', justifyContent: 'flex-end', gap: '15px' }}>
            <button className="btn btn-secondary" onClick={() => setCurrentStep(5)}>
              {isArabic ? 'السابق' : 'Back'}
            </button>
            <button className="btn btn-success" onClick={handleSaveReview}>
              {isArabic ? 'حفظ وتأكيد مسودة جدول الكميات' : 'Confirm Quantities & Open Exports'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (currentStep === 8) {
    return (
      <div className="glass-panel" style={{ padding: '40px', maxWidth: '650px', margin: '0 auto', textAlign: 'center' }}>
        <div style={{ fontSize: '3.5rem', color: 'var(--success)', marginBottom: '15px' }}>✓</div>
        <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px' }}>
          {isArabic ? '8. تم حصر كميات المشروع بنجاح!' : '8. Project Quantity Takeoff Completed Successfully!'}
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: '35px' }}>
          {isArabic 
            ? 'يمكنك الآن تحميل جداول الكميات والتكلفة التفصيلية بصيغة Excel الاحترافية أو تقرير PDF المهندس.'
            : 'You can now export and download the final itemized BOQ sheets in styled Excel formats or PDF reports.'}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '25px' }}>
          <button className="btn btn-success" onClick={downloadExcel} style={{ padding: '15px 25px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <FileSpreadsheet size={32} />
            <span style={{ fontSize: '1rem', fontWeight: 700 }}>{isArabic ? 'تحميل جدول Excel' : 'Download Excel Sheet'}</span>
          </button>

          <button className="btn btn-primary" onClick={downloadPDF} style={{ padding: '15px 25px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <FileText size={32} />
            <span style={{ fontSize: '1rem', fontWeight: 700 }}>{isArabic ? 'تحميل تقرير PDF' : 'Download PDF Report'}</span>
          </button>
        </div>

        <button className="btn btn-secondary" onClick={() => onNavigate('dashboard')} style={{ width: '100%' }}>
          {isArabic ? 'العودة للوحة التحكم الرئيسية' : 'Return to Dashboard'}
        </button>
      </div>
    );
  }

  return null;
}
