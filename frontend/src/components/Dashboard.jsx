import React, { useState, useEffect } from 'react';
import { Plus, Folder, Calendar, ArrowRight, Trash2, ShieldAlert } from 'lucide-react';

export default function Dashboard({ token, isArabic, onSelectProject, onNavigate }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newProjName, setNewProjName] = useState('');
  const [creating, setCreating] = useState(false);
  const [activeProject, setActiveProject] = useState(null);
  const [details, setDetails] = useState(null);

  useEffect(() => {
    fetchProjects();
    fetchActiveProjectState();
    fetchSubscriptionDetails();
  }, []);

  const fetchSubscriptionDetails = async () => {
    try {
      const res = await fetch("/api/billing/subscription", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        setDetails(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckoutAddon = async () => {
    try {
      const res = await fetch(`/api/billing/checkout?tier=addon`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) {
        window.open(data.checkout_url, '_blank');
      } else {
        alert(data.detail || 'Could not generate checkout link.');
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

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

  const fetchActiveProjectState = async () => {
    try {
      const res = await fetch("/api/projects/active", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.has_active) {
        if (data.state_data && typeof data.state_data === 'string') {
          try {
            data.state_data = JSON.parse(data.state_data);
          } catch (e) {
            console.error("Error parsing active project state_data:", e);
          }
        }
        data.project_id = data.project_id || data.state_data?.project_id;
        setActiveProject(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjName.trim() || creating) return;

    setCreating(true);
    try {
      const res = await fetch("/api/projects", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_name: newProjName.trim(),
          current_step: 1
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create project.');
      
      onSelectProject({ id: data.project_id, name: newProjName.trim(), current_step: 1 });
      onNavigate('workflow');
    } catch (err) {
      alert(err.message);
    } finally {
      setCreating(false);
      setNewProjName('');
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
        if (activeProject && activeProject.project_id === id) {
          setActiveProject(null);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleResumeActive = () => {
    if (activeProject) {
      onSelectProject({
        id: activeProject.project_id || activeProject.state_data?.project_id,
        name: activeProject.state_data?.project_name || 'Villa Project',
        current_step: activeProject.current_step
      });
      onNavigate('workflow');
    }
  };

  const handleClearActive = async () => {
    try {
      const res = await fetch("/api/projects/active", {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setActiveProject(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="dashboard-content" style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      {/* Welcome Banner */}
      <div style={{ marginBottom: '35px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
          {isArabic ? 'أهلاً بك باشمهندس باسل! 🏗️' : 'Welcome Eng. Basel! 🏗️'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginTop: '6px' }}>
          {isArabic ? 'منصة حصر الكميات الذكية وتوليد جداول BOQ المعتمدة على الذكاء الاصطناعي.' : 'Your smart Quantity Takeoff and automated BOQ generation platform.'}
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '25px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '35px' }}>
        <div className="glass-card" style={{ borderLeft: '4px solid var(--primary)' }}>
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'الباقة الحالية' : 'Current Plan'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>{details ? details.plan_name : '...'}</h3>
          {details ? (
            details.subscription_status === 'active' ? (
              <span style={{ color: 'var(--success)', fontSize: '0.8rem', fontWeight: 700 }}>✓ Active</span>
            ) : (
              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Inactive</span>
            )
          ) : (
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>...</span>
          )}
        </div>

        <div className="glass-card">
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'حصر المشاريع' : 'Projects Takeoffs'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
            {details ? `${details.usage.projects} / ${details.project_limit}` : '...'}
          </h3>
          {details && details.extra_projects > 0 && (
            <span style={{ color: 'var(--primary)', fontSize: '0.78rem', fontWeight: 600 }}>
              (+{details.extra_projects} Add-ons)
            </span>
          )}
        </div>

        <div className="glass-card">
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'تصدير التقارير' : 'REPORTS EXPORTS'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
            {details ? details.usage.exports : '...'}
          </h3>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {isArabic ? 'ملفات Excel و PDF' : 'Excel & PDF files'}
          </span>
        </div>

        {/* 4th Box: Green Add Extra Project Box */}
        <div 
          className="glass-card" 
          style={{ 
            backgroundColor: 'rgba(16, 185, 129, 0.05)', 
            border: '1px solid rgba(16, 185, 129, 0.3)', 
            cursor: details ? 'pointer' : 'default',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
            transition: 'all 0.2s ease',
            opacity: details ? 1 : 0.6
          }}
          onClick={details ? handleCheckoutAddon : undefined}
          onMouseOver={(e) => { if(details) e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.1)' }}
          onMouseOut={(e) => { if(details) e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.05)' }}
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            color: 'var(--success)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '8px'
          }}>
            <Plus size={20} />
          </div>
          <h4 style={{ fontWeight: 700, color: 'var(--success)' }}>
            {isArabic ? 'إضافة مشروع' : 'Add Extra Project'}
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {isArabic ? '+50 درهم' : '+50 AED'}
          </span>
        </div>
      </div>

      {/* Create New Project Section */}
      <div className="glass-panel" style={{ padding: '25px', marginBottom: '35px' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '15px' }}>
          {isArabic ? 'بدء مشروع جديد' : 'Start a New Project'}
        </h3>
        <form onSubmit={handleCreateProject} style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
          <input
            type="text"
            className="input-field"
            style={{ flex: 1, minWidth: '250px' }}
            placeholder={isArabic ? 'اسم المشروع (مثال: فيلا رقم 12)' : 'Project Name (e.g. Villa 12)'}
            value={newProjName}
            onChange={e => setNewProjName(e.target.value)}
            disabled={creating}
          />
          <button type="submit" className="btn btn-primary" disabled={creating || !newProjName.trim()}>
            {creating ? (isArabic ? 'جاري الإنشاء...' : 'Creating...') : (isArabic ? 'بدء المشروع 🚀' : 'Start Project 🚀')}
          </button>
        </form>
      </div>

      {/* Active Project State Recovery Banner */}
      {activeProject && (
        <div className="glass-panel" style={{
          padding: '20px',
          borderLeft: isArabic ? 'none' : '4px solid var(--primary)',
          borderRight: isArabic ? '4px solid var(--primary)' : 'none',
          backgroundColor: 'rgba(59, 130, 246, 0.05)',
          marginBottom: '30px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '15px'
        }}>
          <div>
            <h4 style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldAlert size={18} color="var(--primary)" />
              {isArabic ? 'تنبيه: يوجد مشروع غير مكتمل!' : 'Found an unsaved project!'}
            </h4>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              {isArabic 
                ? `لقد كنت تعمل على الخطوة ${activeProject.current_step} (تاريخ التعديل: ${activeProject.updated_at})`
                : `You were working on Step ${activeProject.current_step} (Last updated: ${activeProject.updated_at})`}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-primary" onClick={handleResumeActive}>
              {isArabic ? '🔄 استكمال المشروع' : 'Resume Project'}
            </button>
            <button className="btn btn-secondary" onClick={handleClearActive} style={{ color: 'var(--error)' }}>
              {isArabic ? '🗑️ بدء جديد' : 'Clear State'}
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'center', margin: '40px 0' }}>
        {/* Attention Banner */}
        <div style={{
          width: '100%',
          maxWidth: '600px',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: '8px',
          padding: '20px 25px',
          color: '#e2e8f0',
          display: 'flex',
          flexDirection: 'column',
          gap: '15px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#3b82f6', fontWeight: 700 }}>
            <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center' }}>⚠️</span>
            {isArabic ? 'تنبيه:' : 'Attention:'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.9rem', color: '#60a5fa', lineHeight: '1.6' }}>
            <p>
              1- {isArabic 
                ? 'تم تصميم النظام لتوفير الوقت والجهد. لضمان النتائج، مراجعة المهندس ضرورية ولا غنى عنها.'
                : "The system is designed to save time and effort. To guarantee the results, engineer's review is a must."}
            </p>
            <p>
              2- {isArabic 
                ? 'تعتمد جودة نتائج النظام بشكل أساسي على جودة المخططات ودقة تصنيفها.'
                : 'Results quality of the system depends on the quality of the drawings and drawings classification accuracy.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

