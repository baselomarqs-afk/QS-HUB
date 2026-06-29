import React, { useState, useEffect } from 'react';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import Workflow from './components/Workflow';
import MarketPrices from './components/MarketPrices';
import PlanComparison from './components/PlanComparison';
import Billing from './components/Billing';
import LandingPage from './components/LandingPage';
import SarahChat from './components/SarahChat';
import logoImg from './assets/logo.png';
import Admin from './components/Admin';
import QsAssistant from './components/QsAssistant';
import Projects from './components/Projects';
import Programme from './components/Programme';
import CashFlow from './components/CashFlow';
import {
  LayoutDashboard, Folder, Play, BarChart2, Eye, LogOut, Globe, Moon, Sun, CreditCard, Shield, Bot, Menu, X, CalendarDays, Wallet
} from 'lucide-react';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('qto_token') || '');
  const [user, setUser] = useState(null);
  const [page, setPage] = useState('dashboard');
  const [pageParams, setPageParams] = useState(null);
  const [selectedProject, setSelectedProject] = useState(null);
  const [isArabic, setIsArabic] = useState(false); // Default to English as requested
  const [isDark, setIsDark] = useState(true);
  const [showAuth, setShowAuth] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [moduleProjectName, setModuleProjectName] = useState({ programme: '', cashflow: '' });
  const [activeModules, setActiveModules] = useState({ programme: false, cashflow: false });

  useEffect(() => {
    if (token) {
      fetchUserProfile();
    }
  }, [token]);

  useEffect(() => {
    // Apply dark mode class to body
    if (isDark) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
  }, [isDark]);

  const fetchUserProfile = async () => {
    try {
      const res = await fetch("/api/auth/profile", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        setUser(data);
      } else {
        // Token invalid, logout
        handleLogout();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleLoginSuccess = (authToken, userData) => {
    setToken(authToken);
    setUser(userData);
    handleNavigate('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('qto_token');
    localStorage.removeItem('qto_user');
    setToken('');
    setUser(null);
    setSelectedProject(null);
    handleNavigate('dashboard');
  };

  const handleNavigate = (newPage, params = null) => {
    setPage(newPage);
    setPageParams(params);
  };

  const handleStartModuleProject = (module, name) => {
    setModuleProjectName(prev => ({ ...prev, [module]: name }));
    setActiveModules(prev => ({ ...prev, [module]: true }));
    handleNavigate(module);
  };

  const isQtoLimitZero = user && user.role !== 'admin' && (!user.plan || user.plan.projects === 0);
  const isWorkflowActive = selectedProject !== null && !isQtoLimitZero;
  const isProgrammeActive = activeModules.programme && !isQtoLimitZero;
  const isCashflowActive = activeModules.cashflow && !isQtoLimitZero;

  if (!token) {
    if (!showAuth) {
      return <LandingPage isArabic={isArabic} setIsArabic={setIsArabic} onGetStarted={() => setShowAuth(true)} />;
    }
    return (
      <div style={{ position: 'relative' }}>
        <button 
          onClick={() => setShowAuth(false)}
          className="btn btn-secondary" 
          style={{ position: 'absolute', top: '20px', left: isArabic ? 'auto' : '20px', right: isArabic ? '20px' : 'auto', zIndex: 10 }}
        >
          {isArabic ? 'الرئيسية' : 'Home'}
        </button>
        <Auth onLoginSuccess={handleLoginSuccess} isArabic={isArabic} />
      </div>
    );
  }

  return (
    <div className="dashboard-grid" style={{ direction: isArabic ? 'rtl' : 'ltr' }}>
      
      {/* Mobile Hamburger Button */}
      <button 
        className="mobile-menu-btn"
        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        aria-label="Toggle menu"
      >
        {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div 
          className="mobile-overlay"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`sidebar ${mobileMenuOpen ? 'sidebar-open' : ''}`} style={{
        background: 'var(--bg-secondary)',
        borderRight: isArabic ? 'none' : '1px solid var(--border-color)',
        borderLeft: isArabic ? '1px solid var(--border-color)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '25px 20px',
        height: '100vh',
        position: 'sticky',
        top: 0,
        overflowY: 'auto'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
          {/* Logo Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src={logoImg} 
              alt="THE QS HUB" 
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '50%',
                objectFit: 'cover',
                border: '1.5px solid rgba(59, 130, 246, 0.3)'
              }} 
            />
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>THE QS HUB</h2>
          </div>

          {/* Language Switch */}
          <button 
            className="btn btn-secondary" 
            onClick={() => setIsArabic(!isArabic)}
            style={{ width: '100%', gap: '8px', fontSize: '0.88rem', padding: '8px 12px' }}
          >
            <Globe size={14} />
            {isArabic ? 'English' : 'العربية'}
          </button>

          {/* Nav List */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', padding: '0 8px 4px' }}>
              {isArabic ? 'القائمة الرئيسية' : 'Main Menu'}
            </span>

            {/* Dashboard Link */}
            <button 
              onClick={() => { setPage('dashboard'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'dashboard' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'dashboard' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'dashboard' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <LayoutDashboard size={18} />
              {isArabic ? 'لوحة التحكم' : 'Dashboard'}
            </button>

            {/* Projects Link */}
            <button 
              onClick={() => { setPage('projects'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'projects' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'projects' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'projects' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <Folder size={18} />
              {isArabic ? 'المشاريع' : 'Projects'}
            </button>

            {/* Workflow Link */}
            <button 
              onClick={() => {
                if (isWorkflowActive) {
                  setPage('workflow');
                  setMobileMenuOpen(false);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'workflow' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'workflow' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'workflow' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: isWorkflowActive ? 'pointer' : 'not-allowed',
                opacity: isWorkflowActive ? 1 : 0.5,
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
              disabled={!isWorkflowActive}
            >
              <Play size={18} />
              {isArabic ? 'مسار حصر الكميات' : 'QTO Workflow'}
            </button>

            {/* Work Programme Link */}
            <button
              onClick={() => {
                if (isProgrammeActive) {
                  setPage('programme');
                  setMobileMenuOpen(false);
                }
              }}
              style={{
                display: 'flex', alignItems: 'center', gap: '12px', width: '100%', padding: '12px 15px',
                borderRadius: '8px', border: 'none',
                background: page === 'programme' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'programme' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'programme' ? 700 : 500, fontSize: '0.92rem',
                cursor: isProgrammeActive ? 'pointer' : 'not-allowed',
                opacity: isProgrammeActive ? 1 : 0.5,
                textAlign: isArabic ? 'right' : 'left', transition: 'all 0.2s ease',
              }}
              disabled={!isProgrammeActive}
            >
              <CalendarDays size={18} />
              {isArabic ? 'جدول زمني' : 'Work Programme'}
            </button>

            {/* Cash Flow Link */}
            <button
              onClick={() => {
                if (isCashflowActive) {
                  setPage('cashflow');
                  setMobileMenuOpen(false);
                }
              }}
              style={{
                display: 'flex', alignItems: 'center', gap: '12px', width: '100%', padding: '12px 15px',
                borderRadius: '8px', border: 'none',
                background: page === 'cashflow' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'cashflow' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'cashflow' ? 700 : 500, fontSize: '0.92rem',
                cursor: isCashflowActive ? 'pointer' : 'not-allowed',
                opacity: isCashflowActive ? 1 : 0.5,
                textAlign: isArabic ? 'right' : 'left', transition: 'all 0.2s ease',
              }}
              disabled={!isCashflowActive}
            >
              <Wallet size={18} />
              {isArabic ? 'التدفق النقدي' : 'Cash Flow'}
            </button>

            {/* Drawing Compare Link */}
            <button
              onClick={() => { setPage('compare'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'compare' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'compare' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'compare' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <Eye size={18} />
              {isArabic ? 'مقارنة المخططات' : 'Plan Comparison'}
            </button>

            {/* Market Prices Link */}
            <button 
              onClick={() => { setPage('market'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'market' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'market' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'market' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <BarChart2 size={18} />
              {isArabic ? 'أسعار السوق' : 'Market Prices'}
            </button>

            {/* Billing Link */}
            <button 
              onClick={() => { setPage('billing'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'billing' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'billing' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'billing' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <CreditCard size={18} />
              {isArabic ? 'الاشتراكات والفواتير' : 'Billing & Subscription'}
            </button>

            {/* QS Assistant Link */}
            <button 
              onClick={() => { setPage('qs_assistant'); setMobileMenuOpen(false); }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                width: '100%',
                padding: '12px 15px',
                borderRadius: '8px',
                border: 'none',
                background: page === 'qs_assistant' ? 'var(--primary-glow)' : 'transparent',
                color: page === 'qs_assistant' ? 'var(--primary)' : 'var(--text-secondary)',
                fontWeight: page === 'qs_assistant' ? 700 : 500,
                fontSize: '0.92rem',
                cursor: 'pointer',
                textAlign: isArabic ? 'right' : 'left',
                transition: 'all 0.2s ease',
              }}
            >
              <Bot size={18} />
              {isArabic ? 'مساعد الكميات الذكي' : 'QS Assistant'}
            </button>

            {/* Admin Dashboard Link */}
            {user && user.role === 'admin' && (
              <button 
                onClick={() => { setPage('admin'); setMobileMenuOpen(false); }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  width: '100%',
                  padding: '12px 15px',
                  borderRadius: '8px',
                  border: 'none',
                  background: page === 'admin' ? 'var(--primary-glow)' : 'transparent',
                  color: page === 'admin' ? 'var(--primary)' : 'var(--text-secondary)',
                  fontWeight: page === 'admin' ? 700 : 500,
                  fontSize: '0.92rem',
                  cursor: 'pointer',
                  textAlign: isArabic ? 'right' : 'left',
                  transition: 'all 0.2s ease',
                }}
              >
                <Shield size={18} />
                {isArabic ? 'لوحة تحكم المسؤول' : 'Admin Panel'}
              </button>
            )}
          </nav>
        </div>

        {/* Sidebar Footer (Profile / Theme / Logout) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {/* User profile details */}
          {user && (
            <div style={{ padding: '8px 10px', display: 'flex', alignItems: 'center', gap: '10px', borderTop: '1px solid var(--border-color)', paddingTop: '15px' }}>
              <div style={{
                width: '34px',
                height: '34px',
                borderRadius: '50%',
                backgroundColor: 'var(--primary-glow)',
                color: 'var(--primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.88rem'
              }}>{user.email.substring(0, 2).toUpperCase()}</div>
              <div style={{ overflow: 'hidden' }}>
                <p style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.email}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: 600 }}>{user.plan?.name || 'Free Plan'}</p>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: '8px' }}>
            {/* Theme Toggle */}
            <button 
              className="btn btn-secondary" 
              onClick={() => setIsDark(!isDark)}
              style={{ flex: 1, padding: '8px', borderRadius: '8px' }}
            >
              {isDark ? <Sun size={15} /> : <Moon size={15} />}
            </button>

            {/* Logout */}
            <button 
              className="btn btn-secondary" 
              onClick={handleLogout}
              style={{ flex: 1, padding: '8px', borderRadius: '8px', color: 'var(--error)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Body Content */}
      <main style={{ minHeight: '100vh', overflowY: 'auto', backgroundColor: 'var(--bg-primary)' }}>
        {page === 'dashboard' && (
          <Dashboard 
            token={token} 
            isArabic={isArabic} 
            onSelectProject={setSelectedProject}
            onNavigate={handleNavigate}
            onStartModuleProject={handleStartModuleProject}
            user={user}
          />
        )}
        {page === 'projects' && (
          <Projects 
            token={token} 
            isArabic={isArabic} 
            onSelectProject={setSelectedProject}
            onNavigate={handleNavigate}
            initialTab={pageParams?.tab}
          />
        )}
        {page === 'workflow' && (
          <Workflow 
            token={token} 
            project={selectedProject} 
            isArabic={isArabic}
            onNavigate={setPage}
          />
        )}
        {page === 'programme' && (
          <Programme 
            token={token} 
            isArabic={isArabic} 
            initialProjectName={moduleProjectName.programme}
            onClearInitialName={() => setModuleProjectName(prev => ({ ...prev, programme: '' }))}
            onStartProject={() => setActiveModules(prev => ({ ...prev, programme: true }))}
            initialLoadData={pageParams?.loadData}
            onClearInitialLoadData={() => setPageParams(null)}
          />
        )}
        {page === 'cashflow' && (
          <CashFlow 
            token={token} 
            isArabic={isArabic} 
            initialProjectName={moduleProjectName.cashflow}
            onClearInitialName={() => setModuleProjectName(prev => ({ ...prev, cashflow: '' }))}
            onStartProject={() => setActiveModules(prev => ({ ...prev, cashflow: true }))}
            initialLoadData={pageParams?.loadData}
            onClearInitialLoadData={() => setPageParams(null)}
          />
        )}
        {page === 'market' && <MarketPrices token={token} isArabic={isArabic} />}
        {page === 'compare' && <PlanComparison token={token} isArabic={isArabic} />}
        {page === 'billing' && <Billing token={token} isArabic={isArabic} user={user} onLogout={handleLogout} />}
        {page === 'qs_assistant' && <QsAssistant token={token} isArabic={isArabic} />}
        {page === 'admin' && <Admin token={token} isArabic={isArabic} />}
      </main>

      {/* Floating Sarah Chat Widget */}
      <SarahChat token={token} isArabic={isArabic} />
    </div>
  );
}
