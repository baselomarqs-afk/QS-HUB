import React, { useState, useEffect } from 'react';
import { Folder, Calendar, ArrowRight, Trash2, FileSpreadsheet, LayoutList, CheckCircle2, Clock } from 'lucide-react';

export default function Projects({ token, isArabic, onSelectProject, onNavigate, initialTab }) {
  const [activeTab, setActiveTab] = useState(initialTab || 'qto');
  const [qtoProjects, setQtoProjects] = useState([]);
  const [progProjects, setProgProjects] = useState([]);
  const [cfProjects, setCfProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab || 'qto');
  }, [initialTab]);

  useEffect(() => {
    if (activeTab === 'qto' && qtoProjects.length === 0) fetchQto();
    else if (activeTab === 'programme' && progProjects.length === 0) fetchProg();
    else if (activeTab === 'cashflow' && cfProjects.length === 0) fetchCf();
  }, [activeTab]);

  const fetchQto = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/projects", { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setQtoProjects(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const fetchProg = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/modules/programme", { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setProgProjects(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const fetchCf = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/modules/cashflow", { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setCfProjects(await res.json());
    } catch (err) { console.error(err); } finally { setLoading(false); }
  };

  const handleDeleteQto = async (id, e) => {
    e.stopPropagation();
    if (!confirm(isArabic ? 'هل أنت متأكد من رغبتك في حذف هذا المشروع نهائياً؟' : 'Are you sure you want to delete this project permanently?')) return;
    try {
      const res = await fetch(`/api/projects/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setQtoProjects(prev => prev.filter(p => p.id !== id));
    } catch (err) { console.error(err); }
  };

  const handleDeleteModule = async (feature, id, e) => {
    e.stopPropagation();
    if (!confirm(isArabic ? 'هل أنت متأكد؟' : 'Are you sure?')) return;
    try {
      const res = await fetch(`/api/modules/${feature}/item/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) {
        if (feature === 'programme') setProgProjects(prev => prev.filter(p => p.id !== id));
        else setCfProjects(prev => prev.filter(p => p.id !== id));
      }
    } catch (err) { console.error(err); }
  };

  const handleLoadModule = async (feature, id) => {
    try {
      const res = await fetch(`/api/modules/${feature}/item/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        onNavigate(feature, { loadData: { id: data.id, config: data.config } });
      }
    } catch (err) { console.error(err); }
  };

  const renderQto = () => (
    loading && qtoProjects.length === 0 ? (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div className="spin-anim" style={{ width: '30px', height: '30px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 10px' }}></div>
        <p>{isArabic ? 'جاري جلب المشاريع...' : 'Fetching projects history...'}</p>
      </div>
    ) : qtoProjects.length === 0 ? (
      <div style={{ textAlign: 'center', padding: '50px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد مشاريع سابقة حالياً.' : 'No previous projects found.'}</p>
      </div>
    ) : (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {qtoProjects.map((proj) => (
          <div 
            key={proj.id} className="glass-card" onClick={() => { onSelectProject(proj); onNavigate('workflow'); }}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <div style={{ width: '45px', height: '45px', borderRadius: '10px', backgroundColor: 'rgba(59, 130, 246, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary)' }}>
                <Folder size={22} />
              </div>
              <div>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{proj.name}</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Calendar size={12} /> {proj.date}</span>
                  <span>•</span>
                  <span>{isArabic ? `الخطوة ${proj.current_step || 8} من 8` : `Step ${proj.current_step || 8} of 8`}</span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              {proj.current_step >= 7 && (
                <button className="btn btn-secondary" onClick={(e) => { e.stopPropagation(); window.open(`/api/workflow/export/excel?project_id=${proj.id}&Authorization=Bearer ${token}`); }} style={{ padding: '8px', borderRadius: '50%', color: 'var(--success)', borderColor: 'transparent' }} title={isArabic ? "تحميل إكسل" : "Download Excel"}>
                  <FileSpreadsheet size={18} />
                </button>
              )}
              <button className="btn btn-secondary" onClick={(e) => handleDeleteQto(proj.id, e)} style={{ padding: '8px', borderRadius: '50%', color: 'var(--error)', borderColor: 'transparent' }}>
                <Trash2 size={16} />
              </button>
              <ArrowRight size={18} color="var(--text-muted)" style={{ transform: isArabic ? 'rotate(180deg)' : 'none' }} />
            </div>
          </div>
        ))}
      </div>
    )
  );

  const renderModule = (items, feature) => (
    loading && items.length === 0 ? (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <div className="spin-anim" style={{ width: '30px', height: '30px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 10px' }}></div>
        <p>{isArabic ? 'جاري جلب المشاريع...' : 'Fetching projects history...'}</p>
      </div>
    ) : items.length === 0 ? (
      <div style={{ textAlign: 'center', padding: '50px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد مشاريع سابقة حالياً.' : 'No previous projects found.'}</p>
      </div>
    ) : (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {items.map((proj) => (
          <div 
            key={proj.id} className="glass-card" onClick={() => handleLoadModule(feature, proj.id)}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <div style={{ width: '45px', height: '45px', borderRadius: '10px', backgroundColor: feature === 'programme' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: feature === 'programme' ? 'var(--success)' : 'var(--warning)' }}>
                {feature === 'programme' ? <Clock size={22} /> : <CheckCircle2 size={22} />}
              </div>
              <div>
                <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{proj.name}</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Calendar size={12} /> {proj.date}</span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
              <button className="btn btn-secondary" onClick={(e) => handleDeleteModule(feature, proj.id, e)} style={{ padding: '8px', borderRadius: '50%', color: 'var(--error)', borderColor: 'transparent' }}>
                <Trash2 size={16} />
              </button>
              <ArrowRight size={18} color="var(--text-muted)" style={{ transform: isArabic ? 'rotate(180deg)' : 'none' }} />
            </div>
          </div>
        ))}
      </div>
    )
  );

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Tabs */}
        <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '10px' }}>
          <button 
            className={`btn ${activeTab === 'qto' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('qto')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '8px', padding: '10px 20px', whiteSpace: 'nowrap' }}
          >
            <LayoutList size={18} />
            {isArabic ? 'حصر الكميات (QTO)' : 'QTO History'}
          </button>
          <button 
            className={`btn ${activeTab === 'programme' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('programme')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '8px', padding: '10px 20px', whiteSpace: 'nowrap', backgroundColor: activeTab === 'programme' ? 'var(--success)' : undefined, color: activeTab === 'programme' ? '#fff' : undefined, borderColor: activeTab === 'programme' ? 'var(--success)' : undefined }}
          >
            <Clock size={18} />
            {isArabic ? 'جدول زمني' : 'Work Programme'}
          </button>
          <button 
            className={`btn ${activeTab === 'cashflow' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('cashflow')}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', borderRadius: '8px', padding: '10px 20px', whiteSpace: 'nowrap', backgroundColor: activeTab === 'cashflow' ? 'var(--warning)' : undefined, color: activeTab === 'cashflow' ? '#fff' : undefined, borderColor: activeTab === 'cashflow' ? 'var(--warning)' : undefined }}
          >
            <CheckCircle2 size={18} />
            {isArabic ? 'التدفق النقدي' : 'Cash Flow'}
          </button>
        </div>

        {/* History List */}
        <div className="glass-panel" style={{ padding: '25px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Folder size={20} color="var(--primary)" />
            {activeTab === 'qto' && (isArabic ? 'مشاريع حصر الكميات السابقة' : 'Takeoff History')}
            {activeTab === 'programme' && (isArabic ? 'تاريخ الجداول الزمنية' : 'Work Programme History')}
            {activeTab === 'cashflow' && (isArabic ? 'التدفقات النقدية السابقة' : 'Cash Flow History')}
          </h3>

          {activeTab === 'qto' && renderQto()}
          {activeTab === 'programme' && renderModule(progProjects, 'programme')}
          {activeTab === 'cashflow' && renderModule(cfProjects, 'cashflow')}
        </div>
      </div>
    </div>
  );
}
