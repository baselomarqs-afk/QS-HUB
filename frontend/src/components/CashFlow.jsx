// نافذة التدفق النقدي — Cash Flow window (bilingual). Parametric S-Curve linked to the 
// Work Programme's CPM schedule. Enforces UAE advance, retention, VAT and payment delays.
import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Loader2, Download, Save, Rocket } from 'lucide-react';
import FeatureGate from './FeatureGate';
import ModuleHistory from './ModuleHistory';
import SpecPrefill from './SpecPrefill';
import DrawingUpload from './DrawingUpload';
import { DEFAULT_CONFIG, suggestedHandover, num } from '../engine/projectConfig';
import { VILLA_TYPE_DEFINITIONS } from '../engine/villaTypes';
import { buildActivityList } from '../engine/durationEngine';
import { runScheduler } from '../engine/scheduler';
import { computeCashFlow, fmtAed } from '../engine/cashflow';
import FeedbackModal from './common/FeedbackModal';

function CashFlowTool({ token, isArabic, initialProjectName, onClearInitialName, onStartProject }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [cfg, setCfg] = useState({ ...DEFAULT_CONFIG });
  const [processed, setProcessed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [savedId, setSavedId] = useState(null); // reused so re-saves don't consume another credit
  const justLoaded = useRef(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [loadingPct, setLoadingPct] = useState(0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [autoSavePending, setAutoSavePending] = useState(false);

  const process = () => {
    if (canProcess) {
      setIsSimulating(true);
      setLoadingPct(0);
      let pct = 0;
      const interval = setInterval(() => {
        pct += 1;
        setLoadingPct(pct);
        if (pct >= 100) {
          clearInterval(interval);
          setIsSimulating(false);
          setProcessed(true);
          if (!savedId) {
            const acts = buildActivityList(cfg);
            const out = runScheduler(cfg, acts);
            const resObj = computeCashFlow(cfg, out.monthly);
            save(resObj);
          }
          if (onStartProject) onStartProject();
        }
      }, 600);
    }
  };

  const patch = (p) => setCfg((c) => ({ ...c, ...p }));

  const missing = [];
  if (!cfg.projectName.trim()) missing.push(t('Project Name', 'اسم المشروع'));
  if (!cfg.villaType) missing.push(t('Villa Type', 'نوع الفيلا'));
  if (!(cfg.buaPerFloor > 0)) missing.push(t('BUA per Floor', 'مساحة البناء للدور'));
  if (!(cfg.contractValueAed > 0)) missing.push(t('Contract Value', 'قيمة العقد'));
  const canProcess = missing.length === 0;

  // Geometry changes alter the schedule → require re-processing.
  const geomSig = `${cfg.villaType}|${cfg.buaPerFloor}|${cfg.complexityFactor}|${cfg.hasPool}|${cfg.hasDemolition}|${cfg.startISO}|${cfg.handoverISO}`;
  useEffect(() => {
    setProcessed(false);
    setSavedMsg('');
    if (justLoaded.current) justLoaded.current = false;
    else setSavedId(null);
  }, [geomSig]);

  useEffect(() => {
    if (initialProjectName) {
      patch({ projectName: initialProjectName });
      onClearInitialName();
    }
  }, [initialProjectName]);

  const result = useMemo(() => {
    if (!canProcess) return null;
    const acts = buildActivityList(cfg);
    const out = runScheduler(cfg, acts);
    return computeCashFlow(cfg, out.monthly);
  }, [cfg, canProcess]);


  const show = processed && canProcess && result;

  const exportExcel = async () => {
    const mod = await import('../engine/cashflowExcel');
    mod.exportCashFlowToExcel(cfg, result, cfg.projectName || 'Project');
  };

  const save = async (resultObj = result) => {
    if (!resultObj) return;
    setSaving(true);
    setSavedMsg('');
    try {
      const res = await fetch('/api/modules/cashflow/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          project_id: savedId,
          name: cfg.projectName,
          config: cfg,
          summary: resultObj.summary,
        }),
      });
      const data = await res.json();
      if (res.ok) { setSavedId(data.project_id); setSavedMsg(t('Saved to history ✓', 'حُفظ في السجل ✓')); }
      else setSavedMsg(data.detail || t('Save failed', 'فشل الحفظ'));
    } catch {
      setSavedMsg(t('Save failed', 'فشل الحفظ'));
    } finally {
      setSaving(false);
    }
  };

  const onStart = (startISO) => {
    const linked = !cfg.handoverISO || cfg.handoverISO === suggestedHandover(cfg.startISO);
    patch(linked ? { startISO, handoverISO: suggestedHandover(cfg.startISO) } : { startISO });
  };

  const lbl = { display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 };
  const inp = { width: '100%', padding: '9px 11px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' };
  const card = { background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 14, padding: 22, marginBottom: 20 };
  
  const numField = (en, ar, key, step = '1', required = false) => (
    <div>
      <label style={lbl}>{t(en, ar)}{required ? ' *' : ''}</label>
      <input style={inp} type="number" step={step} value={cfg[key] || ''} placeholder="0" onChange={(e) => patch({ [key]: num(e.target.value) })} />
    </div>
  );

  return (
    <div style={{ padding: '28px clamp(16px, 4vw, 40px)', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>💰 {t('Cash-Flow Forecast', 'توقع التدفق النقدي')}</h1>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        {t('Flow: (1) Enter project and financial parameters, (2) attach drawings, (3) press Process to calculate the cash flow mapped to construction activities.',
           'خطوات العمل: (١) أدخل البيانات الهندسية والمالية للمشروع، (٢) أرفق المخططات، (٣) اضغط معالجة لإنشاء التدفق المالي المرتبط بجدول الأنشطة التنفيذية.')}
      </p>

      <ModuleHistory feature="cashflow" token={token} isArabic={isArabic} refreshKey={savedId}
        onLoad={({ id, config }) => {
          justLoaded.current = true;
          setCfg({ ...DEFAULT_CONFIG, ...config });
          setSavedId(id);
          if (onStartProject) onStartProject();
        }} />

      <div style={card}>
        <h3 style={{ marginTop: 0, color: 'var(--text-primary)' }}>① {t('Project Entries', 'بيانات المشروع')}</h3>
        <SpecPrefill cfg={cfg} setCfg={patch} isArabic={isArabic} token={token} />

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 }}>
          <div>
            <label style={lbl}>{t('Project Name', 'اسم المشروع')} *</label>
            <input style={inp} value={cfg.projectName} placeholder={t('Project Name', 'اسم المشروع')} onChange={(e) => patch({ projectName: e.target.value })} />
          </div>
          <div>
            <label style={lbl}>{t('Villa Type', 'نوع الفيلا')} *</label>
            <select style={inp} value={cfg.villaType} onChange={(e) => patch({ villaType: e.target.value })}>
              <option value="">— {t('select', 'اختر')} —</option>
              {Object.entries(VILLA_TYPE_DEFINITIONS).map(([k, v]) => (
                <option key={k} value={k}>{k} — {isArabic ? v.labelAr : v.label}</option>
              ))}
            </select>
          </div>
          {numField('BUA per Floor (m²)', 'مساحة البناء للدور (م²)', 'buaPerFloor', '10', true)}
          <div>
            <label style={lbl}>{t('Start Date', 'تاريخ البدء')} *</label>
            <input style={inp} type="date" value={cfg.startISO} onChange={(e) => onStart(e.target.value)} />
          </div>
          <div>
            <label style={lbl}>{t('Handover Date', 'تاريخ التسليم')}</label>
            <input style={inp} type="date" value={cfg.handoverISO} min={cfg.startISO || undefined} onChange={(e) => patch({ handoverISO: e.target.value })} />
          </div>
        </div>

        <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>② {t('Financial Entries', 'البيانات المالية')}</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 }}>
          {numField('Contract Value (AED)', 'قيمة العقد (درهم)', 'contractValueAed', '10000', true)}
          {numField('Advance Payment %', 'نسبة الدفعة المقدمة %', 'advancePaymentPct', '1')}
          {numField('Retention %', 'نسبة الاستقطاع %', 'retentionPct', '0.5')}
          {numField('Retention Release @ Completion %', 'إفراج الاستقطاع عند الإنجاز %', 'retentionReleaseAtCompletionPct', '5')}
          {numField('VAT %', 'ضريبة القيمة المضافة %', 'vatPct', '1')}
          {numField('Certification Period (Days)', 'فترة الاعتماد (بالأيام)', 'certificationPeriodDays', '1')}
          {numField('Payment Period (Days)', 'فترة الدفع (بالأيام)', 'paymentPeriodDays', '1')}
          {numField('DLP (Months)', 'فترة ضمان العيوب (أشهر)', 'defectsLiabilityMonths', '1')}
          {numField('Cost Ratio (cost/bill)', 'نسبة التكلفة للفاتورة', 'contractorCostRatio', '0.01')}
        </div>

        <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>③ {t('Attach Drawings', 'إرفاق المخططات')}</h3>
        <DrawingUpload drawings={cfg.drawings || []} setDrawings={(drawingsList) => patch({ drawings: drawingsList })} isArabic={isArabic} />

        <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>④ {t('Run Process', 'تشغيل المعالجة')}</h3>
        {missing.length > 0 && (
          <p style={{ color: 'var(--warning, #d97706)', marginTop: 14 }}>⚠️ {t('Please fill required fields', 'يرجى تعبئة الحقول المطلوبة')}: {missing.join('، ')}</p>
        )}
        {isSimulating ? (
          <div style={{ marginTop: 20, padding: 20, background: 'var(--bg-primary)', borderRadius: 8, border: '1px solid var(--border-color)', textAlign: 'center' }}>
            <h4 style={{ margin: 0, marginBottom: 10, color: 'var(--text-primary)' }}>{t('Processing Financial Data...', 'جاري معالجة البيانات المالية...')}</h4>
            <div style={{ width: '100%', height: 10, background: 'rgba(0,0,0,0.1)', borderRadius: 5, overflow: 'hidden' }}>
              <div style={{ width: `${loadingPct}%`, height: '100%', background: 'var(--primary)', transition: 'width 0.3s ease' }} />
            </div>
            <p style={{ marginTop: 10, marginBottom: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {loadingPct}% {t('Complete', 'مكتمل')}
            </p>
          </div>
        ) : !processed && (
          <button className="btn btn-primary" disabled={!canProcess} onClick={process} style={{ marginTop: 16, padding: '12px 20px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Rocket size={16} /> {t('Process — Build Cash Flow', 'معالجة — إنشاء التدفق النقدي')}
          </button>
        )}
        <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 10 }}>
          {t('* Calculation builds the schedule first, then generates monthly bills according to the Work Programme construction sequence.',
             '* تقوم المعالجة ببناء الجدول التنفيذي أولاً، ثم استنتاج فواتير الدفعات الشهرية وفق التسلسل الزمني لبرنامج الأعمال.')}
        </p>
      </div>

      {show && result && (
        <>
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>📈 {cfg.projectName} — {cfg.villaType}</h3>
              <div style={{ display: 'flex', gap: 8 }}>
                {!savedId && (
                  <button className="btn btn-secondary" onClick={() => save()} disabled={saving}>
                    {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />} {t('Save to History', 'حفظ في السجل')}
                  </button>
                )}
                <button className="btn btn-primary" onClick={exportExcel}>
                  <Download size={15} /> {t('Export Excel', 'تصدير إكسل')}
                </button>
              </div>
            </div>
            {savedMsg && <p style={{ color: 'var(--success)', fontSize: '0.85rem', margin: '8px 0 0' }}>{savedMsg}</p>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginTop: 16 }}>
              {[
                [fmtAed(result.summary.contractValue), t('Contract Value', 'قيمة العقد')],
                [fmtAed(result.summary.advancePayment), t('Advance Payment', 'الدفعة المقدمة')],
                [fmtAed(result.summary.workingCapitalRequired), t('Working Capital', 'رأس المال العامل')],
                [`M${result.summary.peakNegativeMonth}`, t('Peak Deficit Month', 'شهر أقصى عجز')],
                [result.summary.paybackMonth ? `M${result.summary.paybackMonth}` : '—', t('Payback Month', 'شهر الاسترداد')],
                [`${result.summary.profitMarginPct}%`, t('Profit Margin', 'هامش الربح')],
              ].map(([v, k], i) => (
                <div key={i} style={{ background: 'var(--bg-primary)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                  <div style={{ fontWeight: 800, fontSize: '1.05rem', color: i === 2 ? 'var(--error)' : 'var(--primary)' }}>{v}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{k}</div>
                </div>
              ))}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 10, marginBottom: 0 }}>
              {t(`Total Retention: ${fmtAed(result.summary.totalRetentionWithheld)} AED • Release @ PC: ${fmtAed(result.summary.retentionAtCompletion)} AED • Release @ DLP End: ${fmtAed(result.summary.retentionAtDlpEnd)} AED`,
                 `إجمالي المحتجزات: ${fmtAed(result.summary.totalRetentionWithheld)} درهم • الإفراج عند التسليم: ${fmtAed(result.summary.retentionAtCompletion)} درهم • نهاية الصيانة: ${fmtAed(result.summary.retentionAtDlpEnd)} درهم`)}
            </p>
            {result.summary.hasDoubleDip && (
              <p style={{ color: 'var(--warning, #d97706)', marginTop: 10, fontSize: '0.85rem', marginBottom: 0 }}>
                ⚠️ {t(
                  `Double dip: a second financing trough of ${fmtAed(Math.abs(result.summary.secondTroughCashflow))} AED occurs around month ${result.summary.secondTroughMonth}. Prepare working capital for both periods.`,
                  `هبوط مزدوج: عجز مالي ثانٍ بقيمة ${fmtAed(Math.abs(result.summary.secondTroughCashflow))} درهم يظهر حول الشهر ${result.summary.secondTroughMonth}. جهّز رأس المال للفترتين.`,
                )}
              </p>
            )}
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textAlign: isArabic ? 'right' : 'left' }}>
                  <th>#</th>
                  <th>{t('Period', 'الفترة')}</th>
                  <th>{t('Planned Value', 'القيمة المخططة')}</th>
                  <th>{t('Cum %', 'تراكمي %')}</th>
                  <th>{t('Adv. Recovery', 'استرداد المقدمة')}</th>
                  <th>{t('Retention Held', 'المحتجزات')}</th>
                  <th>{t('Net Cert.', 'صافي الشهادة')}</th>
                  <th>{t('VAT', 'الضريبة')}</th>
                  <th>{t('Received', 'المستلم')}</th>
                  <th>{t('Expenditure', 'المصروفات')}</th>
                  <th>{t('Net Cashflow', 'صافي التدفق')}</th>
                  <th>{t('Cumulative', 'التراكمي')}</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((m) => (
                  <tr key={m.monthNumber} style={{ borderBottom: '1px solid var(--border-color)', background: m.isRetentionRelease ? 'rgba(var(--primary-rgb), 0.1)' : 'transparent' }}>
                    <td style={{ padding: 6, textAlign: 'center' }}>{m.monthNumber}</td>
                    <td style={{ padding: 6 }}>{m.monthLabel}{m.isRetentionRelease ? ` (${t('retention', 'محتجزات')})` : ''}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.plannedValue)}</td>
                    <td style={{ padding: 6 }}>{m.cumulProgressPct.toFixed(0)}%</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.advanceRecovery)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.retentionDeducted)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.netCertificate)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.vatOnCert)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.paymentReceived)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.expenditure)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.netCashflow)}</td>
                    <td style={{ padding: 6, color: m.cumulCashflow < 0 ? 'var(--error)' : 'var(--success)', fontWeight: 600 }}>{fmtAed(m.cumulCashflow)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 12 }}>
              {t('Net Certificate = Gross − Advance Recovery − Retention (+VAT). Cash inflow is delayed by (Certification + Payment) period. Highlighted rows indicate retention release periods.',
                 'صافي الشهادة = الإجمالي − استرداد الدفعة المقدمة − المحتجزات (+ الضريبة). يتأخر التدفق المالي للداخل بفترة الاعتماد والسداد. الصفوف المميّزة تعبر عن فترات الإفراج عن المحتجزات.')}
            </p>
          </div>

          <FeedbackModal 
            isOpen={true} 
            inline={true}
            toolName="Cash Flow" 
            projectName={cfg.projectName} 
            isArabic={isArabic} 
          />
        </>
      )}
    </div>
  );
}

export default function CashFlow({ token, isArabic, initialProjectName, onClearInitialName, onStartProject }) {
  return (
    <FeatureGate feature="cashflow" token={token} isArabic={isArabic}
      title={isArabic ? 'التدفق النقدي' : 'Cash Flow'}>
      <CashFlowTool 
        token={token} 
        isArabic={isArabic} 
        initialProjectName={initialProjectName} 
        onClearInitialName={onClearInitialName} 
        onStartProject={onStartProject}
      />
    </FeatureGate>
  );
}
