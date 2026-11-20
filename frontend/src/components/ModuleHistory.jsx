// سجل المشاريع — Saved-project history for a module tool (programme / cashflow).
// Lists the user's saved projects; clicking a project loads it back into the tool,
// alongside quick Excel download and Delete actions.
import { useEffect, useState } from 'react';
import { History, Trash2, Loader2, Download, FolderOpen } from 'lucide-react';

export default function ModuleHistory({ feature, token, isArabic, refreshKey, onLoad, onExport }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [localRefresh, setLocalRefresh] = useState(0);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      await Promise.resolve();
      if (!active) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/modules/${feature}`, { headers: { Authorization: `Bearer ${token}` } });
        if (active && res.ok) setItems(await res.json());
      } catch { /* ignore */ } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [feature, token, refreshKey, localRefresh]);

  const fetchProject = async (id) => {
    setBusyId(id);
    try {
      const res = await fetch(`/api/modules/${feature}/item/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) return await res.json();
    } catch { /* ignore */ } finally {
      setBusyId(null);
    }
    return null;
  };

  const handleLoad = async (id) => {
    if (!onLoad) return;
    const data = await fetchProject(id);
    if (data) {
      onLoad({ id: data.id, config: data.config, summary: data.summary });
      setOpen(false);
    }
  };

  const handleExport = async (id, e) => {
    e.stopPropagation();
    if (!onExport) return;
    const data = await fetchProject(id);
    if (data) onExport({ id: data.id, config: data.config, summary: data.summary });
  };

  const remove = async (id, e) => {
    e.stopPropagation();
    try {
      await fetch(`/api/modules/${feature}/item/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
      setLocalRefresh((n) => n + 1);
    } catch { /* ignore */ }
  };

  if (!items.length && !loading) return null;

  return (
    <div style={{ marginBottom: 16 }}>
      <button className="btn btn-secondary" onClick={() => setOpen((o) => !o)} style={{ fontSize: '0.85rem' }}>
        <History size={15} /> {t('Saved Projects', 'المشاريع المحفوظة')} ({items.length}) {open ? '▾' : '▸'}
      </button>
      {open && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
          {loading && <Loader2 size={16} className="spin" />}
          {items.map((it) => (
            <div
              key={it.id}
              onClick={() => handleLoad(it.id)}
              title={onLoad ? t('Click to open saved project', 'اضغط لفتح المشروع المحفوظ') : undefined}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
                borderRadius: 8, padding: '7px 11px',
                cursor: onLoad ? 'pointer' : 'default',
              }}
            >
              {busyId === it.id ? (
                <Loader2 size={14} className="spin" style={{ color: 'var(--primary)' }} />
              ) : (
                <FolderOpen size={14} style={{ color: 'var(--primary)' }} />
              )}
              <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.84rem' }}>{it.name}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginRight: 'auto', marginLeft: isArabic ? 'auto' : 0 }}>{it.date}</span>

              {onExport && (
                <Download
                  size={15}
                  style={{ color: 'var(--primary)', cursor: 'pointer', margin: '0 4px' }}
                  onClick={(e) => handleExport(it.id, e)}
                  title={isArabic ? 'تنزيل التقرير (Excel)' : 'Download Report (Excel)'}
                />
              )}

              <Trash2
                size={15}
                style={{ color: 'var(--error)', cursor: 'pointer' }}
                onClick={(e) => remove(it.id, e)}
                title={isArabic ? 'حذف' : 'Delete'}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
