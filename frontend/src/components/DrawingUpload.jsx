// إرفاق وتحليل المخططات — Real villa drawing uploader + AI Vision analyzer.
// Uploads architectural/structural PDFs or images, extracts real project entries
// (Villa Type, BUA, Foundation Type, Pool, Boundary Wall, Landscape, Roof Garden,
// Complexity, Plot Number) via /api/modules/drawings/analyze, lets the QS review
// & apply them in 1 click, and keeps reference metadata clean for Excel & DB save.
import { useState } from 'react';
import { Loader2, Sparkles, CheckCircle2 } from 'lucide-react';

let _drawingIdSeq = 0;
function makeDrawingId() {
  _drawingIdSeq += 1;
  return `drw-${_drawingIdSeq}-${Date.now()}`;
}

const KINDS = ['architectural', 'structural', 'mep', 'other'];

const KIND_LABELS = {
  architectural: ['Architectural', 'معماري'],
  structural: ['Structural', 'إنشائي'],
  mep: ['MEP', 'كهرباء وميكانيك'],
  other: ['Other', 'أخرى'],
};

const PARAM_LABELS = {
  projectName: ['Project Name', 'اسم المشروع'],
  clientName: ['Client Name', 'اسم العميل'],
  plotNumber: ['Plot Number', 'رقم القطعة'],
  location: ['Location', 'الموقع'],
  consultantName: ['Consultant Name', 'اسم الاستشاري'],
  villaType: ['Villa Type', 'نوع الفيلا'],
  foundationType: ['Foundation Type', 'نوع الأساسات'],
  buaPerFloor: ['BUA per Floor (m²)', 'مساحة البناء للدور (م²)'],
  basementArea: ['Basement Area (m²)', 'مساحة القبو (م²)'],
  mezzanineArea: ['Mezzanine Area (m²)', 'مساحة الميزانين (م²)'],
  hasPool: ['Swimming Pool', 'مسبح'],
  hasRoofGarden: ['Roof Garden', 'حديقة سطح'],
  hasExternalLandscape: ['External Paving & Landscape', 'الرصف وتنسيق الحدائق'],
  hasBoundaryWall: ['Boundary Wall & Gates', 'السور الخارجي والبوابات'],
  hasDemolition: ['Demolition', 'أعمال الهدم'],
  complexityFactor: ['Complexity', 'درجة التعقيد'],
};

function fileToDataUrl(file) {
  return new Promise((resolve) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result));
    r.onerror = () => resolve('');
    r.readAsDataURL(file);
  });
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// Lightweight zero-dependency client-side PDF page counter
function countPdfPages(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = function (e) {
      try {
        const arr = new Uint8Array(e.target.result);
        const text = new TextDecoder().decode(arr);
        const match = text.match(/\/Count\s+(\d+)/);
        if (match && match[1]) {
          resolve(parseInt(match[1], 10));
          return;
        }
        const pageMatches = text.match(/\/Type\s*\/Page\b/g);
        if (pageMatches) {
          resolve(pageMatches.length);
          return;
        }
        resolve(1);
      } catch {
        resolve(1);
      }
    };
    reader.onerror = () => resolve(1);
    reader.readAsArrayBuffer(file);
  });
}

export default function DrawingUpload({ drawings, setDrawings, isArabic, cfg, setCfg, token, feature }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [busy, setBusy] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [picked, setPicked] = useState({});
  const [appliedBanner, setAppliedBanner] = useState(false);
  const [filesMap, setFilesMap] = useState({}); // drawingId -> File (kept in memory only, never saved to DB)

  function fmtVal(key, v) {
    if (typeof v === 'boolean') return v ? t('Yes', 'نعم') : t('No', 'لا');
    if (key === 'complexityFactor') return `×${v}`;
    if (key === 'foundationType') {
      if (v === 'raft') return t('Raft Foundation', 'لبشة خرسانية');
      if (v === 'isolated') return t('Isolated Footings & Tie Beams', 'قواعد منفصلة وميدات');
    }
    if (v === undefined || v === null || v === '') return '—';
    return String(v);
  }

  async function runAiAnalysis(targetFiles) {
    if (!token || !setCfg || !targetFiles || !targetFiles.length) return;
    setAnalyzing(true);
    setAnalysis(null);
    setPicked({});
    setAppliedBanner(false);
    try {
      const formData = new FormData();
      for (const f of targetFiles) {
        formData.append('files', f);
      }
      const url = feature ? `/api/modules/drawings/analyze?feature=${encodeURIComponent(feature)}` : '/api/modules/drawings/analyze';
      const res = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const r = await res.json();
      if (!res.ok) {
        setAnalysis({ _success: false, _error: r.detail || r._error || t('Request denied.', 'تم رفض الطلب.') });
        return;
      }
      setAnalysis(r);
      if (r._success && r.suggestions) {
        const init = {};
        for (const k of Object.keys(r.suggestions)) init[k] = true;
        setPicked(init);
      }
    } catch (e) {
      setAnalysis({ _success: false, _error: e.message || String(e) });
    } finally {
      setAnalyzing(false);
    }
  }

  async function onFiles(list) {
    if (!list || !list.length) return;
    setBusy(true);
    try {
      const out = [];
      const nextFilesMap = { ...filesMap };
      for (const f of Array.from(list)) {
        const id = makeDrawingId();
        let thumb = '';
        let pages = 1;

        if (f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')) {
          pages = await countPdfPages(f);
          thumb = '';
        } else if (f.type.startsWith('image/')) {
          thumb = await fileToDataUrl(f);
          pages = 1;
        }

        // Auto-detect likely discipline from filename
        const lower = f.name.toLowerCase();
        let kind = 'architectural';
        if (lower.includes('str') || lower.includes('struct') || lower.includes('found') || lower.includes('col')) {
          kind = 'structural';
        } else if (lower.includes('mep') || lower.includes('elec') || lower.includes('plumb') || lower.includes('hvac')) {
          kind = 'mep';
        }

        nextFilesMap[id] = f;
        out.push({ id, name: f.name, kind, size: f.size, pages, thumb });
      }
      if (out.length) {
        const nextDrawings = [...drawings, ...out];
        setFilesMap(nextFilesMap);
        setDrawings(nextDrawings);
        const allFiles = nextDrawings.map((d) => nextFilesMap[d.id]).filter(Boolean);
        setBusy(false);
        // Automatically read & analyze uploaded villa drawings
        if (allFiles.length) await runAiAnalysis(allFiles);
        return;
      }
    } catch (e) {
      alert('Failed to read drawing: ' + (e.message || String(e)));
    } finally {
      setBusy(false);
    }
  }

  function remove(id) {
    setFilesMap((prev) => {
      const copy = { ...prev };
      delete copy[id];
      return copy;
    });
    const next = drawings.filter((d) => d.id !== id);
    setDrawings(next);
    if (!next.length) {
      setAnalysis(null);
      setPicked({});
      setAppliedBanner(false);
    }
  }

  function setKind(id, kind) {
    setDrawings(drawings.map((d) => (d.id === id ? { ...d, kind } : d)));
  }

  function applySelected() {
    if (!analysis?.suggestions || !setCfg) return;
    const patch = {};
    for (const [k, v] of Object.entries(analysis.suggestions)) {
      if (picked[k]) patch[k] = v;
    }
    if (Object.keys(patch).length) {
      setCfg(patch);
      setAppliedBanner(true);
    }
    setAnalysis(null);
    setPicked({});
  }

  const activeFiles = drawings.map((d) => filesMap[d.id]).filter(Boolean);
  const entries = analysis?.suggestions ? Object.entries(analysis.suggestions) : [];
  const selectedCount = Object.values(picked).filter(Boolean).length;

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' }}>
        <label className="btn btn-secondary" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <span>📎</span>
          <span>{t('Attach & Analyze Drawings (PDF / Images)', 'إرفاق وتحليل مخططات المشروع (PDF / صور)')}</span>
          <input
            type="file"
            accept="application/pdf,image/*"
            multiple
            style={{ display: 'none' }}
            disabled={busy || analyzing}
            onChange={(e) => { onFiles(e.target.files); e.target.value = ''; }}
          />
        </label>

        {activeFiles.length > 0 && token && setCfg && !analyzing && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => runAiAnalysis(activeFiles)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--primary)' }}
          >
            <Sparkles size={15} /> {t('Re-analyze Drawings with AI', 'إعادة تحليل المخططات بالذكاء الاصطناعي')}
          </button>
        )}
      </div>

      {busy && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 8 }}>
          {t('Reading drawing files...', 'جاري تجهيز ملفات المخططات...')}
        </p>
      )}

      {analyzing && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, padding: '10px 14px', borderRadius: 8, background: 'rgba(59, 130, 246, 0.08)', color: 'var(--primary)', fontSize: '0.84rem', fontWeight: 600 }}>
          <Loader2 size={16} className="spin" />
          <span>
            {t('Analyzing drawings with AI Vision (reading villa floors, BUA, foundation type, pool, boundary wall & landscape)...',
               'جاري تحليل المخططات بالذكاء الاصطناعي (قراءة عدد الأدوار، مساحة البناء، نوع الأساسات، المسبح، السور واللاندسكيب)...')}
          </span>
        </div>
      )}

      {appliedBanner && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10, padding: '8px 12px', borderRadius: 8, background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', fontSize: '0.83rem', fontWeight: 600 }}>
          <CheckCircle2 size={16} />
          <span>{t('Extracted drawing parameters applied to Project Entries above ✓', 'تم تطبيق البيانات المستخرجة من المخططات في الحقول أعلاه ✓')}</span>
        </div>
      )}

      {analysis && !analysis._success && (
        <p style={{ color: 'var(--error)', background: 'rgba(239, 68, 68, 0.1)', padding: 10, borderRadius: 8, marginTop: 10, fontSize: '0.84rem' }}>
          ⚠️ {analysis._error}
        </p>
      )}

      {analysis?._success && entries.length > 0 && (
        <div style={{ marginTop: 14, padding: 14, borderRadius: 10, background: 'var(--bg-primary)', border: '1px solid var(--primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
            <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              🔍 {t('Detected from Uploaded Drawings', 'البيانات المستخرجة من المخططات المرفقة')}
            </strong>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              {t(`Scanned ${analysis.totalPages || 0} pages (${analysis.visualPagesAnalyzed || 0} inspected visually) • Confidence: ${analysis.confidence}`,
                 `تم فحص ${analysis.totalPages || 0} صفحة (${analysis.visualPagesAnalyzed || 0} بصرياً) • الثقة: ${analysis.confidence}`)}
            </span>
          </div>

          {(isArabic ? analysis.summaryAr || analysis.summaryEn : analysis.summaryEn) && (
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 0, marginBottom: 10 }}>
              {isArabic ? (analysis.summaryAr || analysis.summaryEn) : analysis.summaryEn}
            </p>
          )}

          <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-secondary)', textAlign: isArabic ? 'right' : 'left' }}>
                  <th style={{ padding: '6px 8px' }}></th>
                  <th style={{ padding: '6px 8px' }}>{t('Parameter', 'الحقل')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('Current', 'الحالي')}</th>
                  <th style={{ padding: '6px 8px' }}>{t('Read from Drawings', 'مستخرج من المخططات')}</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([k, v]) => {
                  const cur = cfg ? cfg[k] : undefined;
                  const lbl = PARAM_LABELS[k] ? t(PARAM_LABELS[k][0], PARAM_LABELS[k][1]) : k;
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

          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 10 }}
            disabled={selectedCount === 0}
            onClick={applySelected}
          >
            ✓ {t(`Apply Extracted Data (${selectedCount})`, `تطبيق البيانات المستخرجة (${selectedCount})`)}
          </button>
        </div>
      )}

      {analysis?._success && entries.length === 0 && (
        <p style={{ color: 'var(--warning, #d97706)', background: 'rgba(245, 158, 11, 0.1)', padding: 10, borderRadius: 8, marginTop: 10, fontSize: '0.84rem' }}>
          {t('Drawings attached, but no clear project parameters could be extracted automatically. Please enter fields manually above.',
             'تم إرفاق المخططات، لكن لم يتم استخراج حقول واضحة تلقائياً. يرجى إدخال البيانات يدوياً أعلاه.')}
        </p>
      )}

      {drawings.length === 0 && !busy && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginTop: 8, fontStyle: 'italic' }}>
          {t('Attach villa architectural/structural drawings (PDF or images) to auto-detect villa type, BUA, foundation type & scope, and list them in your Excel report.',
             'أرفق المخططات المعمارية أو الإنشائية للفيلا (PDF أو صور) لاستخراج نوع الفيلا ومساحة البناء ونوع الأساسات ونطاق الأعمال تلقائياً وإدراجها في تقرير الإكسل.')}
        </p>
      )}

      {drawings.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginTop: 12 }}>
          {drawings.map((d) => (
            <div
              key={d.id}
              style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                padding: 10,
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
              }}
            >
              {d.thumb ? (
                <img
                  src={d.thumb}
                  alt={d.name}
                  style={{ width: '100%', height: 100, objectFit: 'cover', borderRadius: 4, marginBottom: 8 }}
                />
              ) : (
                <div
                  style={{
                    width: '100%',
                    height: 100,
                    background: 'var(--bg-secondary)',
                    borderRadius: 4,
                    marginBottom: 8,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '2rem',
                    color: 'var(--text-muted)',
                  }}
                >
                  📄
                </div>
              )}
              <div
                style={{
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  color: 'var(--text-primary)',
                }}
                title={d.name}
              >
                {d.name}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
                {d.pages} {t('pages', 'صفحات')} • {fmtSize(d.size)}
              </div>
              <select
                value={d.kind}
                onChange={(e) => setKind(d.id, e.target.value)}
                style={{
                  marginTop: 6,
                  padding: '3px 6px',
                  fontSize: '0.75rem',
                  borderRadius: 4,
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                }}
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {t(KIND_LABELS[k][0], KIND_LABELS[k][1])}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn sm ghost"
                style={{
                  marginTop: 6,
                  fontSize: '0.72rem',
                  padding: '2px 4px',
                  color: 'var(--error)',
                  cursor: 'pointer',
                }}
                onClick={() => remove(d.id)}
              >
                ✕ {t('Remove', 'إزالة')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
