import React, { useState, useEffect } from 'react';
import { CreditCard, Check, AlertCircle, Sparkles } from 'lucide-react';

export default function Billing({ token, isArabic }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

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
          {/* Current Plan & Usage Metrics */}
          <div className="glass-panel" style={{ padding: '25px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', marginBottom: '35px' }}>
            <div className="glass-card" style={{ borderLeft: '4px solid var(--primary)' }}>
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                {isArabic ? 'الباقة الحالية' : 'Current Plan'}
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>{details.plan_name}</h3>
              {details.subscription_status === 'active' ? (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
                  <span style={{ color: 'var(--success)', fontSize: '0.8rem', fontWeight: 700 }}>✓ Active</span>
                  <button 
                    className="btn btn-secondary" 
                    onClick={handlePortal} 
                    style={{ fontSize: '0.75rem', padding: '4px 10px', borderRadius: '6px' }}
                  >
                    {isArabic ? 'إدارة الاشتراك' : 'Manage Subscription'}
                  </button>
                </div>
              ) : (
                <div style={{ marginTop: '12px', padding: '10px', backgroundColor: 'rgba(0,0,0,0.1)', borderRadius: '6px' }}>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    {isArabic ? 'الحالة: غير نشط' : 'Status: Inactive'}
                  </span>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.4' }}>
                    {isArabic ? 'أنت غير مشترك حالياً في أي باقة. يرجى اختيار باقة من الأسفل لترقية حسابك.' : 'You are not subscribed to any plan. Please choose a package below to upgrade your account.'}
                  </p>
                </div>
              )}
            </div>

            <div className="glass-card">
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                {isArabic ? 'حصر المشاريع' : 'Projects Takeoffs'}
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
                {details.usage.projects} / {details.project_limit}
              </h3>
              {details.extra_projects > 0 && (
                <span style={{ color: 'var(--primary)', fontSize: '0.78rem', fontWeight: 600 }}>
                  (+{details.extra_projects} Add-ons)
                </span>
              )}
            </div>

            <div className="glass-card">
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                {isArabic ? 'استدعاءات الذكاء الاصطناعي' : 'AI Analysis Calls'}
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
                {details.usage.ai_calls}
              </h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {isArabic ? 'استهلاك هذا الشهر' : 'Usage this month'}
              </span>
            </div>

            <div className="glass-card">
              <span style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700 }}>
                {isArabic ? 'تصدير التقارير' : 'Reports Exports'}
              </span>
              <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '5px' }}>
                {details.usage.exports}
              </h3>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {isArabic ? 'ملفات Excel و PDF' : 'Excel & PDF files'}
              </span>
            </div>
          </div>

          {/* Add-on Extra Project Option */}
          {details.plan_tier > 0 && (
            <div className="glass-panel" style={{
              padding: '20px',
              backgroundColor: 'rgba(16, 185, 129, 0.04)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              marginBottom: '35px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderRadius: '12px'
            }}>
              <div>
                <h4 style={{ fontWeight: 700, color: 'var(--success)' }}>
                  {isArabic ? 'تحتاج لمشروع إضافي؟' : 'Need an extra project?'}
                </h4>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {isArabic ? 'يمكنك شراء مشروع حصر واحد إضافي لا تنتهي صلاحيته مقابل 50 درهم.' : 'Buy a single project allowance that never expires for 50 AED.'}
                </p>
              </div>
              <button className="btn btn-success" onClick={() => handleCheckout('addon')}>
                {isArabic ? 'شراء مشروع إضافي (+50 درهم)' : 'Buy +1 Project (50 AED)'}
              </button>
            </div>
          )}

          {/* Subscription Catalog */}
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px' }}>
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
