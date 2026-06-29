import React, { useState } from 'react';

const LABEL_KEY = {
  projectName: ['Project Name', 'اسم المشروع'],
  clientName: ['Client Name', 'اسم العميل'],
  plotNumber: ['Plot Number', 'رقم القطعة'],
  location: ['Location', 'الموقع'],
  consultantName: ['Consultant Name', 'اسم الاستشاري'],
  contractorName: ['Contractor Name', 'اسم المقاول'],
  villaType: ['Villa Type', 'نوع الفيلا'],
  buaPerFloor: ['BUA per Floor', 'مساحة البناء للدور'],
  basementArea: ['Basement Area', 'مساحة القبو'],
  mezzanineArea: ['Mezzanine Area', 'مساحة الميزانين'],
  hasPool: ['Pool', 'مسبح'],
  hasRoofGarden: ['Roof Garden', 'حديقة سطح'],
  hasExternalLandscape: ['External Landscape', 'أعمال اللاندسكيب الخارجية'],
  hasBoundaryWall: ['Boundary Wall', 'السور الخارجي'],
  hasDemolition: ['Demolition', 'أعمال الهدم'],
  complexityFactor: ['Complexity', 'درجة التعقيد'],
  contractValueAed: ['Contract Value', 'قيمة العقد'],
  advancePaymentPct: ['Advance %', 'نسبة الدفعة المقدمة'],
  retentionPct: ['Retention %', 'نسبة الاستقطاع'],
  vatPct: ['VAT %', 'نسبة ضريبة القيمة المضافة'],
  certificationPeriodDays: ['Cert Period (Days)', 'فترة الاعتماد (بالأيام)'],
  paymentPeriodDays: ['Payment Period (Days)', 'فترة الدفع (بالأيام)'],
  defectsLiabilityMonths: ['DLP (Months)', 'فترة ضمان العيوب (بالأشهر)'],
};

export default function SpecPrefill({ cfg, setCfg, isArabic, token }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [picked, setPicked] = useState({});

  function fmtVal(key, v) {
    if (typeof v === 'boolean') return v ? t('Yes', 'نعم') : t('No', 'لا');
    if (key === 'complexityFactor') return `×${v}`;
    if (v === undefined || v === null) return '—';
    return String(v);
  }

  async function onFile(file) {
    if (!file) return;
    setBusy(true);
    setResult(null);
    setPicked({});
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/modules/spec/prefill', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const r = await res.json();
      setResult(r);
      if (res.ok && r._success && r.suggestions) {
        const init = {};
        for (const k of Object.keys(r.suggestions)) {
          init[k] = true;
        }
        setPicked(init);
      }
    } catch (e) {
      setResult({ _success: false, _error: e.message || String(e) });
    } finally {
      setBusy(false);
    }
  }

  function applySelected() {
    if (!result?.suggestions) return;
    const patch = {};
    for (const [k, v] of Object.entries(result.suggestions)) {
      if (picked[k]) patch[k] = v;
    }
    if (Object.keys(patch).length) {
      setCfg(patch);
    }
    setResult(null);
    setPicked({});
  }

  const entries = result?.suggestions ? Object.entries(result.suggestions) : [];
  const selectedCount = Object.values(picked).filter(Boolean).length;

  return (
    <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 10, padding: '12px 16px', marginBottom: 16 }}>
      <button 
        className="btn" 
        onClick={() => setOpen((o) => !o)} 
        style={{ 
          background: 'none', 
          border: 'none', 
          color: 'var(--primary)', 
          fontWeight: 600, 
          cursor: 'pointer',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 6
        }}
      >
        <span>🪄</span>
        <span>{open ? t('▾ Hide AI Specification Pre-fill', '▾ إخفاء التعبئة التلقائية الذكية') : t('▸ Show AI Specification Pre-fill', '▸ إظهار التعبئة التلقائية الذكية')}</span>
      </button>

      {open && (
        <div style={{ marginTop: 10 }}>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 0, marginBottom: 12 }}>
            {t('Upload the villa project specification document (PDF or Text). The AI will read it to suggest values for project & financial parameters.',
               'قم برفع وثيقة مواصفات المشروع (PDF أو نص). سيقوم الذكاء الاصطناعي بقراءتها واقتراح الحقول المناسبة.')}
          </p>
          <label className="btn btn-secondary" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <span>📄</span>
            <span>{t('Upload Specification Document', 'رفع ملف المواصفات')}</span>
            <input 
              type="file" 
              accept="application/pdf,text/plain,.txt,.md" 
              style={{ display: 'none' }}
              disabled={busy} 
              onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} 
            />
          </label>
          {busy && <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginInlineStart: 12 }}>{t('Reading and analyzing spec sheet...', 'جاري قراءة وتحليل وثيقة المواصفات...')}</span>}

          {result && !result._success && (
            <p style={{ color: 'var(--error)', background: 'rgba(239, 68, 68, 0.1)', padding: 10, borderRadius: 8, marginTop: 10, fontSize: '0.85rem' }}>
              ⚠️ {result._error}
            </p>
          )}

          {result?._success && entries.length === 0 && (
            <p style={{ color: 'var(--warning)', background: 'rgba(245, 158, 11, 0.1)', padding: 10, borderRadius: 8, marginTop: 10, fontSize: '0.85rem' }}>
              {t('No suggestions could be extracted from this document with high confidence.', 'لم يتم استخراج أي مقترحات من هذا الملف بثقة كافية.')}
            </p>
          )}

          {result?._success && entries.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{t('Review AI Suggestions', 'مراجعة مقترحات الذكاء الاصطناعي')}</strong>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{t('Confidence', 'مستوى الثقة')}: {result.confidence}</span>
              </div>
              <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)', textAlign: isArabic ? 'right' : 'left' }}>
                      <th style={{ padding: '6px 8px' }}></th>
                      <th style={{ padding: '6px 8px' }}>{t('Parameter', 'الحقل')}</th>
                      <th style={{ padding: '6px 8px' }}>{t('Current', 'الحالي')}</th>
                      <th style={{ padding: '6px 8px' }}>{t('AI Suggested', 'المقترح')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map(([k, v]) => {
                      const cur = cfg[k];
                      const lbl = LABEL_KEY[k] ? t(LABEL_KEY[k][0], LABEL_KEY[k][1]) : k;
                      return (
                        <tr key={k} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '6px 8px', textAlign: 'center', width: 34 }}>
                            <input 
                              type="checkbox" 
                              checked={!!picked[k]}
                              onChange={(e) => setPicked((p) => ({ ...p, [k]: e.target.checked }))} 
                            />
                          </td>
                          <td style={{ padding: '6px 8px', fontWeight: 600 }}>{lbl}</td>
                          <td style={{ padding: '6px 8px', color: 'var(--text-muted)' }}>{fmtVal(k, cur)}</td>
                          <td style={{ padding: '6px 8px', color: 'var(--primary)', fontWeight: 600 }}>→ {fmtVal(k, v)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {result.notes && (
                <p style={{ fontStyle: 'italic', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 8, marginBottom: 10 }}>
                  * {result.notes}
                </p>
              )}
              <button 
                className="btn btn-primary" 
                style={{ marginTop: 8 }} 
                disabled={selectedCount === 0} 
                onClick={applySelected}
              >
                ✓ {t(`Apply Selected (${selectedCount})`, `تطبيق الحقول المحددة (${selectedCount})`)}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
