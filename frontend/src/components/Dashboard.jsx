import React, { useState, useEffect } from 'react';
import { Plus, Folder, Calendar, ArrowRight, Trash2, ShieldAlert, Play, CalendarDays, Wallet } from 'lucide-react';

export default function Dashboard({ token, isArabic, onSelectProject, onNavigate, onStartModuleProject, user }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [qtoProjName, setQtoProjName] = useState('');
  const [programmeProjName, setProgrammeProjName] = useState('');
  const [cashflowProjName, setCashflowProjName] = useState('');
  const [creating, setCreating] = useState(false);
  const [activeProject, setActiveProject] = useState(null);
  const [details, setDetails] = useState(null);
  const [programmeAccess, setProgrammeAccess] = useState(null);
  const [cashflowAccess, setCashflowAccess] = useState(null);

  useEffect(() => {
    fetchProjects();
    fetchActiveProjectState();
    fetchSubscriptionDetails();
    fetchModuleAccess();
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

  const fetchModuleAccess = async () => {
    try {
      const pRes = await fetch("/api/billing/feature-access?feature=programme", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (pRes.ok) {
        const pData = await pRes.json();
        setProgrammeAccess(pData);
      }
      
      const cRes = await fetch("/api/billing/feature-access?feature=cashflow", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (cRes.ok) {
        const cData = await cRes.json();
        setCashflowAccess(cData);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCheckout = async (tier) => {
    try {
      const res = await fetch(`/api/billing/checkout?tier=${tier}`, {
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

  const handleCheckoutAddon = async () => {
    await handleCheckout('addon');
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
    if (!qtoProjName.trim() || creating) return;

    setCreating(true);
    try {
      const res = await fetch("/api/projects", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_name: qtoProjName.trim(),
          current_step: 1
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to create project.');
      
      onSelectProject({ id: data.project_id, name: qtoProjName.trim(), current_step: 1 });
      onNavigate('workflow');
    } catch (err) {
      alert(err.message);
    } finally {
      setCreating(false);
      setQtoProjName('');
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
  const limitReached = details && (details.usage.projects >= details.project_limit);
  const isAdmin = user && user.role === 'admin';

  let userName = '';
  if (user) {
    if (user.name) {
      userName = user.name;
    } else if (user.email) {
      userName = user.email.split('@')[0];
    }
  }
  const displayUserName = userName ? userName.charAt(0).toUpperCase() + userName.slice(1) : '';

  return (
    <div className="dashboard-content" style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      {/* Welcome Banner */}
      <div style={{ marginBottom: '35px' }}>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
          {isArabic ? `أهلاً بك! م. ${displayUserName} 🏗️` : `Welcome! Eng. ${displayUserName} 🏗️`}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginTop: '6px' }}>
          {isArabic ? 'منصة حصر الكميات الذكية وتوليد جداول BOQ المعتمدة على الذكاء الاصطناعي.' : 'AI powered assistant for quantity taking-off , cash flow . work programs for villas project in the UAE..'}
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '25px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '35px' }}>
        <div 
          className="glass-card" 
          style={{ borderLeft: '4px solid var(--primary)', cursor: 'pointer', transition: 'all 0.2s ease' }}
          onClick={() => onNavigate('billing')}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'none'}
        >
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

        <div 
          className="glass-card"
          style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
          onClick={() => onNavigate('projects', { tab: 'qto' })}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'none'}
        >
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'حصر المشاريع' : 'Projects Takeoffs'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
            {details ? details.usage.projects : '...'}
          </h3>
          {details && details.extra_projects > 0 && (
            <span style={{ color: 'var(--primary)', fontSize: '0.78rem', fontWeight: 600 }}>
              (+{details.extra_projects} Add-ons)
            </span>
          )}
        </div>

        <div 
          className="glass-card"
          style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
          onClick={() => onNavigate('projects', { tab: 'programme' })}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'none'}
        >
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'برامج الأعمال المنجزة' : 'WORK PROGMS CREATED'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
            {programmeAccess ? programmeAccess.projects : '...'}
          </h3>
          {programmeAccess && programmeAccess.credits > 0 && (
            <span style={{ color: 'var(--success)', fontSize: '0.78rem', fontWeight: 600 }}>
              (+{programmeAccess.credits} Add-ons)
            </span>
          )}
        </div>

        {/* 4th Box: Cash Flows Done */}
        <div 
          className="glass-card"
          style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
          onClick={() => onNavigate('projects', { tab: 'cashflow' })}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'none'}
        >
          <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
            {isArabic ? 'التدفقات النقدية المنجزة' : 'CASH FLOWS DONE'}
          </span>
          <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
            {cashflowAccess ? cashflowAccess.projects : '...'}
          </h3>
          {cashflowAccess && cashflowAccess.credits > 0 && (
            <span style={{ color: 'var(--warning)', fontSize: '0.78rem', fontWeight: 600 }}>
              (+{cashflowAccess.credits} Add-ons)
            </span>
          )}
        </div>
      </div>

      {/* QTO System Tools Section */}
      <div style={{ marginBottom: '35px' }}>
        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '15px' }}>
          {isArabic ? 'أدوات النظام' : 'Q.S Tools'}
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '25px' }}>
          
          {/* Tile 1: QTO Workflow */}
          <div 
            className="glass-card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              padding: '25px',
              border: '1px solid rgba(59, 130, 246, 0.15)',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, transparent 100%), var(--bg-secondary)',
              gap: '15px',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 20px -5px rgba(59, 130, 246, 0.2)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {/* Top Interactive Info Area */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '12px',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                color: 'var(--primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Play size={24} fill="var(--primary)" />
              </div>
              <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                {isArabic ? 'مسار حصر الكميات' : 'QTO Workflow'}
              </h4>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
                {isArabic 
                  ? 'رفع المخططات الهندسية، حصر الكميات، وتوليد جداول كميات (BOQ) معتمدة على الذكاء الاصطناعي.'
                  : 'Upload engineering drawings, extract quantities, and generate standard BOQs powered by AI.'}
              </p>
            </div>

            {/* Divider */}
            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', margin: '5px 0' }} />

            {/* Stats / Project Counter */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
                  {isArabic ? 'المشاريع:' : 'Projects Counter:'}
                </span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  {isAdmin ? (isArabic ? 'غير محدود' : 'Infinite') : (details ? `${details.usage.projects} / ${details.project_limit}` : '...')}
                </span>
              </div>
              {!isAdmin && details && (
                <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, (details.usage.projects / details.project_limit) * 100)}%`,
                    height: '100%',
                    backgroundColor: (details.usage.projects >= details.project_limit) ? 'var(--error)' : 'var(--primary)',
                    borderRadius: '3px',
                    transition: 'width 0.4s ease'
                  }} />
                </div>
              )}
            </div>

            {/* Start Project Bar */}
            <div style={{ marginTop: '5px' }}>
              {(!isAdmin && details && details.usage.projects >= details.project_limit) ? (
                <div style={{
                  padding: '10px',
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '6px',
                  color: 'var(--error)',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span>⚠️</span>
                  <span>{isArabic ? 'تم الوصول للحد! يرجى الشراء.' : 'Limit reached! Please purchase.'}</span>
                </div>
              ) : (
                <form 
                  onSubmit={handleCreateProject}
                  style={{ display: 'flex', gap: '8px' }}
                >
                  <input
                    type="text"
                    className="form-input"
                    style={{ 
                      flex: 1, 
                      minWidth: '0',
                      fontSize: '0.85rem',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)'
                    }}
                    placeholder={isArabic ? 'اسم المشروع...' : 'Project name...'}
                    value={qtoProjName}
                    onChange={e => setQtoProjName(e.target.value)}
                    disabled={creating}
                  />
                  <button 
                    type="submit" 
                    className="btn btn-primary" 
                    style={{ padding: '8px 14px', fontSize: '0.85rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
                    disabled={creating || !qtoProjName.trim()}
                  >
                    {creating ? (isArabic ? 'جاري...' : 'Starting...') : (isArabic ? 'بدء 🚀' : 'Start 🚀')}
                  </button>
                </form>
              )}
            </div>

            {/* Add Project Green Box */}
            {!isAdmin && (
              <div 
                style={{ 
                  backgroundColor: 'rgba(16, 185, 129, 0.05)', 
                  border: '1px solid rgba(16, 185, 129, 0.3)', 
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  transition: 'all 0.2s ease',
                  marginTop: '5px'
                }}
                onClick={() => handleCheckout('addon')}
                onMouseOver={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.1)' }}
                onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.05)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Plus size={14} style={{ color: 'var(--success)' }} />
                  <span style={{ fontWeight: 700, color: 'var(--success)', fontSize: '0.8rem' }}>
                    {isArabic ? 'إضافة مشروع' : 'Add Project'}
                  </span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  {isArabic ? '50 درهم' : '50 AED'}
                </span>
              </div>
            )}
          </div>

          {/* Tile 2: Work Programme */}
          <div 
            className="glass-card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              padding: '25px',
              border: '1px solid rgba(16, 185, 129, 0.15)',
              background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, transparent 100%), var(--bg-secondary)',
              gap: '15px',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 20px -5px rgba(16, 185, 129, 0.2)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {/* Top Interactive Info Area */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '12px',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                color: 'var(--success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <CalendarDays size={24} />
              </div>
              <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                {isArabic ? 'جدول زمني' : 'Work Programme'}
              </h4>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
                {isArabic 
                  ? 'توليد جداول زمنية للعمل ومخططات غانت والمراحل الرئيسية للمشروع استناداً إلى الكميات المقاسة.'
                  : 'Generate work schedules, Gantt charts, and milestones automatically derived from measured quantities.'}
              </p>
            </div>

            {/* Divider */}
            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', margin: '5px 0' }} />

            {/* Stats / Project Counter */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
                  {isArabic ? 'المشاريع:' : 'Projects Counter:'}
                </span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  {isAdmin ? (isArabic ? 'غير محدود' : 'Infinite') : (programmeAccess ? `${programmeAccess.projects} / ${programmeAccess.limit}` : '...')}
                </span>
              </div>
              {!isAdmin && programmeAccess && (
                <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, (programmeAccess.projects / programmeAccess.limit) * 100)}%`,
                    height: '100%',
                    backgroundColor: (programmeAccess.projects >= programmeAccess.limit) ? 'var(--error)' : 'var(--success)',
                    borderRadius: '3px',
                    transition: 'width 0.4s ease'
                  }} />
                </div>
              )}
            </div>

            {/* Start Project Bar */}
            <div style={{ marginTop: '5px' }}>
              {(!isAdmin && programmeAccess && !programmeAccess.can_create) ? (
                <div style={{
                  padding: '10px',
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '6px',
                  color: 'var(--error)',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span>⚠️</span>
                  <span>{isArabic ? 'تم الوصول للحد! يرجى الشراء.' : 'Limit reached! Please purchase.'}</span>
                </div>
              ) : (
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!programmeProjName.trim()) return;
                    onStartModuleProject('programme', programmeProjName.trim());
                    setProgrammeProjName('');
                  }}
                  style={{ display: 'flex', gap: '8px' }}
                >
                  <input
                    type="text"
                    className="form-input"
                    style={{ 
                      flex: 1, 
                      minWidth: '0',
                      fontSize: '0.85rem',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)'
                    }}
                    placeholder={isArabic ? 'اسم المشروع...' : 'Project name...'}
                    value={programmeProjName}
                    onChange={e => setProgrammeProjName(e.target.value)}
                  />
                  <button 
                    type="submit" 
                    className="btn btn-primary" 
                    style={{ padding: '8px 14px', fontSize: '0.85rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
                    disabled={!programmeProjName.trim()}
                  >
                    {isArabic ? 'بدء 🚀' : 'Start 🚀'}
                  </button>
                </form>
              )}
            </div>

            {/* Add Project Green Box */}
            {!isAdmin && (
              <div 
                style={{ 
                  backgroundColor: 'rgba(16, 185, 129, 0.05)', 
                  border: '1px solid rgba(16, 185, 129, 0.3)', 
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  transition: 'all 0.2s ease',
                  marginTop: '5px'
                }}
                onClick={() => handleCheckout('programme')}
                onMouseOver={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.1)' }}
                onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.05)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Plus size={14} style={{ color: 'var(--success)' }} />
                  <span style={{ fontWeight: 700, color: 'var(--success)', fontSize: '0.8rem' }}>
                    {isArabic ? 'إضافة مشروع' : 'Add Project'}
                  </span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  {isArabic ? '50 درهم' : '50 AED'}
                </span>
              </div>
            )}
          </div>

          {/* Tile 3: Cash Flow */}
          <div 
            className="glass-card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              padding: '25px',
              border: '1px solid rgba(245, 158, 11, 0.15)',
              background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, transparent 100%), var(--bg-secondary)',
              gap: '15px',
              transition: 'transform 0.2s ease, box-shadow 0.2s ease',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 8px 20px -5px rgba(245, 158, 11, 0.2)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'none';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {/* Top Interactive Info Area */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '12px',
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                color: 'var(--warning)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Wallet size={24} />
              </div>
              <h4 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
                {isArabic ? 'التدفق النقدي' : 'Cash Flow'}
              </h4>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
                {isArabic 
                  ? 'توقعات التدفقات النقدية الداخلة والخارجة، وجداول الدفعات، ومنحنيات S-Curve المالية للمشروع.'
                  : 'Forecast project cash flows, payment schedules, and generate financial S-curves for budget planning.'}
              </p>
            </div>

            {/* Divider */}
            <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', margin: '5px 0' }} />

            {/* Stats / Project Counter */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
                  {isArabic ? 'المشاريع:' : 'Projects Counter:'}
                </span>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  {isAdmin ? (isArabic ? 'غير محدود' : 'Infinite') : (cashflowAccess ? `${cashflowAccess.projects} / ${cashflowAccess.limit}` : '...')}
                </span>
              </div>
              {!isAdmin && cashflowAccess && (
                <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${Math.min(100, (cashflowAccess.projects / cashflowAccess.limit) * 100)}%`,
                    height: '100%',
                    backgroundColor: (cashflowAccess.projects >= cashflowAccess.limit) ? 'var(--error)' : 'var(--warning)',
                    borderRadius: '3px',
                    transition: 'width 0.4s ease'
                  }} />
                </div>
              )}
            </div>

            {/* Start Project Bar */}
            <div style={{ marginTop: '5px' }}>
              {(!isAdmin && cashflowAccess && !cashflowAccess.can_create) ? (
                <div style={{
                  padding: '10px',
                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  borderRadius: '6px',
                  color: 'var(--error)',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <span>⚠️</span>
                  <span>{isArabic ? 'تم الوصول للحد! يرجى الشراء.' : 'Limit reached! Please purchase.'}</span>
                </div>
              ) : (
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!cashflowProjName.trim()) return;
                    onStartModuleProject('cashflow', cashflowProjName.trim());
                    setCashflowProjName('');
                  }}
                  style={{ display: 'flex', gap: '8px' }}
                >
                  <input
                    type="text"
                    className="form-input"
                    style={{ 
                      flex: 1, 
                      minWidth: '0',
                      fontSize: '0.85rem',
                      padding: '8px 10px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)'
                    }}
                    placeholder={isArabic ? 'اسم المشروع...' : 'Project name...'}
                    value={cashflowProjName}
                    onChange={e => setCashflowProjName(e.target.value)}
                  />
                  <button 
                    type="submit" 
                    className="btn btn-primary" 
                    style={{ padding: '8px 14px', fontSize: '0.85rem', borderRadius: '6px', whiteSpace: 'nowrap' }}
                    disabled={!cashflowProjName.trim()}
                  >
                    {isArabic ? 'بدء 🚀' : 'Start 🚀'}
                  </button>
                </form>
              )}
            </div>

            {/* Add Project Green Box */}
            {!isAdmin && (
              <div 
                style={{ 
                  backgroundColor: 'rgba(16, 185, 129, 0.05)', 
                  border: '1px solid rgba(16, 185, 129, 0.3)', 
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  borderRadius: '8px',
                  transition: 'all 0.2s ease',
                  marginTop: '5px'
                }}
                onClick={() => handleCheckout('cashflow')}
                onMouseOver={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.1)' }}
                onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.05)' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Plus size={14} style={{ color: 'var(--success)' }} />
                  <span style={{ fontWeight: 700, color: 'var(--success)', fontSize: '0.8rem' }}>
                    {isArabic ? 'إضافة مشروع' : 'Add Project'}
                  </span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  {isArabic ? '50 درهم' : '50 AED'}
                </span>
              </div>
            )}
          </div>
        </div>
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
          backgroundColor: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.3)',
          borderRadius: '8px',
          padding: '20px 25px',
          color: 'var(--text-primary)',
          display: 'flex',
          flexDirection: 'column',
          gap: '15px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--warning)', fontWeight: 800 }}>
            <span style={{ fontSize: '1.2rem', display: 'flex', alignItems: 'center' }}>⚠️</span>
            {isArabic ? 'تنبيه:' : 'Attention:'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: '1.6', fontWeight: 500 }}>
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

