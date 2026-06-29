// سجل المشاريع — Saved-project history for a module tool (programme / cashflow).
// Lists the user's saved projects and loads one back into the tool on click.
import React, { useEffect, useState } from 'react';
import { History, Trash2, Loader2, Download } from 'lucide-react';

export default function ModuleHistory({ feature, token, isArabic, onLoad, refreshKey, onExport }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const fetchList = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/modules/${feature}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) setItems(await res.json());
    } catch { /* ignore */ } finally { setLoading(false); }
  };

  useEffect(() => { fetchList(); /* eslint-disable-next-line */ }, [feature, token, refreshKey]);

  const load = async (id) => {
    try {
      const res = await fetch(`/api/modules/${feature}/item/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        onLoad({ id: data.id, config: data.config });
      }
    } catch { /* ignore */ }
  };

  const remove = async (id, e) => {
    e.stopPropagation();
    try {
      await fetch(`/api/modules/${feature}/item/${id}`, { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } });
      fetchList();
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
            <div key={it.id} 
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--bg-primary)', border: '1px solid var(--border-color)',
                borderRadius: 8, padding: '7px 11px',
              }}>
              <span onClick={() => load(it.id)} style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '0.84rem', cursor: 'pointer' }}>{it.name}</span>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginRight: 'auto', marginLeft: isArabic ? 'auto' : 0 }}>{it.date}</span>
              
              {onExport && (
                <Download 
                  size={15} 
                  style={{ color: 'var(--primary)', cursor: 'pointer', margin: '0 4px' }} 
                  onClick={async (e) => {
                    e.stopPropagation();
                    try {
                      const res = await fetch(`/api/modules/${feature}/item/${it.id}`, { headers: { Authorization: `Bearer ${token}` } });
                      if (res.ok) {
                        const data = await res.json();
                        onExport({ id: data.id, config: data.config });
                      }
                    } catch { /* ignore */ }
                  }}
                  title={isArabic ? 'تصدير إكسل' : 'Export Excel'}
                />
              )}

              <Trash2 size={15} style={{ color: 'var(--error)', cursor: 'pointer' }} onClick={(e) => remove(it.id, e)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
