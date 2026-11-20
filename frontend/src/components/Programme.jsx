// نافذة برنامج الأعمال — Work Programme window (bilingual). Genuine CPM
// schedule (Forward + Backward Pass, Total Float, Critical Path) for a UAE villa.
// Enforces server-verified per-project quota before revealing results/exports and
// locks the input form once completed so users must start a new project from Dashboard.
import { useMemo, useState, useEffect, useRef } from 'react';
import { Loader2, Download, Save, Rocket, RotateCcw, ArrowLeft, CheckCircle2 } from 'lucide-react';
import FeatureGate from './FeatureGate';
import ModuleHistory from './ModuleHistory';
import SpecPrefill from './SpecPrefill';
import DrawingUpload from './DrawingUpload';
import { DEFAULT_CONFIG, deriveVilla, suggestedHandover, num } from '../engine/projectConfig';
import { VILLA_TYPE_DEFINITIONS } from '../engine/villaTypes';
import { buildActivityList, autoCalculateTotalWeeks, resolveFoundationType } from '../engine/durationEngine';
import { runScheduler, fmtDate } from '../engine/scheduler';
import FeedbackModal from './common/FeedbackModal';

const SIG_KEYS = new Set([
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

function ProgrammeTool({
  token, isArabic, initialProjectName, onClearInitialName,
  onStartProject, onProjectComplete, onNavigate,
  initialLoadData, onClearInitialLoadData,
}) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [cfg, setCfg] = useState(() => {
    if (initialLoadData?.config) return { ...DEFAULT_CONFIG, ...initialLoadData.config };
    if (initialProjectName) return { ...DEFAULT_CONFIG, projectName: initialProjectName };
    return { ...DEFAULT_CONFIG };
  });
  const [processed, setProcessed] = useState(() => Boolean(initialLoadData?.config));
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [processError, setProcessError] = useState('');
  const [dirtyEdits, setDirtyEdits] = useState(false);
  const [savedId, setSavedId] = useState(() => initialLoadData?.id ?? null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [loadingPct, setLoadingPct] = useState(0);
  const [isHistoryView] = useState(() => Boolean(initialLoadData));
  const timerRef = useRef(null);

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const patch = (p) => {
    if (processed || isHistoryView) return; // Lock form once completed
    const isStructural = Object.keys(p).some((k) => SIG_KEYS.has(k));
    setCfg((c) => ({
      ...c,
      ...p,
      ...(isStructural ? { customDurations: {} } : {}),
    }));
    setProcessError('');
  };

  const derived = useMemo(() => deriveVilla(cfg), [cfg]);
  const effectiveFoundation = useMemo(() => resolveFoundationType(cfg), [cfg]);

  const missing = [];
  if (!cfg.projectName.trim()) missing.push(t('Project Name', 'اسم المشروع'));
  if (!cfg.villaType) missing.push(t('Villa Type', 'نوع الفيلا'));
  if (!(cfg.buaPerFloor > 0)) missing.push(t('BUA per Floor', 'مساحة البناء للدور'));
  if (!cfg.startISO) missing.push(t('Start Date', 'تاريخ البدء'));
  if (!cfg.handoverISO) missing.push(t('Handover Date', 'تاريخ التسليم'));
  const handoverInvalid = !!cfg.handoverISO && !!cfg.startISO && cfg.handoverISO <= cfg.startISO;
  const canProcess = missing.length === 0 && !handoverInvalid;

  useEffect(() => {
    if (initialProjectName && onClearInitialName) onClearInitialName();
  }, [initialProjectName, onClearInitialName]);

  useEffect(() => {
    if (initialLoadData && onClearInitialLoadData) onClearInitialLoadData();
  }, [initialLoadData, onClearInitialLoadData]);

  const out = useMemo(() => {
    if (!processed || !cfg.villaType || !(cfg.buaPerFloor > 0) || !cfg.startISO) return null;
    const baseActs = buildActivityList(cfg);
    return runScheduler(cfg, baseActs);
  }, [processed, cfg]);

  const totalDays = out?.totalDays ?? 1;
  const hasCustomEdits = Object.keys(cfg.customDurations || {}).length > 0;

  const saveToServer = async (scheduleOut, configToSave, existingId = savedId) => {
    setSaving(true);
    setSavedMsg('');
    try {
      const cleanCfg = sanitizeConfigForSave(configToSave);
      const res = await fetch('/api/modules/programme/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          project_id: existingId,
          name: cleanCfg.projectName,
          config: cleanCfg,
          summary: {
            villaType: cleanCfg.villaType,
            totalBua: derived.totalBua,
            startDate: scheduleOut.startDate,
            finishDate: scheduleOut.finishDate,
            totalWeeks: scheduleOut.totalWeeks,
            activities: scheduleOut.scheduled.length,
            criticalCount: scheduleOut.criticalCount,
          },
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSavedId(data.project_id);
        setDirtyEdits(false);
        setSavedMsg(t('Saved to history ✓', 'حُفظ في السجل ✓'));
        return { ok: true, id: data.project_id };
      }
      return { ok: false, error: data.detail || t('Save failed — quota limit reached.', 'فشل الحفظ — تم الوصول للحد المسموح.') };
    } catch {
      return { ok: false, error: t('Network error while saving project.', 'حدث خطأ في الاتصال أثناء حفظ المشروع.') };
    } finally {
      setSaving(false);
    }
  };

  // Server-verified entitlement gate + keep the 1-minute (600ms x 100) waiting bar intact
  const process = async () => {
    if (!canProcess || isSimulating || processed) return;
    setProcessError('');

    // Pre-check server entitlement so exhausted users get blocked immediately
    try {
      const accRes = await fetch('/api/billing/feature-access?feature=programme', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (accRes.ok) {
        const acc = await accRes.json();
        if (!acc.can_create) {
          setProcessError(t(
            'Project limit reached for Work Programme. Please subscribe or purchase an extra project from the Dashboard.',
            'تم الوصول للحد المسموح في برنامج الأعمال. يرجى الاشتراك أو إضافة مشروع من لوحة التحكم.',
          ));
          return;
        }
      }
    } catch {
      // Final authoritative check still runs on /save below
    }

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
        (async () => {
          const newActs = buildActivityList(cfg);
          const scheduleOut = runScheduler(cfg, newActs);
          const res = await saveToServer(scheduleOut, cfg, null);
          setIsSimulating(false);
          if (res.ok) {
            setProcessed(true);
            if (onStartProject) onStartProject();
            if (onProjectComplete) onProjectComplete();
          } else {
            setProcessError(res.error);
          }
        })();
      }
    }, 600);
  };

  const patchActDuration = (id, weeks) => {
    const clean = Math.max(0.5, Math.min(52, weeks || 0.5));
    setCfg((c) => ({
      ...c,
      customDurations: { ...(c.customDurations || {}), [id]: clean },
    }));
    setDirtyEdits(true);
    setSavedMsg('');
  };

  const resetCustomDurations = () => {
    setCfg((c) => ({ ...c, customDurations: {} }));
    setDirtyEdits(Boolean(savedId));
    setSavedMsg('');
  };

  const onStart = (startISO) => {
    const linked = !cfg.handoverISO || cfg.handoverISO === suggestedHandover(cfg.startISO);
    patch(linked ? { startISO, handoverISO: suggestedHandover(startISO) } : { startISO });
  };

  const exportExcel = async () => {
    if (!out) return;
    const mod = await import('../engine/programmeExcel');
    mod.exportProgrammeToExcel(out, cfg.projectName || 'Project', cfg.drawings || []);
  };

  const lbl = { display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 };
  const inp = { width: '100%', padding: '9px 11px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' };
  const card = { background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 14, padding: 22, marginBottom: 20 };

  return (
    <div style={{ padding: '28px clamp(16px, 4vw, 40px)', maxWidth: 1260, margin: '0 auto' }}>
      <h1 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>📅 {t('Construction Work Programme', 'الجدول الزمني للتنفيذ')}</h1>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        {t('Flow: (1) Enter the project entries or pre-fill from a specification, (2) attach & analyze drawings, (3) press Process to build the CPM schedule.',
           'خطوات العمل: (١) أدخل بيانات المشروع أو املأها تلقائياً من المواصفات، (٢) أرفق المخططات لتحليلها، (٣) اضغط معالجة لإنشاء جدول المسار الحرج (CPM).')}
      </p>

      {/* Download-only history shortcut (re-running a new project always starts from Dashboard) */}
      <ModuleHistory
        feature="programme"
        token={token}
        isArabic={isArabic}
        refreshKey={savedId}
        onExport={async ({ config }) => {
          const merged = { ...DEFAULT_CONFIG, ...config };
          const newActs = buildActivityList(merged);
          const scheduleOut = runScheduler(merged, newActs);
          const mod = await import('../engine/programmeExcel');
          mod.exportProgrammeToExcel(scheduleOut, merged.projectName || 'Project', merged.drawings || []);
        }}
      />

      {!processed && !isHistoryView && (
        <div style={card}>
          <h3 style={{ marginTop: 0, color: 'var(--text-primary)' }}>① {t('Project Entries', 'بيانات المشروع')}</h3>
          <SpecPrefill cfg={cfg} setCfg={patch} isArabic={isArabic} token={token} feature="programme" />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: 14 }}>
            <div>
              <label style={lbl}>{t('Project Name', 'اسم المشروع')} *</label>
              <input style={inp} value={cfg.projectName} onChange={(e) => patch({ projectName: e.target.value })} />
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
            <div>
              <label style={lbl}>{t('BUA per Floor (m²)', 'مساحة البناء للدور (م²)')} *</label>
              <input style={inp} type="number" step="10" min={0} value={cfg.buaPerFloor || ''} onChange={(e) => patch({ buaPerFloor: num(e.target.value) })} />
            </div>
            <div>
              <label style={lbl}>{t('Start Date', 'تاريخ البدء')} *</label>
              <input style={inp} type="date" value={cfg.startISO} onChange={(e) => onStart(e.target.value)} />
            </div>
            <div>
              <label style={lbl}>{t('Handover Date', 'تاريخ التسليم')} *</label>
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
              <label style={lbl}>{t('Plot Number', 'رقم القطعة')}</label>
              <input style={inp} value={cfg.plotNumber} onChange={(e) => patch({ plotNumber: e.target.value })} />
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

          <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>② {t('Attach & Analyze Drawings', 'إرفاق وتحليل المخططات')}</h3>
          <DrawingUpload
            drawings={cfg.drawings || []}
            setDrawings={(drawingsList) => patch({ drawings: drawingsList })}
            isArabic={isArabic}
            cfg={cfg}
            setCfg={patch}
            token={token}
            feature="programme"
          />

          <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>③ {t('Run Process', 'تشغيل المعالجة')}</h3>
          {handoverInvalid && (
            <p style={{ color: 'var(--error)', marginTop: 14 }}>⚠️ {t('Handover date must be after the start date.', 'يجب أن يكون تاريخ التسليم بعد تاريخ البدء.')}</p>
          )}
          {missing.length > 0 && (
            <p style={{ color: 'var(--warning, #d97706)', marginTop: 14 }}>⚠️ {t('Please fill required fields', 'يرجى تعبئة الحقول المطلوبة')}: {missing.join('، ')}</p>
          )}
          {processError && (
            <p style={{ color: 'var(--error)', background: 'rgba(239, 68, 68, 0.1)', padding: 12, borderRadius: 8, marginTop: 14, fontWeight: 600 }}>
              ⚠️ {processError}
            </p>
          )}

          {isSimulating ? (
            <div style={{ marginTop: 20, padding: 20, background: 'var(--bg-primary)', borderRadius: 8, border: '1px solid var(--border-color)', textAlign: 'center' }}>
              <h4 style={{ margin: 0, marginBottom: 10, color: 'var(--text-primary)' }}>{t('Processing Project Data...', 'جاري معالجة بيانات المشروع...')}</h4>
              <div style={{ width: '100%', height: 10, background: 'rgba(0,0,0,0.1)', borderRadius: 5, overflow: 'hidden' }}>
                <div style={{ width: `${loadingPct}%`, height: '100%', background: 'var(--primary)', transition: 'width 0.3s ease' }} />
              </div>
              <p style={{ marginTop: 10, marginBottom: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {loadingPct}% {t('Complete', 'مكتمل')}
              </p>
            </div>
          ) : (
            <button className="btn btn-primary" disabled={!canProcess} onClick={process} style={{ marginTop: 16, padding: '12px 20px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Rocket size={16} /> {t('Process — Build CPM Schedule', 'معالجة — إنشاء برنامج الأعمال')}
            </button>
          )}
        </div>
      )}

      {out && (
        <>
          <div style={{ marginBottom: 16, padding: '14px 18px', borderRadius: 10, background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.35)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--success)', fontWeight: 700 }}>
              <CheckCircle2 size={18} />
              <span>
                {t('Work Programme completed & saved! Export your Excel below. To create another project, start a new one from the Dashboard.',
                   'تم إنشاء وحفظ برنامج الأعمال بنجاح! يمكنك تحميل ملف الإكسل أدناه، ولعمل مشروع جديد ابدأ من لوحة التحكم.')}
              </span>
            </div>
            {onNavigate && (
              <button className="btn btn-secondary" onClick={() => onNavigate('dashboard')} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.84rem' }}>
                <ArrowLeft size={15} /> {t('Return to Dashboard', 'العودة للوحة التحكم')}
              </button>
            )}
          </div>

          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>
                📊 {cfg.projectName} — {cfg.villaType} ({effectiveFoundation === 'raft' ? t('Raft', 'لبشة') : t('Isolated Footings', 'قواعد منفصلة')})
              </h3>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {hasCustomEdits && (
                  <button className="btn btn-secondary" onClick={resetCustomDurations} title={t('Reset edited durations to fit Handover Date', 'إعادة ضبط المدد المعدّلة لتطابق تاريخ التسليم')}>
                    <RotateCcw size={15} /> {t('Re-fit Handover', 'ضبط لتاريخ التسليم')}
                  </button>
                )}
                {dirtyEdits && savedId && (
                  <button className="btn btn-secondary" onClick={() => saveToServer(out, cfg, savedId)} disabled={saving}>
                    {saving ? <Loader2 size={15} className="spin" /> : <Save size={15} />} {t('Save Duration Tweaks', 'حفظ تعديلات المدد')}
                  </button>
                )}
                <button className="btn btn-primary" onClick={exportExcel}>
                  <Download size={15} /> {t('Export Excel', 'تصدير إكسل')}
                </button>
              </div>
            </div>
            {savedMsg && <p style={{ color: 'var(--success)', fontSize: '0.85rem', margin: '8px 0 0' }}>{savedMsg}</p>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginTop: 16 }}>
              {[
                [derived.totalBua, t('Total BUA (m²)', 'إجمالي البناء (م²)')],
                [fmtDate(out.startDate), t('Start', 'البدء')],
                [fmtDate(out.finishDate), t('Finish', 'الانتهاء')],
                [out.totalWeeks, t('Weeks', 'أسابيع')],
                [out.scheduled.length, t('Activities', 'الأنشطة')],
                [out.criticalCount, t('Critical Tasks', 'أنشطة المسار الحرج')],
                [autoCalculateTotalWeeks(cfg), t('Benchmark wks', 'المرجعي (أسبوع)')],
              ].map(([v, k], i) => (
                <div key={i} style={{ background: 'var(--bg-primary)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem', color: i === 5 ? '#ef4444' : 'var(--primary)' }}>{v}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{k}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <thead>
                <tr style={{ textAlign: isArabic ? 'right' : 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: 6 }}>#</th>
                  <th style={{ padding: 6 }}>ID</th>
                  <th style={{ padding: 6 }}>{t('Activity', 'النشاط')}</th>
                  <th style={{ padding: 6 }}>{t('Pred.', 'السابق')}</th>
                  <th style={{ padding: 6 }}>{t('Wks', 'أسابيع')}</th>
                  <th style={{ padding: 6 }}>{t('Start', 'البدء')}</th>
                  <th style={{ padding: 6 }}>{t('Finish', 'الانتهاء')}</th>
                  <th style={{ padding: 6 }}>{t('Float (d)', 'سماحية (يوم)')}</th>
                  <th style={{ padding: 6, minWidth: 200 }}>{t('Timeline', 'المخطط الزمني')}</th>
                </tr>
              </thead>
              <tbody>{renderRows()}</tbody>
            </table>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 12 }}>
              {t('Genuine CPM schedule (Forward & Backward Pass). Fixed technical durations (7-day curing, 48hr flood test, handover) are protected. 🔴 / Red bars = Critical Path (Total Float = 0 days).',
                 'جدول مسار حرج CPM حقيقي (حساب المسار الأمامي والخلفي والسماحية). المدد الفنية الثابتة (معالجة الخرسانة ٧ أيام، اختبار الغمر ٤٨ ساعة) محمية من المطّ. 🔴 / الأعمدة الحمراء = المسار الحرج (سماحية = ٠ يوم).')}
            </p>
          </div>

          <FeedbackModal
            isOpen={true}
            inline={true}
            toolName="Work Programme"
            projectName={cfg.projectName}
            isArabic={isArabic}
          />
        </>
      )}
    </div>
  );

  function renderRows() {
    if (!out) return null;
    const rows = [];
    let prevPhase = '';
    let no = 1;
    for (const s of out.scheduled) {
      const a = s.activity;
      if (a.phaseId !== prevPhase) {
        rows.push(
          <tr key={`ph-${a.phaseId}-${no}`} style={{ background: `#${a.phaseColor}` }}>
            <td colSpan={9} style={{ color: '#fff', padding: '6px 8px', fontWeight: 700 }}>{isArabic ? a.phaseNameAr : a.phaseName}</td>
          </tr>,
        );
        prevPhase = a.phaseId;
      }
      const left = ((s.startDay - 1) / totalDays) * 100;
      const width = Math.max(1.5, (a.durationDays / totalDays) * 100);
      const preds = s.predecessorIds?.length ? s.predecessorIds.join(', ') : '—';
      const floatDays = s.totalFloatDays ?? 0;
      const isEdited = cfg.customDurations && cfg.customDurations[a.id] !== undefined;

      rows.push(
        <tr key={a.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
          <td style={{ padding: 6, textAlign: 'center' }}>{no++}</td>
          <td style={{ padding: 6, textAlign: 'center', whiteSpace: 'nowrap', fontWeight: s.isCritical ? 700 : 400, color: s.isCritical ? '#ef4444' : undefined }}>
            {a.id}{s.isCritical ? ' 🔴' : ''}
          </td>
          <td style={{ padding: 6, fontWeight: s.isCritical ? 600 : 400 }}>{isArabic ? a.nameAr : a.name}</td>
          <td style={{ padding: 6, whiteSpace: 'nowrap', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{preds}</td>
          <td style={{ padding: 6, width: 68 }}>
            <input
              type="number"
              step="0.5"
              min={0.5}
              value={String(a.durationWeeks)}
              onChange={(e) => patchActDuration(a.id, num(e.target.value))}
              style={{
                width: 58,
                padding: '3px 5px',
                borderRadius: 6,
                border: isEdited ? '1.5px solid var(--primary)' : '1px solid var(--border-color)',
                background: 'var(--bg-primary)',
                color: 'var(--text-primary)',
              }}
            />
          </td>
          <td style={{ padding: 6, whiteSpace: 'nowrap' }}>{fmtDate(s.startDate)}</td>
          <td style={{ padding: 6, whiteSpace: 'nowrap' }}>{fmtDate(s.finishDate)}</td>
          <td style={{ padding: 6, textAlign: 'center', fontWeight: floatDays === 0 ? 700 : 400, color: floatDays === 0 ? '#ef4444' : 'var(--text-muted)' }}>
            {floatDays}
          </td>
          <td style={{ padding: 6 }}>
            <div style={{ position: 'relative', height: 14, background: 'var(--bg-primary)', borderRadius: 4 }}>
              <div
                style={{
                  position: 'absolute',
                  insetInlineStart: `${left}%`,
                  width: `${width}%`,
                  height: '100%',
                  background: s.isCritical ? '#dc2626' : `#${a.phaseColor}`,
                  borderRadius: 4,
                }}
              />
            </div>
          </td>
        </tr>,
      );
    }
    return rows;
  }
}

export default function Programme({
  token, isArabic, initialProjectName, onClearInitialName,
  onStartProject, onProjectComplete, onNavigate,
  initialLoadData, onClearInitialLoadData,
}) {
  return (
    <FeatureGate feature="programme" token={token} isArabic={isArabic} title={isArabic ? 'جدول زمني' : 'Work Programme'}>
      <ProgrammeTool
        token={token}
        isArabic={isArabic}
        initialProjectName={initialProjectName}
        onClearInitialName={onClearInitialName}
        onStartProject={onStartProject}
        onProjectComplete={onProjectComplete}
        onNavigate={onNavigate}
        initialLoadData={initialLoadData}
        onClearInitialLoadData={onClearInitialLoadData}
      />
    </FeatureGate>
  );
}
