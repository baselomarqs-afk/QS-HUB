import React, { useState, useEffect, useRef } from 'react';
import { CreditCard, Check, AlertCircle, Sparkles, Layers, Briefcase, DollarSign, CheckCircle, Loader } from 'lucide-react';

export default function Billing({ token, isArabic, user, onLogout, paymentSuccess, onPaymentSuccessHandled }) {
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [message, setMessage] = useState('');
  const [activeTab, setActiveTab] = useState('qto');

  // Payment activation state
  const [activating, setActivating] = useState(false);
  const [activated, setActivated] = useState(false);
  const [activatedPlan, setActivatedPlan] = useState(null);
  const pollRef = useRef(null);
  const pollCountRef = useRef(0);

  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(user?.name || '');

  // When paymentSuccess prop arrives, start polling for activation
  useEffect(() => {
    if (paymentSuccess) {
      setActivating(true);
      pollCountRef.current = 0;
      startPolling();
    }
  }, [paymentSuccess]);

  const startPolling = () => {
    // Poll every 2.5 seconds for up to 40 seconds (16 attempts)
    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > 16) {
        clearInterval(pollRef.current);
        // Even if not confirmed, refresh and stop
        setActivating(false);
        fetchSubscriptionDetails(activeTab);
        if (onPaymentSuccessHandled) onPaymentSuccessHandled();
        return;
      }
      try {
        // Check all 3 features for any new active subscription
        const features = ['qto', 'cashflow', 'programme'];
        for (const feat of features) {
          const res = await fetch(`/api/billing/subscription?feature=${feat}`, {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          const data = await res.json();
          if (res.ok && data.subscription_status === 'active' && data.plan_tier > 0) {
            // Found an active subscription!
            clearInterval(pollRef.current);
            setActivating(false);
            setActivated(true);
            setActivatedPlan({ feature: feat, plan: data.plan_name, tier: data.plan_tier, limit: data.project_limit });
            fetchSubscriptionDetails(feat);
            setActiveTab(feat);
            if (onPaymentSuccessHandled) onPaymentSuccessHandled();
            return;
          }
        }
      } catch (e) { /* ignore */ }
    }, 2500);
  };

  useEffect(() => {
    fetchSubscriptionDetails(activeTab);
  }, [activeTab]);

  const fetchSubscriptionDetails = async (feature) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/billing/subscription?feature=${feature}`, {
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

  const handleCheckout = async (tier, feature = 'qto') => {
    setLoading(true);
    setMessage('');
    try {
      const res = await fetch(`/api/billing/checkout?tier=${tier}&feature=${feature}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) {
        window.open(data.checkout_url, '_blank');
        // Show a tip to the user to come back after payment
        setMessage(isArabic
          ? '✅ تم فتح صفحة الدفع. بعد إتمام الدفع، ارجع لهذه الصفحة وسيتم تفعيل اشتراكك تلقائياً!'
          : '✅ Payment page opened. After completing payment, return here and your subscription will activate automatically!');
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

  // === ACTIVATING OVERLAY ===
  if (activating) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center', padding: '40px' }}>
        <div style={{ width: '80px', height: '80px', border: '6px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '30px' }} />
        <h2 style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '12px' }}>
          {isArabic ? '⚡ جاري تفعيل اشتراكك...' : '⚡ Activating your subscription...'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', maxWidth: '400px' }}>
          {isArabic
            ? 'تم استلام الدفع بنجاح. نحن الآن نفعّل اشتراكك ونفتح المشاريع لحسابك.'
            : 'Payment received. We are now activating your subscription and unlocking your projects.'}
        </p>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '16px' }}>
          {isArabic ? 'قد يستغرق هذا بضع ثوانٍ...' : 'This may take a few seconds...'}
        </p>
      </div>
    );
  }

  // === SUCCESS OVERLAY ===
  if (activated && activatedPlan) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center', padding: '40px' }}>
        <div style={{ width: '100px', height: '100px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--success), #059669)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '30px', boxShadow: '0 0 40px rgba(16, 185, 129, 0.4)' }}>
          <Check size={50} color="white" strokeWidth={3} />
        </div>
        <h2 style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--success)', marginBottom: '12px' }}>
          {isArabic ? '🎉 تم تفعيل اشتراكك!' : '🎉 Subscription Activated!'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.1rem', marginBottom: '8px' }}>
          {isArabic ? `خطتك الجديدة: ${activatedPlan.plan}` : `Your plan: ${activatedPlan.plan}`}
        </p>
        <p style={{ color: 'var(--text-primary)', fontSize: '1rem', fontWeight: 700, marginBottom: '30px' }}>
          {isArabic ? `تم فتح ${activatedPlan.limit} مشاريع لحسابك!` : `${activatedPlan.limit} projects unlocked for your account!`}
        </p>
        <button
          onClick={() => setActivated(false)}
          className="btn btn-primary"
          style={{ padding: '14px 40px', fontSize: '1rem', fontWeight: 700, borderRadius: '12px' }}
        >
          {isArabic ? 'ابدأ الآن! 🚀' : 'Start Now! 🚀'}
        </button>
      </div>
    );
  }

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
                  if (!details || !details.plans_catalog) return;
                  const nextPlan = details.plans_catalog.find(p => p.tier > details.plan_tier);
                  if (nextPlan) {
                    handleCheckout(nextPlan.tier, activeTab);
                  } else {
                    setMessage(isArabic ? 'أنت بالفعل على أعلى باقة متاحة.' : 'You are already on the highest available plan.');
                    document.getElementById('subscription-catalog')?.scrollIntoView({ behavior: 'smooth' });
                  }
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
          
          {/* Tabs for different products */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '25px', overflowX: 'auto', paddingBottom: '5px' }}>
            <button 
              onClick={() => setActiveTab('qto')}
              style={{
                padding: '12px 20px', borderRadius: '12px', border: 'none',
                background: activeTab === 'qto' ? 'var(--primary)' : 'var(--bg-secondary)',
                color: activeTab === 'qto' ? 'white' : 'var(--text-primary)',
                fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <Layers size={18} />
              {isArabic ? 'حصر الكميات (QTO)' : 'QTO Takeoff'}
            </button>
            <button 
              onClick={() => setActiveTab('programme')}
              style={{
                padding: '12px 20px', borderRadius: '12px', border: 'none',
                background: activeTab === 'programme' ? 'var(--primary)' : 'var(--bg-secondary)',
                color: activeTab === 'programme' ? 'white' : 'var(--text-primary)',
                fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <Briefcase size={18} />
              {isArabic ? 'برنامج العمل' : 'Work Programme'}
            </button>
            <button 
              onClick={() => setActiveTab('cashflow')}
              style={{
                padding: '12px 20px', borderRadius: '12px', border: 'none',
                background: activeTab === 'cashflow' ? 'var(--primary)' : 'var(--bg-secondary)',
                color: activeTab === 'cashflow' ? 'white' : 'var(--text-primary)',
                fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <DollarSign size={18} />
              {isArabic ? 'التدفق المالي' : 'Cash Flow'}
            </button>
          </div>

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
                  {p.tier === 1 && (
                    <div style={{
                      position: 'absolute',
                      top: '12px',
                      right: isArabic ? 'auto' : '12px',
                      left: isArabic ? '12px' : 'auto',
                      backgroundColor: 'var(--success)',
                      color: 'white',
                      fontSize: '0.85rem',
                      fontWeight: 'bold',
                      padding: '6px 14px',
                      borderRadius: '16px',
                      boxShadow: '0 4px 10px rgba(16, 185, 129, 0.3)',
                      zIndex: 10
                    }}>
                      🌟 {isArabic ? 'شهر مجاني!' : '1 Month Free!'}
                      <div style={{ fontSize: '0.75rem', textAlign: 'center', marginTop: '2px', opacity: 0.95 }}>
                        {isArabic ? 'مشروعين للشهر الأول' : '2 Projects 1st Month'}
                      </div>
                    </div>
                  )}

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
                    
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginBottom: '15px', flexWrap: 'wrap' }}>
                      {(showDiscount || p.tier === 1) && (
                        <span style={{ fontSize: '0.9rem', textDecoration: 'line-through', color: 'var(--text-muted)' }}>
                          {p.price_aed} AED
                        </span>
                      )}
                      <span style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)' }}>
                        {p.tier === 1 ? 'Free' : `${discountedPrice} AED`}
                      </span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {p.tier === 1 ? (isArabic ? 'للشهر الأول' : '1st month') : '/ mo'}
                      </span>
                    </div>

                    <ul style={{ listStyle: 'none', padding: 0, margin: '20px 0', display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.88rem' }}>
                      <li style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Check size={14} color="var(--success)" />
                        <span>
                          {activeTab === 'qto' && (isArabic ? 'حصر المشاريع: ' : 'Projects Takeoffs: ')}
                          {activeTab === 'programme' && (isArabic ? 'برامج العمل: ' : 'Programmes: ')}
                          {activeTab === 'cashflow' && (isArabic ? 'التدفقات المالية: ' : 'Cash Flows: ')}
                          
                          {p.tier === 1 ? (
                            <>
                              <span style={{ textDecoration: 'line-through', color: 'var(--text-muted)', margin: '0 4px' }}>{p.projects_limit}</span>
                              <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>2</span>
                            </>
                          ) : p.projects_limit}
                        </span>
                      </li>
                    </ul>
                  </div>

                  <button 
                    className={`btn ${p.tier === details.plan_tier ? 'btn-secondary' : 'btn-primary'}`} 
                    style={{ width: '100%' }}
                    onClick={() => handleCheckout(p.tier, activeTab)}
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
