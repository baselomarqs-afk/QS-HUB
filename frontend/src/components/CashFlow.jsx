// نافذة التدفق النقدي — Cash Flow window (bilingual). UAE / FIDIC-compliant
// S-Curve & monthly certificate forecast linked to the parametric construction
// schedule: pro-rata advance recovery, UAE FTA 5% VAT accounting, retention
// release tracking, interactive SVG S-Curve & cash flow charts, and Excel export.
import { useMemo, useState, useEffect, useRef } from 'react';
import { Loader2, Download, Save, Rocket, PlusCircle } from 'lucide-react';
import FeatureGate from './FeatureGate';
import ModuleHistory from './ModuleHistory';
import SpecPrefill from './SpecPrefill';
import DrawingUpload from './DrawingUpload';
import CashFlowCharts from './CashFlowCharts';
import { DEFAULT_CONFIG, deriveVilla, suggestedHandover, num } from '../engine/projectConfig';
import { VILLA_TYPE_DEFINITIONS } from '../engine/villaTypes';
import { buildActivityList, resolveFoundationType } from '../engine/durationEngine';
import { runScheduler } from '../engine/scheduler';
import { computeCashFlow, fmtAed } from '../engine/cashflow';
import FeedbackModal from './common/FeedbackModal';

const GEOM_KEYS = new Set([
  'villaType', 'buaPerFloor', 'complexityFactor', 'foundationType',
  'hasPool', 'hasDemolition', 'hasRoofGarden', 'hasBoundaryWall', 'hasExternalLandscape',
  'basementArea', 'mezzanineArea', 'startISO', 'handoverISO',
]);

/** Strip large base64 image thumbnails from drawings before persisting to DB. */
function sanitizeConfigForSave(cfg) {
  const drawings = Array.isArray(cfg.drawings)
    ? cfg.drawings.map((d) => ({ id: d.id, name: d.name, kind: d.kind, size: d.size, pages: d.pages }))
    : [];
  return { ...cfg, drawings };
}

function CashFlowTool({ token, isArabic, initialProjectName, onClearInitialName, onStartProject, initialLoadData, onClearInitialLoadData }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [cfg, setCfg] = useState(() => {
    if (initialLoadData?.config) return { ...DEFAULT_CONFIG, ...initialLoadData.config };
    if (initialProjectName) return { ...DEFAULT_CONFIG, projectName: initialProjectName };
    return { ...DEFAULT_CONFIG };
  });
  const [processed, setProcessed] = useState(() => Boolean(initialLoadData));
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [savedId, setSavedId] = useState(() => initialLoadData?.id ?? null); // reused so re-saves don't consume another credit
  const justLoaded = useRef(Boolean(initialLoadData));
  const [isSimulating, setIsSimulating] = useState(false);
  const [loadingPct, setLoadingPct] = useState(0);
  const [isHistoryView, setIsHistoryView] = useState(() => Boolean(initialLoadData));
  const timerRef = useRef(null);

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const derived = useMemo(() => deriveVilla(cfg), [cfg]);
  const effectiveFoundation = useMemo(() => resolveFoundationType(cfg), [cfg]);

  const missing = [];
  if (!cfg.projectName.trim()) missing.push(t('Project Name', 'اسم المشروع'));
  if (!cfg.villaType) missing.push(t('Villa Type', 'نوع الفيلا'));
  if (!(cfg.buaPerFloor > 0)) missing.push(t('BUA per Floor', 'مساحة البناء للدور'));
  if (!cfg.startISO) missing.push(t('Start Date', 'تاريخ البدء'));
  if (!(cfg.contractValueAed > 0)) missing.push(t('Contract Value', 'قيمة العقد'));
  const handoverInvalid = !!cfg.handoverISO && !!cfg.startISO && cfg.handoverISO <= cfg.startISO;
  const canProcess = missing.length === 0 && !handoverInvalid;

  useEffect(() => {
    if (initialProjectName && onClearInitialName) onClearInitialName();
  }, [initialProjectName, onClearInitialName]);

  useEffect(() => {
    if (initialLoadData && onClearInitialLoadData) onClearInitialLoadData();
  }, [initialLoadData, onClearInitialLoadData]);

  const result = useMemo(() => {
    if (!cfg.projectName.trim() || !cfg.villaType || !(cfg.buaPerFloor > 0) || !(cfg.contractValueAed > 0) || !cfg.startISO || handoverInvalid) {
      return null;
    }
    const acts = buildActivityList(cfg);
    const out = runScheduler(cfg, acts);
    return computeCashFlow(cfg, out.monthly);
  }, [cfg, handoverInvalid]);

  const show = processed && canProcess && result;

  const save = async (resultObj = result, configToSave = cfg) => {
    if (!resultObj) return;
    setSaving(true);
    setSavedMsg('');
    try {
      const cleanCfg = sanitizeConfigForSave(configToSave);
      const res = await fetch('/api/modules/cashflow/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          project_id: savedId,
          name: cleanCfg.projectName,
          config: cleanCfg,
          summary: resultObj.summary,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSavedId(data.project_id);
        setSavedMsg(t('Saved to history ✓', 'حُفظ في السجل ✓'));
      } else {
        setSavedMsg(data.detail || t('Save failed', 'فشل الحفظ'));
      }
    } catch {
      setSavedMsg(t('Save failed', 'فشل الحفظ'));
    } finally {
      setSaving(false);
    }
  };

  // Keep the 1-minute (600ms x 100) processing progress bar as requested by user
  const process = () => {
    if (canProcess) {
      if (timerRef.current) clearInterval(timerRef.current);
      setIsSimulating(true);
      setLoadingPct(0);
      let pct = 0;
      timerRef.current = setInterval(() => {
        pct += 1;
        setLoadingPct(pct);
        if (pct >= 100) {
          clearInterval(timerRef.current);
          timerRef.current = null;
          setIsSimulating(false);
          setProcessed(true);
          if (!savedId) {
            const acts = buildActivityList(cfg);
            const out = runScheduler(cfg, acts);
            const resObj = computeCashFlow(cfg, out.monthly);
            save(resObj, cfg);
          }
          if (onStartProject) onStartProject();
        }
      }, 600);
    }
  };

  const patch = (p) => {
    setCfg((c) => ({ ...c, ...p }));
    if (Object.keys(p).some((k) => GEOM_KEYS.has(k))) {
      setProcessed(false);
      setSavedMsg('');
      if (justLoaded.current) justLoaded.current = false;
      else setSavedId(null);
    }
  };

  const startNewProject = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    setIsSimulating(false);
    setIsHistoryView(false);
    setProcessed(false);
    setSavedId(null);
    setSavedMsg('');
    setCfg({ ...DEFAULT_CONFIG });
  };

  const exportExcel = async () => {
    if (!result) return;
    const mod = await import('../engine/cashflowExcel');
    mod.exportCashFlowToExcel(cfg, result, cfg.projectName || 'Project');
  };

  const onStart = (startISO) => {
    const linked = !cfg.handoverISO || cfg.handoverISO === suggestedHandover(cfg.startISO);
    patch(linked ? { startISO, handoverISO: suggestedHandover(startISO) } : { startISO });
  };

  const lbl = { display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 };
  const inp = { width: '100%', padding: '9px 11px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' };
  const card = { background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 14, padding: 22, marginBottom: 20 };

  const numField = (en, ar, key, step = '1', required = false) => {
    const rawVal = cfg[key];
    const displayVal = required ? (rawVal || '') : (rawVal === null || rawVal === undefined ? '' : rawVal);
    return (
      <div>
        <label style={lbl}>{t(en, ar)}{required ? ' *' : ''}</label>
        <input
          style={inp}
          type="number"
          step={step}
          min={0}
          value={displayVal}
          placeholder="0"
          onChange={(e) => patch({ [key]: e.target.value === '' ? 0 : num(e.target.value) })}
        />
      </div>
    );
  };

  const retTagLabel = (m) => {
    if (!m.isRetentionRelease) return '';
    if (m.retentionTag === 'pc_dlp') return ` (${t('PC + DLP Ret.', 'إفراج استلام + صيانة')})`;
    if (m.retentionTag === 'pc') return ` (${t('PC Retention', 'إفراج استلام ابتدائي')})`;
    if (m.retentionTag === 'dlp') return ` (${t('DLP Retention', 'إفراج نهاية الصيانة')})`;
    return ` (${t('Retention', 'محتجزات')})`;
  };

  return (
    <div style={{ padding: '28px clamp(16px, 4vw, 40px)', maxWidth: 1280, margin: '0 auto' }}>
      <h1 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>💰 {t('Cash-Flow Forecast', 'توقع التدفق النقدي')}</h1>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        {t('Flow: (1) Enter project and financial parameters, (2) attach drawings, (3) press Process to calculate the UAE FTA-compliant cash flow & S-Curve.',
           'خطوات العمل: (١) أدخل البيانات الهندسية والمالية للمشروع، (٢) أرفق المخططات، (٣) اضغط معالجة لإنشاء التدفق النقدي ومنحنى S-Curve وفق نظام الضريبة الإماراتي.')}
      </p>

      <ModuleHistory
        feature="cashflow"
        token={token}
        isArabic={isArabic}
        refreshKey={savedId}
        onLoad={({ id, config }) => {
          justLoaded.current = true;
          const merged = { ...DEFAULT_CONFIG, ...config };
          setCfg(merged);
          setProcessed(true);
          setSavedId(id);
          setSavedMsg('');
          setIsHistoryView(true);
          if (onStartProject) onStartProject();
        }}
        onExport={async ({ config }) => {
          const merged = { ...DEFAULT_CONFIG, ...config };
          const acts = buildActivityList(merged);
          const scheduleOut = runScheduler(merged, acts);
          const resObj = computeCashFlow(merged, scheduleOut.monthly);
          const mod = await import('../engine/cashflowExcel');
          mod.exportCashFlowToExcel(merged, resObj, merged.projectName || 'Project');
        }}
      />

      {isHistoryView && (
        <div style={{ marginBottom: 15, padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
            {t('History View — Read Only', 'وضع عرض السجل — للقراءة فقط')}
          </span>
          <button className="btn btn-secondary" onClick={startNewProject} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem' }}>
            <PlusCircle size={15} /> {t('New Project', 'مشروع جديد')}
          </button>
        </div>
      )}

      {!isHistoryView && (
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
            <div>
              <label style={lbl}>{t('Foundation Type', 'نوع الأساسات')}</label>
              <select style={inp} value={cfg.foundationType || 'auto'} onChange={(e) => patch({ foundationType: e.target.value })}>
                <option value="auto">
                  {t('Auto', 'تلقائي')} ({effectiveFoundation === 'raft' ? t('Raft', 'لبشة') : t('Isolated Footings', 'قواعد منفصلة')})
                </option>
                <option value="isolated">{t('Isolated Footings & Tie Beams', 'قواعد منفصلة وميدات')}</option>
                <option value="raft">{t('Raft Foundation', 'لبشة خرسانية')}</option>
              </select>
            </div>
            <div>
              <label style={lbl}>{t('Complexity', 'درجة التعقيد')}</label>
              <select style={inp} value={cfg.complexityFactor} onChange={(e) => patch({ complexityFactor: num(e.target.value) })}>
                <option value={0.8}>{t('Simple', 'بسيط')} (×0.8)</option>
                <option value={1.0}>{t('Standard', 'قياسي')} (×1.0)</option>
                <option value={1.2}>{t('Complex', 'معقّد')} (×1.2)</option>
              </select>
            </div>
            {derived.hasBasement && (
              <div>
                <label style={lbl}>{t('Basement Area (m²)', 'مساحة القبو (م²)')}</label>
                <input style={inp} type="number" step="10" value={cfg.basementArea || ''} onChange={(e) => patch({ basementArea: num(e.target.value) })} />
              </div>
            )}
            {derived.hasMezzanine && (
              <div>
                <label style={lbl}>{t('Mezzanine Area (m²)', 'مساحة الميزانين (م²)')}</label>
                <input style={inp} type="number" step="10" value={cfg.mezzanineArea || ''} onChange={(e) => patch({ mezzanineArea: num(e.target.value) })} />
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginTop: 14 }}>
            <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!cfg.hasBoundaryWall} onChange={(e) => patch({ hasBoundaryWall: e.target.checked })} /> 🧱 {t('Boundary Wall & Gates', 'السور الخارجي والبوابات')}
            </label>
            <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!cfg.hasExternalLandscape} onChange={(e) => patch({ hasExternalLandscape: e.target.checked })} /> 🌴 {t('External Paving & Landscape', 'الرصف وتنسيق الحدائق')}
            </label>
            <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!cfg.hasPool} onChange={(e) => patch({ hasPool: e.target.checked })} /> 🏊 {t('Pool', 'مسبح')}
            </label>
            <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!cfg.hasRoofGarden} onChange={(e) => patch({ hasRoofGarden: e.target.checked })} /> 🌿 {t('Roof Garden', 'حديقة سطح')}
            </label>
            <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
              <input type="checkbox" checked={!!cfg.hasDemolition} onChange={(e) => patch({ hasDemolition: e.target.checked })} /> 🧨 {t('Demolition', 'هدم')}
            </label>
          </div>

          <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>② {t('Financial Entries', 'البيانات المالية')}</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 }}>
            {numField('Contract Value Excl. VAT (AED)', 'قيمة العقد بدون ضريبة (درهم)', 'contractValueAed', '10000', true)}
            {numField('Advance Payment %', 'نسبة الدفعة المقدمة %', 'advancePaymentPct', '1')}
            {numField('Retention %', 'نسبة الاستقطاع %', 'retentionPct', '0.5')}
            {numField('Retention Release @ Completion %', 'إفراج الاستقطاع عند الإنجاز %', 'retentionReleaseAtCompletionPct', '5')}
            {numField('VAT %', 'ضريبة القيمة المضافة %', 'vatPct', '1')}
            {numField('Certification Period (Days)', 'فترة الاعتماد (بالأيام)', 'certificationPeriodDays', '1')}
            {numField('Payment Period (Days)', 'فترة الدفع (بالأيام)', 'paymentPeriodDays', '1')}
            {numField('DLP (Months)', 'فترة ضمان العيوب (أشهر)', 'defectsLiabilityMonths', '1')}
            {numField('Cost Ratio (cost/bill)', 'نسبة التكلفة للفاتورة', 'contractorCostRatio', '0.01')}
          </div>

          <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>③ {t('Attach & Analyze Drawings', 'إرفاق وتحليل المخططات')}</h3>
          <DrawingUpload
            drawings={cfg.drawings || []}
            setDrawings={(drawingsList) => patch({ drawings: drawingsList })}
            isArabic={isArabic}
            cfg={cfg}
            setCfg={patch}
            token={token}
          />

          <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>④ {t('Run Process', 'تشغيل المعالجة')}</h3>
          {handoverInvalid && (
            <p style={{ color: 'var(--error)', marginTop: 14 }}>⚠️ {t('Handover date must be after the start date.', 'يجب أن يكون تاريخ التسليم بعد تاريخ البدء.')}</p>
          )}
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
            {t('* Uses pro-rata UAE/FIDIC advance recovery, full FTA 5% VAT on advance, IPCs & retention releases, and pass-through VAT reconciliation.',
               '* يطبق استرداد الدفعة المقدمة بنسبة تناسبية (FIDIC)، وحساب ضريبة القيمة المضافة الإماراتية (5% FTA) على الدفعة المقدمة والمستخلصات وإفراج المحتجزات، مع فصل ضريبة الدولة عن ربح المقاول.')}
          </p>
        </div>
      )}

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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(138px, 1fr))', gap: 12, marginTop: 16 }}>
              {[
                [fmtAed(result.summary.contractValue), t('Contract (Ex. VAT)', 'قيمة العقد (بدون ضريبة)'), false],
                [fmtAed(result.summary.totalVat), t(`Total VAT (${cfg.vatPct}%)`, `إجمالي الضريبة (${cfg.vatPct}%)`), false],
                [fmtAed(result.summary.totalContractInclVat), t('Contract (Inc. VAT)', 'العقد شامل الضريبة'), false],
                [fmtAed(result.summary.advancePayment), t('Advance Payment', 'الدفعة المقدمة'), false],
                [fmtAed(result.summary.workingCapitalRequired), t('Working Capital', 'رأس المال العامل'), result.summary.workingCapitalRequired > 0],
                [result.summary.peakNegativeMonth ? `M${result.summary.peakNegativeMonth}` : '—', t('Peak Deficit Month', 'شهر أقصى عجز'), false],
                [result.summary.paybackMonth ? `M${result.summary.paybackMonth}` : '—', t('Payback Month', 'شهر الاسترداد'), false],
                [`${fmtAed(result.summary.totalProfit)} (${result.summary.profitMarginPct}%)`, t('Gross Profit', 'إجمالي الربح'), false],
              ].map(([v, k, isAlert], i) => (
                <div key={i} style={{ background: 'var(--bg-primary)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                  <div style={{ fontWeight: 800, fontSize: '1.02rem', color: isAlert ? 'var(--error)' : 'var(--primary)' }}>{v}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{k}</div>
                </div>
              ))}
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 12, borderTop: '1px solid var(--border-color)', paddingTop: 10, marginBottom: 0 }}>
              {t(`Total Retention: ${fmtAed(result.summary.totalRetentionWithheld)} AED • Release @ PC: ${fmtAed(result.summary.retentionAtCompletion)} AED • Release @ DLP End: ${fmtAed(result.summary.retentionAtDlpEnd)} AED`,
                 `إجمالي المحتجزات: ${fmtAed(result.summary.totalRetentionWithheld)} درهم • الإفراج عند الاستلام الابتدائي: ${fmtAed(result.summary.retentionAtCompletion)} درهم • نهاية الصيانة: ${fmtAed(result.summary.retentionAtDlpEnd)} درهم`)}
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

          <CashFlowCharts rows={result.rows} summary={result.summary} isArabic={isArabic} />

          <div style={{ ...card, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', textAlign: isArabic ? 'right' : 'left' }}>
                  <th style={{ padding: 6 }}>#</th>
                  <th style={{ padding: 6 }}>{t('Period', 'الفترة')}</th>
                  <th style={{ padding: 6 }}>{t('Planned', 'المخطط')}</th>
                  <th style={{ padding: 6 }}>{t('Cum %', 'تراكمي %')}</th>
                  <th style={{ padding: 6 }}>{t('Adv. Rec.', 'استرداد مقدمة')}</th>
                  <th style={{ padding: 6 }}>{t('Ret. Held', 'محتجز')}</th>
                  <th style={{ padding: 6 }}>{t('Ret. Rel.', 'إفراج محتجز')}</th>
                  <th style={{ padding: 6 }}>{t('Net Cert.', 'صافي الشهادة')}</th>
                  <th style={{ padding: 6 }}>{t('VAT', 'الضريبة')}</th>
                  <th style={{ padding: 6 }}>{t('Rcvd (Inc. VAT)', 'المستلم شامل الضريبة')}</th>
                  <th style={{ padding: 6 }}>{t('VAT to FTA', 'توريد الضريبة')}</th>
                  <th style={{ padding: 6 }}>{t('Expenditure', 'المصروفات')}</th>
                  <th style={{ padding: 6 }}>{t('Net CF', 'صافي التدفق')}</th>
                  <th style={{ padding: 6 }}>{t('Cumulative', 'التراكمي')}</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((m) => (
                  <tr key={m.monthNumber} style={{ borderBottom: '1px solid var(--border-color)', background: m.isRetentionRelease ? 'rgba(59, 130, 246, 0.08)' : 'transparent' }}>
                    <td style={{ padding: 6, textAlign: 'center' }}>{m.monthNumber}</td>
                    <td style={{ padding: 6 }}>{m.monthLabel}{retTagLabel(m)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.plannedValue)}</td>
                    <td style={{ padding: 6 }}>{m.cumulProgressPct.toFixed(0)}%</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.advanceRecovery)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.retentionDeducted)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.retentionReleased)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.netCertificate)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.vatOnCert)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.paymentReceived)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.vatRemitted)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.expenditure)}</td>
                    <td style={{ padding: 6 }}>{fmtAed(m.netCashflow)}</td>
                    <td style={{ padding: 6, color: m.cumulCashflow < 0 ? 'var(--error)' : 'var(--success)', fontWeight: 600 }}>{fmtAed(m.cumulCashflow)}</td>
                  </tr>
                ))}
                <tr style={{ borderTop: '2px solid var(--border-color)', fontWeight: 700, color: 'var(--text-primary)', background: 'var(--bg-primary)' }}>
                  <td style={{ padding: 7 }} colSpan={2}>{t('TOTAL', 'الإجمالي')}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.contractValue)}</td>
                  <td style={{ padding: 7 }}>100%</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.advancePayment)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalRetentionWithheld)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.retentionAtCompletion + result.summary.retentionAtDlpEnd)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.contractValue)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalVat)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalContractInclVat)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalVat)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalExpenditure)}</td>
                  <td style={{ padding: 7 }}>{fmtAed(result.summary.totalProfit)}</td>
                  <td style={{ padding: 7, color: 'var(--success)' }}>{fmtAed(result.summary.totalProfit)}</td>
                </tr>
              </tbody>
            </table>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 12 }}>
              {t('Pro-rata Advance Recovery prevents negative IPCs. Output VAT is collected on Advance, IPCs & Retention Releases and remitted to FTA (pass-through), so Final Cumulative Cash Flow equals exact Gross Profit.',
                 'استرداد الدفعة المقدمة بنسبة تناسبية يمنع أي مستخلص سالب. تُحسب ضريبة القيمة المضافة على الدفعة المقدمة والمستخلصات وإفراج المحتجزات وتُفصل لتوريدها للهيئة الاتحادية للضرائب (FTA)، بحيث يساوي الرصيد التراكمي النهائي صافي الربح بالضبط.')}
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

export default function CashFlow({ token, isArabic, initialProjectName, onClearInitialName, onStartProject, initialLoadData, onClearInitialLoadData }) {
  return (
    <FeatureGate feature="cashflow" token={token} isArabic={isArabic} title={isArabic ? 'التدفق النقدي' : 'Cash Flow'}>
      <CashFlowTool
        token={token}
        isArabic={isArabic}
        initialProjectName={initialProjectName}
        onClearInitialName={onClearInitialName}
        onStartProject={onStartProject}
        initialLoadData={initialLoadData}
        onClearInitialLoadData={onClearInitialLoadData}
      />
    </FeatureGate>
  );
}
