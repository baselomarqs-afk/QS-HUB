import React, { useState, useEffect } from 'react';
import { Plus, Folder, Calendar, ArrowRight, Trash2, ShieldAlert, FileSpreadsheet } from 'lucide-react';

export default function Projects({ token, isArabic, onSelectProject, onNavigate }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/projects", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        setProjects(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };


  const handleDeleteProject = async (id, e) => {
    e.stopPropagation();
    if (!confirm(isArabic ? 'هل أنت متأكد من رغبتك في حذف هذا المشروع نهائياً؟' : 'Are you sure you want to delete this project permanently?')) return;

    try {
      const res = await fetch(`/api/projects/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setProjects(prev => prev.filter(p => p.id !== id));
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
        {/* History List */}
        <div className="glass-panel" style={{ padding: '25px' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Folder size={20} color="var(--primary)" />
            {isArabic ? 'المشاريع السابقة' : 'Takeoff History'}
          </h3>

          {loading && projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div className="spin-anim" style={{ width: '30px', height: '30px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 10px' }}></div>
              <p>{isArabic ? 'جاري جلب المشاريع...' : 'Fetching projects history...'}</p>
            </div>
          ) : projects.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '50px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد مشاريع سابقة حالياً.' : 'No previous projects found.'}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
              {projects.map((proj) => (
                <div 
                  key={proj.id}
                  className="glass-card"
                  onClick={() => {
                    onSelectProject(proj);
                    onNavigate('workflow');
                  }}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                    <div style={{
                      width: '45px',
                      height: '45px',
                      borderRadius: '10px',
                      backgroundColor: 'rgba(59, 130, 246, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--primary)'
                    }}>
                      <Folder size={22} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>{proj.name}</h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <Calendar size={12} />
                          {proj.date}
                        </span>
                        <span>•</span>
                        <span>
                          {isArabic ? `الخطوة ${proj.current_step || 8} من 8` : `Step ${proj.current_step || 8} of 8`}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                    {proj.current_step >= 7 && (
                      <button 
                        className="btn btn-secondary" 
                        onClick={(e) => {
                          e.stopPropagation();
                          window.open(`/api/workflow/export/excel?project_id=${proj.id}&Authorization=Bearer ${token}`);
                        }}
                        style={{ padding: '8px', borderRadius: '50%', color: 'var(--success)', borderColor: 'transparent' }}
                        title={isArabic ? "تحميل إكسل" : "Download Excel"}
                      >
                        <FileSpreadsheet size={18} />
                      </button>
                    )}
                    <button 
                      className="btn btn-secondary" 
                      onClick={(e) => handleDeleteProject(proj.id, e)}
                      style={{ padding: '8px', borderRadius: '50%', color: 'var(--error)', borderColor: 'transparent' }}
                    >
                      <Trash2 size={16} />
                    </button>
                    <ArrowRight size={18} color="var(--text-muted)" style={{ transform: isArabic ? 'rotate(180deg)' : 'none' }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
