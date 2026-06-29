// نافذة برنامج الأعمال — Work Programme window (bilingual). Parametric CPM
// schedule for a UAE villa: enter the project, press Process, get a phase-coloured
// Gantt with critical-path flags, editable durations, Excel export and history save.
import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Loader2, Download, Save, Rocket } from 'lucide-react';
import FeatureGate from './FeatureGate';
import ModuleHistory from './ModuleHistory';
import SpecPrefill from './SpecPrefill';
import DrawingUpload from './DrawingUpload';
import { DEFAULT_CONFIG, deriveVilla, suggestedHandover, num } from '../engine/projectConfig';
import { VILLA_TYPE_DEFINITIONS } from '../engine/villaTypes';
import { buildActivityList, autoCalculateTotalWeeks } from '../engine/durationEngine';
import { runScheduler, fmtDate } from '../engine/scheduler';
import FeedbackModal from './common/FeedbackModal';

function ProgrammeTool({ token, isArabic, initialProjectName, onClearInitialName, onStartProject }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [cfg, setCfg] = useState({ ...DEFAULT_CONFIG });
  const [acts, setActs] = useState(null);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState('');
  const [savedId, setSavedId] = useState(null); // set after first save; reused so re-saves don't consume another credit
  const justLoaded = useRef(false); // skip the savedId reset on the render right after loading from history
  const [isSimulating, setIsSimulating] = useState(false);
  const [loadingPct, setLoadingPct] = useState(0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [autoSavePending, setAutoSavePending] = useState(false);

  const patch = (p) => setCfg((c) => ({ ...c, ...p }));
  const derived = useMemo(() => deriveVilla(cfg), [cfg]);

  const missing = [];
  if (!cfg.projectName.trim()) missing.push(t('Project Name', 'اسم المشروع'));
  if (!cfg.villaType) missing.push(t('Villa Type', 'نوع الفيلا'));
  if (!(cfg.buaPerFloor > 0)) missing.push(t('BUA per Floor', 'مساحة البناء للدور'));
  if (!cfg.startISO) missing.push(t('Start Date', 'تاريخ البدء'));
  if (!cfg.handoverISO) missing.push(t('Handover Date', 'تاريخ التسليم'));
  const handoverInvalid = !!cfg.handoverISO && !!cfg.startISO && cfg.handoverISO <= cfg.startISO;
  const canProcess = missing.length === 0 && !handoverInvalid;

  // Any generation-affecting change invalidates the result.
  const sig = `${cfg.villaType}|${cfg.buaPerFloor}|${cfg.complexityFactor}|${cfg.hasPool}|${cfg.hasDemolition}|${cfg.hasRoofGarden}|${cfg.basementArea}|${cfg.mezzanineArea}|${cfg.startISO}|${cfg.handoverISO}`;
  useEffect(() => {
    setActs(null);
    setSavedMsg('');
    if (justLoaded.current) justLoaded.current = false; // keep loaded project's id
    else setSavedId(null);
  }, [sig]);

  useEffect(() => {
    if (initialProjectName) {
      patch({ projectName: initialProjectName });
      onClearInitialName();
    }
  }, [initialProjectName]);

  const out = useMemo(() => (acts ? runScheduler(cfg, acts) : null), [acts, cfg]);
  const totalDays = out?.totalDays ?? 1;


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
          const newActs = buildActivityList(cfg);
          setActs(newActs);
          if (!savedId) {
            const scheduleOut = runScheduler(cfg, newActs);
            save(scheduleOut);
          }
          if (onStartProject) onStartProject();
        }
      }, 600);
    }
  };
  const patchAct = (id, weeks) =>
    setActs((prev) => prev && prev.map((a) => (a.id === id ? { ...a, durationWeeks: weeks, durationDays: Math.round(weeks * 7) } : a)));

  const onStart = (startISO) => {
    const linked = !cfg.handoverISO || cfg.handoverISO === suggestedHandover(cfg.startISO);
    patch(linked ? { startISO, handoverISO: suggestedHandover(startISO) } : { startISO });
  };

  const exportExcel = async () => {
    const mod = await import('../engine/programmeExcel');
    mod.exportProgrammeToExcel(out, cfg.projectName || 'Project');
  };

  const save = async (scheduleOut = out) => {
    if (!scheduleOut) return;
    setSaving(true);
    setSavedMsg('');
    try {
      const res = await fetch('/api/modules/programme/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          project_id: savedId,
          name: cfg.projectName,
          config: cfg,
          summary: {
            villaType: cfg.villaType, totalBua: derived.totalBua,
            startDate: scheduleOut.startDate, finishDate: scheduleOut.finishDate,
            totalWeeks: scheduleOut.totalWeeks, activities: scheduleOut.scheduled.length,
          },
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

  const lbl = { display: 'block', fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 5 };
  const inp = { width: '100%', padding: '9px 11px', borderRadius: 8, border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' };
  const card = { background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 14, padding: 22, marginBottom: 20 };

  return (
    <div style={{ padding: '28px clamp(16px, 4vw, 40px)', maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ color: 'var(--text-primary)', marginBottom: 4 }}>📅 {t('Construction Work Programme', 'الجدول الزمني للتنفيذ')}</h1>
      <p style={{ color: 'var(--text-muted)', marginTop: 0 }}>
        {t('Flow: (1) Enter the project entries or pre-fill from a specification, (2) attach the drawings, (3) press Process to build the CPM schedule.',
           'خطوات العمل: (١) أدخل بيانات المشروع أو املأها تلقائياً من المواصفات، (٢) أرفق المخططات للرجوع إليها، (٣) اضغط معالجة لإنشاء جدول المسار الحرج (CPM).')}
      </p>

      <ModuleHistory feature="programme" token={token} isArabic={isArabic} refreshKey={savedId}
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
          <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={cfg.hasPool} onChange={(e) => patch({ hasPool: e.target.checked })} /> 🏊 {t('Pool', 'مسبح')}
          </label>
          <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={cfg.hasDemolition} onChange={(e) => patch({ hasDemolition: e.target.checked })} /> 🧨 {t('Demolition', 'هدم')}
          </label>
          <label style={{ color: 'var(--text-secondary)', display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="checkbox" checked={cfg.hasRoofGarden} onChange={(e) => patch({ hasRoofGarden: e.target.checked })} /> 🌿 {t('Roof Garden', 'حديقة سطح')}
          </label>
        </div>

        <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>② {t('Attach Drawings', 'إرفاق المخططات')}</h3>
        <DrawingUpload drawings={cfg.drawings || []} setDrawings={(drawingsList) => patch({ drawings: drawingsList })} isArabic={isArabic} />

        <h3 style={{ marginTop: 22, color: 'var(--text-primary)' }}>③ {t('Run Process', 'تشغيل المعالجة')}</h3>
        {handoverInvalid && (
          <p style={{ color: 'var(--error)', marginTop: 14 }}>⚠️ {t('Handover date must be after the start date.', 'يجب أن يكون تاريخ التسليم بعد تاريخ البدء.')}</p>
        )}
        {missing.length > 0 && (
          <p style={{ color: 'var(--warning, #d97706)', marginTop: 14 }}>⚠️ {t('Please fill required fields', 'يرجى تعبئة الحقول المطلوبة')}: {missing.join('، ')}</p>
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

      {out && (
        <>
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>📊 {cfg.projectName} — {cfg.villaType}</h3>
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
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginTop: 16 }}>
              {[
                [derived.totalBua, t('Total BUA (m²)', 'إجمالي البناء (م²)')],
                [fmtDate(out.startDate), t('Start', 'البدء')],
                [fmtDate(out.finishDate), t('Finish', 'الانتهاء')],
                [out.totalWeeks, t('Weeks', 'أسابيع')],
                [out.scheduled.length, t('Activities', 'الأنشطة')],
                [autoCalculateTotalWeeks(cfg), t('Benchmark wks', 'المرجعي (أسبوع)')],
              ].map(([v, k], i) => (
                <div key={i} style={{ background: 'var(--bg-primary)', borderRadius: 10, padding: '12px 14px', textAlign: 'center' }}>
                  <div style={{ fontWeight: 800, fontSize: '1.1rem', color: 'var(--primary)' }}>{v}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{k}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...card, overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <thead>
                <tr style={{ textAlign: isArabic ? 'right' : 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: 6 }}>#</th><th style={{ padding: 6 }}>ID</th><th style={{ padding: 6 }}>{t('Activity', 'النشاط')}</th>
                  <th style={{ padding: 6 }}>{t('Wks', 'أسابيع')}</th><th style={{ padding: 6 }}>{t('Start', 'البدء')}</th>
                  <th style={{ padding: 6 }}>{t('Finish', 'الانتهاء')}</th><th style={{ padding: 6, minWidth: 200 }}>{t('Timeline', 'المخطط الزمني')}</th>
                </tr>
              </thead>
              <tbody>{renderRows()}</tbody>
            </table>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 12 }}>
              {t('Durations are scaled so the programme fits exactly between the start and handover dates. Villas carry no fire scope. 🔴 = critical path.',
                 'تُحجَّم المدد بحيث يتسع البرنامج تماماً بين تاريخي البدء والتسليم. الفلل بدون أعمال حريق. 🔴 = المسار الحرج.')}
            </p>
          </div>
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
            <td colSpan={7} style={{ color: '#fff', padding: '6px 8px', fontWeight: 700 }}>{isArabic ? a.phaseNameAr : a.phaseName}</td>
          </tr>,
        );
        prevPhase = a.phaseId;
      }
      const left = ((s.startDay - 1) / totalDays) * 100;
      const width = Math.max(1.5, (a.durationDays / totalDays) * 100);
      rows.push(
        <tr key={a.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
          <td style={{ padding: 6, textAlign: 'center' }}>{no++}</td>
          <td style={{ padding: 6, textAlign: 'center', whiteSpace: 'nowrap' }}>{a.id}{s.isCritical ? ' 🔴' : ''}</td>
          <td style={{ padding: 6 }}>{isArabic ? a.nameAr : a.name}</td>
          <td style={{ padding: 6, width: 64 }}>
            <input type="number" step="0.5" min={0.5} value={String(a.durationWeeks)}
              onChange={(e) => patchAct(a.id, num(e.target.value))}
              style={{ width: 54, padding: '3px 5px', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-primary)' }} />
          </td>
          <td style={{ padding: 6, whiteSpace: 'nowrap' }}>{fmtDate(s.startDate)}</td>
          <td style={{ padding: 6, whiteSpace: 'nowrap' }}>{fmtDate(s.finishDate)}</td>
          <td style={{ padding: 6 }}>
            <div style={{ position: 'relative', height: 14, background: 'var(--bg-primary)', borderRadius: 4 }}>
              <div style={{ position: 'absolute', insetInlineStart: `${left}%`, width: `${width}%`, height: '100%', background: `#${a.phaseColor}`, borderRadius: 4 }} />
            </div>
          </td>
        </tr>,
      );
    }
    return rows;
  }
}

export default function Programme({ token, isArabic, initialProjectName, onClearInitialName, onStartProject }) {
  return (
    <FeatureGate feature="programme" token={token} isArabic={isArabic}
      title={isArabic ? 'جدول زمني' : 'Work Programme'}>
      <ProgrammeTool 
        token={token} 
        isArabic={isArabic} 
        initialProjectName={initialProjectName} 
        onClearInitialName={onClearInitialName} 
        onStartProject={onStartProject}
      />
    </FeatureGate>
  );
}
