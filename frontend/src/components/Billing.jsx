import React, { useState, useEffect } from 'react';
import { CreditCard, Check, AlertCircle, Sparkles } from 'lucide-react';

export default function Billing({ token, isArabic, user, onLogout }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState('');
  
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(user?.name || '');

  useEffect(() => {
    fetchSubscriptionDetails();
  }, []);

  const fetchSubscriptionDetails = async () => {
    setLoading(true);
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
    } finally {
      setLoading(false);
    }
  };

  const handleCheckout = async (tier) => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`/api/billing/checkout?tier=${tier}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) {
        window.open(data.checkout_url, '_blank');
      } else {
        throw new Error(data.detail || 'Could not generate checkout link.');
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveName = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/profile', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: editedName })
      });
      if (res.ok) {
        setIsEditingName(false);
        // Refresh page to get new user object globally
        window.location.reload();
      } else {
        const data = await res.json();
        setMessage(data.detail || 'Failed to update name');
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePortal = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`/api/billing/portal`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.portal_url) {
        window.open(data.portal_url, '_blank');
      } else {
        throw new Error(data.detail || 'Could not generate customer portal link.');
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!confirm(isArabic ? 'هل أنت متأكد من رغبتك في حذف الحساب نهائياً؟ هذا الإجراء لا يمكن التراجع عنه.' : 'Are you sure you want to delete your account permanently? This action cannot be undone.')) return;
    
    setDeleting(true);
    setMessage('');
    try {
      const res = await fetch(`/api/auth/account`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        if (onLogout) onLogout();
      } else {
        const data = await res.json();
        throw new Error(data.detail || 'Could not delete account.');
      }
    } catch (err) {
      setMessage(`Error: ${err.message}`);
      setDeleting(false);
    }
  };

  if (loading && !details) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <div className="spin-anim" style={{ width: '40px', height: '40px', border: '4px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 15px' }}></div>
        <p>{isArabic ? 'جاري تحميل تفاصيل الاشتراك...' : 'Loading subscription details...'}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      <div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 800, color: 'var(--primary)' }}>
          {isArabic ? 'الفواتير والاشتراكات' : 'Billing & Subscription'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          {isArabic ? 'إدارة الخطط، الاستهلاك الشهري، الدفع الإلكتروني وحدود الحساب.' : 'Manage plans, monthly usage, payment, and account limits.'}
        </p>
      </div>
      <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '20px 0' }} />

      {message && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(239,68,68,0.1)', color: 'var(--error)', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
          {message}
        </div>
      )}

      {details && (
        <>
          {/* User Profile Overview */}
          <div className="glass-panel" style={{ padding: '25px', marginBottom: '35px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              <div className="glass-card" style={{ borderLeft: '4px solid var(--primary)', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                    {isArabic ? 'اسم المستخدم' : 'User Name'}
                  </span>
                  {!isEditingName && (
                    <button onClick={() => setIsEditingName(true)} style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: '0.8rem' }}>
                      {isArabic ? 'تعديل' : 'Edit'}
                    </button>
                  )}
                </div>
                {isEditingName ? (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                    <input 
                      type="text" 
                      value={editedName} 
                      onChange={(e) => setEditedName(e.target.value)} 
                      style={{ flex: 1, padding: '6px 10px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                    />
                    <button onClick={handleSaveName} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                      {isArabic ? 'حفظ' : 'Save'}
                    </button>
                    <button onClick={() => setIsEditingName(false)} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
                      {isArabic ? 'إلغاء' : 'Cancel'}
                    </button>
                  </div>
                ) : (
                  <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '5px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {user?.name ? user.name : (user?.email ? (user.email.startsWith('eng.') ? user.email.split('@')[0] : `eng.${user.email.split('@')[0]}`) : 'eng.user')}
                  </h3>
                )}
              </div>
              <div className="glass-card" style={{ borderLeft: '4px solid var(--success)' }}>
                <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                  {isArabic ? 'البريد الإلكتروني' : 'Email'}
                </span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '5px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {user ? user.email : '...'}
                </h3>
              </div>
              <div className="glass-card" style={{ borderLeft: '4px solid var(--warning)' }}>
                <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                  {isArabic ? 'الباقة الحالية' : 'Current Plan'}
                </span>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '5px' }}>
                  {details.plan_name}
                </h3>
              </div>
            </div>

            {/* Account Actions */}
            <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap', marginTop: '10px' }}>
              <button 
                className="btn btn-primary" 
                onClick={() => {
                  document.getElementById('subscription-catalog').scrollIntoView({ behavior: 'smooth' });
                }}
                style={{ padding: '10px 20px', borderRadius: '8px', fontWeight: 600 }}
              >
                {isArabic ? 'ترقية الباقة' : 'Upgrade Plan'}
              </button>
              <button 
                className="btn btn-secondary" 
                onClick={handlePortal}
                style={{ padding: '10px 20px', borderRadius: '8px', fontWeight: 600, color: 'var(--warning)', borderColor: 'rgba(245, 158, 11, 0.3)' }}
              >
                {isArabic ? 'إلغاء الاشتراك' : 'Cancel Subscription'}
              </button>
              <button 
                className="btn btn-secondary" 
                onClick={handleDeleteAccount}
                disabled={deleting}
                style={{ padding: '10px 20px', borderRadius: '8px', fontWeight: 600, color: 'var(--error)', borderColor: 'rgba(239, 68, 68, 0.3)' }}
              >
                {deleting ? (isArabic ? 'جاري الحذف...' : 'Deleting...') : (isArabic ? 'حذف الحساب' : 'Delete Account')}
              </button>
            </div>
          </div>

          {/* Subscription Catalog */}
          <h3 id="subscription-catalog" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px', paddingTop: '20px' }}>
            {isArabic ? 'باقات الاشتراك المتاحة' : 'Available Subscription Packages'}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
            {details.plans_catalog.map((p) => {
              const showDiscount = p.tier === 2 || p.tier === 3;
              const discountedPrice = showDiscount ? p.price_aed / 2 : p.price_aed;
              return (
                <div key={p.tier} className="glass-card" style={{
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  border: '2px solid var(--primary)',
                  overflow: 'hidden'
                }}>
                  {showDiscount && (
                    <div style={{
                      position: 'absolute',
                      top: '12px',
                      right: isArabic ? 'auto' : '12px',
                      left: isArabic ? '12px' : 'auto',
                      backgroundColor: 'var(--error)',
                      color: 'white',
                      fontSize: '0.7rem',
                      fontWeight: 'bold',
                      padding: '2px 8px',
                      borderRadius: '10px'
                    }}>
                      🔥 50% OFF
                      <div style={{ fontSize: '0.55rem', textAlign: 'center', marginTop: '2px', opacity: 0.9 }}>Code: QTO2026</div>
                    </div>
                  )}

                  <div>
                    <h4 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '10px' }}>{p.name}</h4>
                    
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '15px' }}>
                      {showDiscount && (
                        <span style={{ fontSize: '0.9rem', textDecoration: 'line-through', color: 'var(--text-muted)' }}>
                          {p.price_aed} AED
                        </span>
                      )}
                      <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)' }}>
                        {discountedPrice} AED
                      </span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>/ mo</span>
                    </div>

                    <ul style={{ listStyle: 'none', padding: 0, margin: '20px 0', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.88rem' }}>
                      <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={14} color="var(--success)" />
                        <span>{isArabic ? `حصر المشاريع: ${p.projects_limit}` : `Projects Takeoffs: ${p.projects_limit}`}</span>
                      </li>
                      <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={14} color="var(--success)" />
                        <span>{isArabic ? 'ذكاء اصطناعي للرؤية والمعادلات' : 'AI Vision & Equations'}</span>
                      </li>
                      <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={14} color="var(--success)" />
                        <span>{isArabic ? 'تقارير Excel و PDF منسقة' : 'Formatted Excel & PDF exports'}</span>
                      </li>
                    </ul>
                  </div>

                  <button 
                    className={`btn ${p.tier === details.plan_tier ? 'btn-secondary' : 'btn-primary'}`} 
                    style={{ width: '100%' }}
                    onClick={() => handleCheckout(p.tier)}
                    disabled={p.tier === details.plan_tier}
                  >
                    {p.tier === details.plan_tier 
                      ? (isArabic ? 'الباقة الحالية' : 'Current Plan') 
                      : (isArabic ? `اختر باقة ${p.name}` : `Select ${p.name}`)}
                  </button>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
