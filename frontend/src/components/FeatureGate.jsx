// بوابة الدفع للميزات — Per-project payment gate for the Work Programme and
// Cash Flow tools (50 AED each). Checks the user's feature credits from the API;
// if none, shows a bilingual payment box that opens the Dodo checkout. Children
// (the actual tool) render only when the user has access.
import React, { useState, useEffect } from 'react';
import { Lock, CheckCircle2, Loader2 } from 'lucide-react';

const PRICE_AED = 50;

export default function FeatureGate({ feature, token, isArabic, title, children }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [state, setState] = useState({ loading: true, access: false, credits: 0, error: '' });
  const [buying, setBuying] = useState(false);

  const checkAccess = async () => {
    setState((s) => ({ ...s, loading: true }));
    try {
      const res = await fetch(`/api/billing/feature-access?feature=${feature}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setState({ loading: false, access: !!data.access, credits: data.credits || 0, error: '' });
      } else {
        // Endpoint not ready / error — fail closed (locked) but allow retry.
        setState({ loading: false, access: false, credits: 0, error: '' });
      }
    } catch {
      setState({ loading: false, access: false, credits: 0, error: t('Could not check access.', 'تعذّر التحقق من الصلاحية.') });
    }
  };

  useEffect(() => { checkAccess(); /* eslint-disable-next-line */ }, [feature, token]);

  const buy = async () => {
    setBuying(true);
    try {
      const res = await fetch(`/api/billing/checkout?tier=${feature}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok && data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setState((s) => ({ ...s, error: data.detail || t('Checkout unavailable.', 'الدفع غير متاح حالياً.') }));
      }
    } catch {
      setState((s) => ({ ...s, error: t('Checkout failed.', 'فشل فتح صفحة الدفع.') }));
    } finally {
      setBuying(false);
    }
  };

  if (state.loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', color: 'var(--text-muted)', gap: 10 }}>
        <Loader2 size={20} className="spin" /> {t('Checking access…', 'جارٍ التحقق…')}
      </div>
    );
  }

  if (state.access) return children;

  return (
    <div style={{ maxWidth: 520, margin: '8vh auto', padding: '0 20px' }}>
      <div style={{
        background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: 16,
        padding: 32, textAlign: 'center',
      }}>
        <div style={{
          width: 64, height: 64, borderRadius: '50%', margin: '0 auto 18px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--primary-glow)', color: 'var(--primary)',
        }}>
          <Lock size={28} />
        </div>
        <h2 style={{ margin: '0 0 8px', color: 'var(--text-primary)', fontSize: '1.4rem' }}>{title}</h2>
        <p style={{ color: 'var(--text-secondary)', margin: '0 0 22px', lineHeight: 1.7 }}>
          {isArabic 
            ? 'هذه الميزة متاحة فقط للمستخدمين المشتركين.'
            : 'This feature requires a premium subscription.'}
        </p>

        {state.error && (
          <p style={{ color: 'var(--error)', fontSize: '0.85rem', marginBottom: 15 }}>{state.error}</p>
        )}

        <button 
          className="btn btn-primary" 
          style={{ width: '100%', padding: '12px 20px', fontWeight: 700 }}
          onClick={() => {
            window.location.hash = '#billing';
            window.dispatchEvent(new Event('hashchange'));
          }}
        >
          {isArabic ? 'الاشتراك الآن' : 'Subscribe Now'}
        </button>
      </div>
    </div>
  );
}
