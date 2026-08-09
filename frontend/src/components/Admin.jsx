import React, { useState, useEffect } from 'react';
import { 
  Users, CreditCard, Shield, Bot, Brain, AlertTriangle, Send, Loader, CheckCircle, XCircle 
} from 'lucide-react';

export default function Admin({ token, isArabic }) {
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [systemStats, setSystemStats] = useState(null);
  const [rules, setRules] = useState({ pending: [], global: [] });
  const [complaints, setComplaints] = useState([]);
  const [feedback, setFeedback] = useState({ summary: [], items: [] });

  // Chat state
  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState([
    {
      role: 'assistant',
      content: isArabic
        ? 'أهلاً بك يا منشئ المنصة! 👑\n\nأنا المدير التنفيذي ومساعدك الذكي لإدارة المنصة بالكامل (AI Manager). يمكنني مساعدتك في صيانة النظام والاستعلام عن الأداء.'
        : 'Welcome Founder! 👑\n\nI am the AI Manager. I can help you monitor stats, trigger database updates, and perform system operations.'
    }
  ]);
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'users') {
        const res = await fetch('/api/admin/users', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setUsers(await res.json());
      } else if (activeTab === 'subscriptions') {
        const res = await fetch('/api/admin/subscriptions', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setSubscriptions(await res.json());
      } else if (activeTab === 'system') {
        const res = await fetch('/api/admin/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setSystemStats(await res.json());
      } else if (activeTab === 'rules') {
        const res = await fetch('/api/admin/memory-rules', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setRules(await res.json());
      } else if (activeTab === 'complaints') {
        const res = await fetch('/api/admin/complaints', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setComplaints(await res.json());
      } else if (activeTab === 'feedback') {
        const res = await fetch('/api/admin/feedback', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) setFeedback(await res.json());
      }
    } catch (err) {
      console.error('Admin fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRule = async (ruleId) => {
    try {
      const res = await fetch('/api/admin/memory-rules/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ rule_id: ruleId })
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleRejectRule = async (ruleId) => {
    try {
      const res = await fetch('/api/admin/memory-rules/reject', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ rule_id: ruleId })
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleResolveComplaint = async (complaintId) => {
    try {
      const res = await fetch('/api/admin/complaints/resolve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ complaint_id: complaintId })
      });
      if (res.ok) {
        fetchData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = { role: 'user', content: chatInput };
    setChatHistory(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch('/api/admin/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ prompt: userMsg.content })
      });
      const data = await res.json();
      if (res.ok) {
        setChatHistory(prev => [...prev, { role: 'assistant', content: data.reply, action_result: data.action_result }]);
      } else {
        setChatHistory(prev => [...prev, { role: 'assistant', content: 'Error communicating with AI manager.' }]);
      }
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Connection failed.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '1200px', margin: '0 auto' }}>
      
      {/* Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--primary)', margin: 0 }}>
            {isArabic ? 'لوحة تحكم المسؤول 👑' : 'Founder Admin Dashboard 👑'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '5px' }}>
            {isArabic ? 'إدارة المستخدمين والاشتراكات وصحة النظام وعمليات الصيانة بالكامل.' : 'Oversee users, subscriptions, system health, and global rules.'}
          </p>
        </div>
      </div>

      {/* Tabs list */}
      <div style={{
        display: 'flex',
        gap: '10px',
        borderBottom: '1px solid var(--border-color)',
        marginBottom: '30px',
        overflowX: 'auto',
        paddingBottom: '5px'
      }}>
        {[
          { id: 'users', label: isArabic ? '👥 المستخدمين' : '👥 Users' },
          { id: 'subscriptions', label: isArabic ? '💳 الاشتراكات' : '💳 Subscriptions' },
          { id: 'system', label: isArabic ? '⚙️ حالة النظام' : '⚙️ System Health' },
          { id: 'chat', label: isArabic ? '🤖 AI Manager' : '🤖 AI Manager' },
          { id: 'rules', label: isArabic ? '🧠 قواعد التعلم' : '🧠 AI Learning' },
          { id: 'complaints', label: isArabic ? '🚨 شكاوى العملاء' : '🚨 Complaints' },
          { id: 'feedback', label: isArabic ? '⭐ تقييمات الأدوات' : '⭐ Tool Feedback' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 18px',
              fontSize: '0.92rem',
              fontWeight: activeTab === tab.id ? 700 : 500,
              background: activeTab === tab.id ? 'var(--primary-glow)' : 'transparent',
              color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-secondary)',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="glass-panel" style={{ padding: '30px', minHeight: '400px' }}>
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '300px' }}>
            <div className="spin-anim" style={{ width: '40px', height: '40px', border: '3px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', marginBottom: '15px' }}></div>
            <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'جاري تحميل البيانات...' : 'Loading data...'}</p>
          </div>
        ) : (
          <>
            {/* 1. USERS TAB */}
            {activeTab === 'users' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '20px' }}>{isArabic ? 'المستخدمون المسجلون' : 'Registered Platform Users'}</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: isArabic ? 'right' : 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>ID</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>{isArabic ? 'البريد الإلكتروني' : 'Email Address'}</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>{isArabic ? 'الصلاحية' : 'Role'}</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>{isArabic ? 'تاريخ التسجيل' : 'Registered At'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(u => (
                        <tr key={u.id} style={{ borderBottom: '1px solid var(--border-color)', hover: { background: 'rgba(255,255,255,0.05)' } }}>
                          <td style={{ padding: '12px 8px' }}>{u.id}</td>
                          <td style={{ padding: '12px 8px', fontWeight: 600 }}>{u.email}</td>
                          <td style={{ padding: '12px 8px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '12px',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              background: u.role === 'admin' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                              color: u.role === 'admin' ? 'var(--error)' : 'var(--primary)'
                            }}>{u.role}</span>
                          </td>
                          <td style={{ padding: '12px 8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            {new Date(u.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 2. SUBSCRIPTIONS TAB */}
            {activeTab === 'subscriptions' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '20px' }}>{isArabic ? 'الاشتراكات الفعالة' : 'Active Billing Subscriptions'}</h3>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: isArabic ? 'right' : 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>User Email</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Tool</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Tier</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Provider</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Status</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Projects</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>AI Calls</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>Exports</th>
                        <th style={{ padding: '12px 8px', fontWeight: 700 }}>End Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subscriptions.map(s => (
                        <tr key={s.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '12px 8px', fontWeight: 600 }}>{s.user_email}</td>
                          <td style={{ padding: '12px 8px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '8px',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              background: s.feature === 'programme' ? 'rgba(16, 185, 129, 0.15)' : s.feature === 'cashflow' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                              color: s.feature === 'programme' ? 'var(--success)' : s.feature === 'cashflow' ? 'var(--warning)' : 'var(--primary)'
                            }}>
                              {s.feature === 'programme' ? 'Work Programme' : s.feature === 'cashflow' ? 'Cash Flow' : 'QTO'}
                            </span>
                          </td>
                          <td style={{ padding: '12px 8px' }}>
                            <span style={{ fontWeight: 700 }}>Tier {s.plan_tier}</span>
                          </td>
                          <td style={{ padding: '12px 8px', textTransform: 'capitalize' }}>{s.provider}</td>
                          <td style={{ padding: '12px 8px' }}>
                            <span style={{
                              padding: '3px 8px',
                              borderRadius: '12px',
                              fontSize: '0.78rem',
                              fontWeight: 700,
                              background: s.status === 'active' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                              color: s.status === 'active' ? 'var(--success)' : 'var(--warning)'
                            }}>{s.status}</span>
                          </td>
                          <td style={{ padding: '12px 8px' }}>{s.projects_used}</td>
                          <td style={{ padding: '12px 8px' }}>{s.ai_calls_used}</td>
                          <td style={{ padding: '12px 8px' }}>{s.exports_used}</td>
                          <td style={{ padding: '12px 8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            {s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : 'N/A'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 3. SYSTEM HEALTH TAB */}
            {activeTab === 'system' && systemStats && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '25px' }}>
                  {systemStats.system_perfect ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', borderRadius: '12px', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' }}>
                      <CheckCircle size={20} />
                      <span style={{ fontWeight: 700 }}>{isArabic ? 'حالة النظام: مثالية ومكتملة' : 'System Health: PERFECT'}</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', borderRadius: '12px', backgroundColor: 'rgba(245, 158, 11, 0.15)', color: 'var(--warning)' }}>
                      <AlertTriangle size={20} />
                      <span style={{ fontWeight: 700 }}>{isArabic ? 'حالة النظام: تتطلب بعض التهيئة' : 'System Health: gaps detected'}</span>
                    </div>
                  )}
                </div>

                {systemStats.analytics && (
                  <div style={{ marginBottom: '35px' }}>
                    <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>📊 {isArabic ? 'إحصائيات النشاط والزوار' : 'Live Activity & Visitor Analytics'}</h4>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px', marginBottom: '20px' }}>
                      <div style={{ padding: '18px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', borderTop: '3px solid #3b82f6' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>{isArabic ? 'إجمالي الزوار (24س)' : 'Total Visitors (24h)'}</p>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: 800 }}>{systemStats.analytics.visitors_24h ?? 0}</h3>
                      </div>
                      <div style={{ padding: '18px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', borderTop: '3px solid #8b5cf6' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>{isArabic ? 'زوار فريدين (IPs)' : 'Unique Visitor IPs'}</p>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: 800 }}>{systemStats.analytics.unique_visitors_24h ?? 0}</h3>
                      </div>
                      <div style={{ padding: '18px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', borderTop: '3px solid var(--primary)' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>{isArabic ? 'تسجيلات الدخول اليوم' : 'Logins Today'}</p>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: 800 }}>{systemStats.analytics.logins_today}</h3>
                      </div>
                      <div style={{ padding: '18px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', borderTop: '3px solid var(--success)' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>{isArabic ? 'المستخدمين الجدد اليوم' : 'New Registrations Today'}</p>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: 800 }}>{systemStats.analytics.regs_today}</h3>
                      </div>
                      <div style={{ padding: '18px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', borderTop: '3px solid var(--warning)' }}>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '5px' }}>{isArabic ? 'مشاريع آخر 12 ساعة' : 'Projects Last 12h'}</p>
                        <h3 style={{ fontSize: '1.8rem', fontWeight: 800 }}>{systemStats.analytics.projects_12h}</h3>
                      </div>
                    </div>

                    <h5 style={{ fontWeight: 700, marginBottom: '10px' }}>{isArabic ? 'أحدث المشاريع المعالجة' : 'Recent Projects'}</h5>
                    {systemStats.analytics.recent_projects && systemStats.analytics.recent_projects.length > 0 ? (
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: isArabic ? 'right' : 'left' }}>
                          <thead>
                            <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                              <th style={{ padding: '10px 8px', fontWeight: 700 }}>ID</th>
                              <th style={{ padding: '10px 8px', fontWeight: 700 }}>{isArabic ? 'المستخدم' : 'User'}</th>
                              <th style={{ padding: '10px 8px', fontWeight: 700 }}>{isArabic ? 'المشروع' : 'Project'}</th>
                              <th style={{ padding: '10px 8px', fontWeight: 700 }}>{isArabic ? 'الحالة' : 'Status'}</th>
                              <th style={{ padding: '10px 8px', fontWeight: 700 }}>{isArabic ? 'تاريخ الإنشاء' : 'Created At'}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {systemStats.analytics.recent_projects.map(p => (
                              <tr key={p.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                <td style={{ padding: '10px 8px' }}>#{p.id}</td>
                                <td style={{ padding: '10px 8px', fontWeight: 600 }}>{p.user_email}</td>
                                <td style={{ padding: '10px 8px' }}>{p.name}</td>
                                <td style={{ padding: '10px 8px' }}>
                                  <span style={{
                                    padding: '3px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 700,
                                    background: p.status === 'completed' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)',
                                    color: p.status === 'completed' ? 'var(--success)' : 'var(--warning)'
                                  }}>{p.status}</span>
                                </td>
                                <td style={{ padding: '10px 8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                  {new Date(p.created_at).toLocaleString()}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد مشاريع حديثة.' : 'No recent projects.'}</p>
                    )}
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '30px' }}>
                  <div>
                    <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>🔑 {isArabic ? 'المتغيرات البيئية' : 'Environment Settings'}</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {Object.entries(systemStats.env_status).map(([env, configured]) => (
                        <div key={env} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                          <code style={{ fontSize: '0.85rem' }}>{env}</code>
                          <span style={{ fontWeight: 700, color: configured ? 'var(--success)' : 'var(--error)' }}>
                            {configured ? (isArabic ? '🟢 مهيأ' : 'Configured') : (isArabic ? '🔴 مفقود' : 'Missing')}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>🔌 {isArabic ? 'اتصال المحركات وقواعد البيانات' : 'Core Integration Pings'}</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <span>Database Connectivity (TiDB Cloud)</span>
                        <span style={{ fontWeight: 700, color: systemStats.db_ok ? 'var(--success)' : 'var(--error)' }}>
                          {systemStats.db_ok ? '🟢 Success' : `🔴 Failed (${systemStats.db_error})`}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <span>EasyOCR Fallback Local Engine</span>
                        <span style={{ fontWeight: 700, color: systemStats.ocr_ready ? 'var(--success)' : 'var(--error)' }}>
                          {systemStats.ocr_ready ? '🟢 Ready' : '🔴 Missing'}
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 15px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                        <span>PyMuPDF Blueprint Renderer</span>
                        <span style={{ fontWeight: 700, color: systemStats.pdf_ready ? 'var(--success)' : 'var(--error)' }}>
                          {systemStats.pdf_ready ? '🟢 Ready' : '🔴 Missing'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '25px 0' }} />

                <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>💾 {isArabic ? 'طبقة التخزين المؤقت للمخططات' : 'Storage & Caching Layer'}</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
                  <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginBottom: '5px' }}>Cache Folder Status</p>
                    <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{systemStats.cache.exists ? 'Created' : 'Not Found'}</h3>
                  </div>
                  <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginBottom: '5px' }}>Cached Blueprint extractions</p>
                    <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{systemStats.cache.count} files</h3>
                  </div>
                  <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center' }}>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginBottom: '5px' }}>Disk Storage Utilized</p>
                    <h3 style={{ fontSize: '1.4rem', fontWeight: 800 }}>{systemStats.cache.size_mb} MB</h3>
                  </div>
                </div>
              </div>
            )}

            {/* 4. AI MANAGER CHAT TAB */}
            {activeTab === 'chat' && (
              <div style={{ height: '500px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div style={{ overflowY: 'auto', flex: 1, padding: '10px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  {chatHistory.map((msg, idx) => (
                    <div key={idx} style={{
                      alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      maxWidth: '80%',
                      background: msg.role === 'user' ? 'var(--primary-glow)' : 'var(--bg-secondary)',
                      color: msg.role === 'user' ? 'var(--primary)' : 'var(--text-primary)',
                      padding: '12px 18px',
                      borderRadius: '12px',
                      border: '1px solid var(--border-color)',
                      whiteSpace: 'pre-line',
                      textAlign: 'left'
                    }}>
                      <div style={{ fontWeight: 700, fontSize: '0.75rem', marginBottom: '4px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                        {msg.role === 'user' ? 'Founder' : 'AI Supervisor'}
                      </div>
                      {msg.content}
                      {msg.action_result && (
                        <div style={{
                          marginTop: '10px',
                          padding: '8px 12px',
                          background: 'rgba(0,0,0,0.2)',
                          borderRadius: '6px',
                          fontSize: '0.82rem',
                          borderLeft: msg.action_result.success ? '3px solid var(--success)' : '3px solid var(--error)'
                        }}>
                          <strong style={{ display: 'block', color: msg.action_result.success ? 'var(--success)' : 'var(--error)' }}>
                            {msg.action_result.success ? 'Execution Success:' : 'Execution Failure:'}
                          </strong>
                          {msg.action_result.message}
                          {msg.action_result.data && (
                            <pre style={{ overflowX: 'auto', marginTop: '5px', fontSize: '0.75rem', color: '#64748b' }}>
                              {JSON.stringify(msg.action_result.data, null, 2)}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {chatLoading && (
                    <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 18px', background: 'var(--bg-secondary)', borderRadius: '12px' }}>
                      <Loader size={16} className="spin-anim" />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>AI executing admin script...</span>
                    </div>
                  )}
                </div>
                
                <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '15px' }}>
                  <input
                    type="text"
                    className="form-input"
                    placeholder={isArabic ? 'اكتب أمر الصيانة أو السؤال هنا...' : 'Enter command for the AI manager...'}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    style={{ flex: 1 }}
                    disabled={chatLoading}
                  />
                  <button type="submit" className="btn btn-primary" style={{ padding: '10px 20px', gap: '8px' }} disabled={chatLoading}>
                    <Send size={16} />
                  </button>
                </form>
              </div>
            )}

            {/* 5. GLOBAL LEARNING TAB */}
            {activeTab === 'rules' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '8px' }}>
                  🧠 {isArabic ? 'مراجعة وتأكيد قواعد التعلم التلقائي' : 'Global AI Learning Queue'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '25px' }}>
                  {isArabic 
                    ? 'هنا يتم استعراض الكلمات الجمركية الجديدة وقواعد الربط المكتشفة من المستخدمين. اعتمادها يعممها كقواعد حصر عامة.'
                    : 'Approve or reject mapping requests submitted by users. Approved mappings apply globally.'}
                </p>

                <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>⏳ {isArabic ? 'القواعد المعلقة للمراجعة' : 'Pending Approvals'} ({rules.pending.length})</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginBottom: '30px' }}>
                  {rules.pending.length === 0 ? (
                    <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                      {isArabic ? 'قائمة القواعد المعلقة فارغة.' : 'No pending rules to review.'}
                    </div>
                  ) : (
                    rules.pending.map(r => (
                      <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '15px 20px', background: 'var(--bg-secondary)', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                        <div>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>User {r.user_id} mapped:</span>
                          <div style={{ fontWeight: 700, marginTop: '4px', fontSize: '0.98rem' }}>
                            "{r.original_text}" ➔ <span style={{ color: 'var(--primary)' }}>{r.mapped_category}</span>
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '10px' }}>
                          <button onClick={() => handleApproveRule(r.id)} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.82rem' }}>
                            {isArabic ? 'موافقة وتعميم' : 'Approve Global'}
                          </button>
                          <button onClick={() => handleRejectRule(r.id)} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.82rem', color: 'var(--error)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                            {isArabic ? 'رفض' : 'Reject'}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

                <h4 style={{ fontWeight: 700, marginBottom: '15px' }}>✅ {isArabic ? 'القواعد العالمية النشطة' : 'Active Global Mapping Rules'} ({rules.global.length})</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: isArabic ? 'right' : 'left' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid var(--border-color)' }}>
                        <th style={{ padding: '10px 8px', fontWeight: 700 }}>Original Phrase</th>
                        <th style={{ padding: '10px 8px', fontWeight: 700 }}>Mapped Category</th>
                        <th style={{ padding: '10px 8px', fontWeight: 700 }}>Date Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rules.global.map(gr => (
                        <tr key={gr.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                          <td style={{ padding: '10px 8px', fontWeight: 600 }}>"{gr.original_text}"</td>
                          <td style={{ padding: '10px 8px', color: 'var(--primary)' }}>{gr.mapped_category}</td>
                          <td style={{ padding: '10px 8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                            {new Date(gr.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 6. CUSTOMER COMPLAINTS TAB */}
            {activeTab === 'complaints' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '20px' }}>
                  🚨 {isArabic ? 'صندوق شكاوى العملاء' : 'Customer Support Escalated Complaints'}
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  {complaints.length === 0 ? (
                    <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', color: 'var(--text-secondary)' }}>
                      {isArabic ? 'لا توجد أي شكاوى معلقة.' : 'No customer complaints recorded.'}
                    </div>
                  ) : (
                    complaints.map(c => (
                      <div key={c.id} style={{
                        padding: '20px',
                        background: 'var(--bg-secondary)',
                        borderRadius: '12px',
                        border: '1px solid var(--border-color)',
                        borderLeft: c.status === 'open' ? '4px solid var(--error)' : '4px solid var(--success)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                          <div>
                            <span style={{ fontWeight: 700 }}>User: {c.user_email}</span>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', marginLeft: '15px' }}>
                              {new Date(c.created_at).toLocaleString()}
                            </span>
                          </div>
                          <span style={{
                            padding: '3px 8px',
                            borderRadius: '12px',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            background: c.status === 'open' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                            color: c.status === 'open' ? 'var(--error)' : 'var(--success)'
                          }}>{c.status}</span>
                        </div>
                        <p style={{ margin: '15px 0', fontSize: '0.92rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                          {c.complaint_text}
                        </p>
                        {c.status === 'open' && (
                          <button onClick={() => handleResolveComplaint(c.id)} className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.82rem' }}>
                            {isArabic ? 'تعليم كتم الحل بنجاح' : 'Mark Resolved'}
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* 7. TOOL FEEDBACK TAB */}
            {activeTab === 'feedback' && (
              <div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '20px' }}>
                  ⭐ {isArabic ? 'تقييمات المستخدمين لكل أداة' : 'User Ratings per Tool'}
                </h3>

                {/* Per-tool summary cards */}
                {feedback.summary && feedback.summary.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '15px', marginBottom: '30px' }}>
                    {feedback.summary.map(s => (
                      <div key={s.tool_name} style={{
                        padding: '18px',
                        background: 'var(--bg-secondary)',
                        borderRadius: '12px',
                        border: '1px solid var(--border-color)'
                      }}>
                        <div style={{ fontWeight: 800, fontSize: '1rem', marginBottom: '8px', color: 'var(--text-primary)' }}>{s.tool_name}</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
                          <span style={{ fontSize: '1.6rem', fontWeight: 800, color: '#eab308' }}>{Number(s.avg_rating).toFixed(2)}</span>
                          <span style={{ color: '#eab308', fontSize: '1.1rem' }}>★</span>
                          <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                            ({s.total} {isArabic ? 'تقييم' : 'ratings'})
                          </span>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem' }}>
                          <span style={{ color: 'var(--success)' }}>👍 {s.positive}</span>
                          <span style={{ color: 'var(--error)' }}>👎 {s.negative}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ padding: '20px', background: 'var(--bg-secondary)', borderRadius: '12px', textAlign: 'center', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                    {isArabic ? 'لا توجد تقييمات بعد.' : 'No feedback recorded yet.'}
                  </div>
                )}

                {/* Individual feedback list */}
                {feedback.items && feedback.items.length > 0 && (
                  <>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '15px' }}>
                      {isArabic ? 'كل التقييمات' : 'All Feedback'}
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {feedback.items.map(f => (
                        <div key={f.id} style={{
                          padding: '16px',
                          background: 'var(--bg-secondary)',
                          borderRadius: '12px',
                          border: '1px solid var(--border-color)',
                          borderLeft: f.rating >= 4 ? '4px solid var(--success)' : '4px solid var(--error)'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <span style={{ color: '#eab308', fontSize: '1rem', letterSpacing: '2px' }}>
                                {'★'.repeat(f.rating)}{'☆'.repeat(5 - f.rating)}
                              </span>
                              <span style={{
                                padding: '2px 10px', borderRadius: '10px', fontSize: '0.75rem', fontWeight: 700,
                                background: 'var(--primary-glow)', color: 'var(--primary)'
                              }}>{f.tool_name}</span>
                              <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>{f.project_name}</span>
                            </div>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                              {f.created_at ? new Date(f.created_at).toLocaleString() : ''}
                            </span>
                          </div>
                          {f.reason && (
                            <p style={{ margin: '8px 0 0', fontSize: '0.9rem', lineHeight: '1.5', color: 'var(--text-primary)' }}>
                              {f.reason}
                            </p>
                          )}
                          <div style={{ marginTop: '8px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                            {f.user_email || (isArabic ? 'مستخدم محذوف' : 'deleted user')}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
