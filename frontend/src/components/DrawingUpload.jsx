import React, { useState } from 'react';

const KINDS = ['architectural', 'structural', 'mep', 'other'];

const KIND_LABELS = {
  architectural: ['Architectural', 'معماري'],
  structural: ['Structural', 'إنشائي'],
  mep: ['MEP', 'كهرباء وميكانيك'],
  other: ['Other', 'أخرى'],
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
        // Find all occurrences of '/Type /Page' or '/Count'
        // A simple robust approach is to look for "/Count " in the catalog
        const match = text.match(/\/Count\s+(\d+)/);
        if (match && match[1]) {
          resolve(parseInt(match[1], 10));
          return;
        }
        
        // Fallback: count /Type /Page objects
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

export default function DrawingUpload({ drawings, setDrawings, isArabic }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [busy, setBusy] = useState(false);

  async function onFiles(list) {
    if (!list || !list.length) return;
    setBusy(true);
    try {
      const out = [];
      for (const f of Array.from(list)) {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        let thumb = '';
        let pages = 1;

        if (f.type === 'application/pdf') {
          pages = await countPdfPages(f);
          thumb = ''; // Use PDF icon placeholder
        } else if (f.type.startsWith('image/')) {
          thumb = await fileToDataUrl(f);
          pages = 1;
        }

        out.push({
          id,
          name: f.name,
          kind: 'architectural',
          size: f.size,
          pages,
          thumb,
        });
      }
      if (out.length) {
        setDrawings([...drawings, ...out]);
      }
    } catch (e) {
      alert('Failed to read drawing: ' + (e.message || String(e)));
    } finally {
      setBusy(false);
    }
  }

  function remove(id) {
    setDrawings(drawings.filter((d) => d.id !== id));
  }

  function setKind(id, kind) {
    setDrawings(
      drawings.map((d) => (d.id === id ? { ...d, kind } : d))
    );
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <label className="btn btn-secondary" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <span>📎</span>
        <span>{t('Attach Project Drawings', 'إرفاق مخططات المشروع')}</span>
        <input 
          type="file" 
          accept="application/pdf,image/*" 
          multiple 
          style={{ display: 'none' }}
          disabled={busy} 
          onChange={(e) => { onFiles(e.target.files); e.target.value = ''; }} 
        />
      </label>
      {busy && <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', marginInlineStart: 12 }}>{t('Processing drawing sheets...', 'جاري معالجة ملفات المخططات...')}</span>}
      
      {drawings.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 8, fontStyle: 'italic' }}>
          {t('No drawings attached for reference.', 'لا توجد مخططات مرفقة للمرجع.')}
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
                position: 'relative'
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
                    color: 'var(--text-muted)'
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
                  color: 'var(--text-primary)'
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
                  color: 'var(--text-primary)'
                }}
              >
                {KINDS.map((k) => (
                  <option key={k} value={k}>
                    {t(KIND_LABELS[k][0], KIND_LABELS[k][1])}
                  </option>
                ))}
              </select>
              <button 
                className="btn sm ghost" 
                style={{ 
                  marginTop: 6, 
                  fontSize: '0.72rem', 
                  padding: '2px 4px', 
                  color: 'var(--error)',
                  cursor: 'pointer'
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
