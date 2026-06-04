import React, { useState } from 'react';
import { Sparkles, Zap, Smartphone, BarChart2, Globe, Bot, TrendingUp } from 'lucide-react';
import logoImg from '../assets/logo.png';
import { PrivacyModal, TermsModal, RefundModal } from './LegalModals';

export default function LandingPage({ isArabic, setIsArabic, onGetStarted }) {
  const [activeModal, setActiveModal] = useState(null);

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-main)',
      direction: isArabic ? 'rtl' : 'ltr',
      textAlign: isArabic ? 'right' : 'left',
      padding: '40px 20px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center'
    }}>
      
      {/* Navigation Header */}
      <header style={{
        width: '100%',
        maxWidth: '1200px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '50px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
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
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 800 }}>THE QS HUB</h2>
        </div>
        
        <div style={{ display: 'flex', gap: '15px' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => setIsArabic(!isArabic)}
            style={{ padding: '6px 12px', fontSize: '0.85rem', gap: '6px' }}
          >
            <Globe size={14} />
            {isArabic ? 'English' : 'العربية'}
          </button>
          <button className="btn btn-primary" onClick={onGetStarted} style={{ padding: '6px 16px', fontSize: '0.88rem' }}>
            {isArabic ? 'تسجيل الدخول' : 'Sign In'}
          </button>
        </div>
      </header>

      {/* Hero Banner Section */}
      <section className="glass-panel landing-hero" style={{
        width: '100%',
        maxWidth: '1000px',
        padding: '50px 25px',
        textAlign: 'center',
        background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(59, 130, 246, 0.1) 100%)',
        marginBottom: '50px',
        borderRadius: '24px',
        border: '1px solid var(--border-color)'
      }}>
        <img 
          src={logoImg} 
          alt="THE QS HUB Logo" 
          style={{
            width: '140px',
            height: '140px',
            borderRadius: '50%',
            objectFit: 'cover',
            margin: '0 auto 25px',
            boxShadow: '0 8px 30px rgba(59, 130, 246, 0.3)',
            border: '2px solid rgba(59, 130, 246, 0.4)',
            display: 'block'
          }} 
        />
        
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: '3.2rem',
          fontWeight: 800,
          color: '#3b82f6',
          lineHeight: '1.2',
          marginBottom: '15px',
          letterSpacing: '-0.02em'
        }}>
          THE QS HUB
        </h1>
        
        <p style={{
          color: 'var(--text-secondary)',
          fontSize: '1.25rem',
          maxWidth: '700px',
          margin: '0 auto 35px',
          lineHeight: '1.6',
          fontWeight: 500
        }}>
          {isArabic 
            ? 'مساعد ذكي مدعوم بالذكاء الاصطناعي لحصر كميات مشاريع الفلل في الإمارات وأكثر.'
            : 'AI powered assistant for quantity taking-off for villas project in the UAE & more.'}
        </p>

        <button className="btn btn-primary" onClick={onGetStarted} style={{ padding: '12px 35px', fontSize: '1.05rem', fontWeight: 700 }}>
          {isArabic ? 'ابدأ حصر مشاريعك الآن مجاناً' : 'Get Started for Free'}
        </button>
      </section>

      {/* Features Grid */}
      <section style={{ width: '100%', maxWidth: '1000px', marginBottom: '60px' }}>
        <h3 style={{
          fontSize: '1.8rem',
          fontWeight: 800,
          textAlign: 'center',
          marginBottom: '35px',
          fontFamily: 'var(--font-display)'
        }}>
          {isArabic ? 'المميزات الرئيسية للمنصة' : 'Core Platform Features'}
        </h3>
        
        <div className="features-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '25px' }}>
          
          {/* Card 1: UR QS ASSISTANT */}
          <div className="glass-card" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            textAlign: 'center', 
            padding: '35px 25px',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            background: 'var(--bg-secondary)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
          }}>
            <div style={{ 
              width: '56px', 
              height: '56px', 
              borderRadius: '14px', 
              backgroundColor: 'rgba(59, 130, 246, 0.15)', 
              color: '#3b82f6', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              marginBottom: '20px' 
            }}>
              <Zap size={28} fill="#3b82f6" />
            </div>
            <h4 style={{ fontWeight: 800, fontSize: '1.2rem', marginBottom: '15px', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              {isArabic ? 'مساعد حصر الكميات الذكي' : 'Ur QS Assistant'}
            </h4>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              {isArabic 
                ? 'وفر الوقت والجهد لإنجاز أكثر من 80% من جداول كميات مشاريع الفلل بمتوسط دقة يصل إلى 80%.'
                : 'Save time and efforts to complete +80% from your villa project BOQ with 80% average accuracy.'}
            </p>
          </div>

          {/* Card 2: VECTOR PDF DRAWINGS */}
          <div className="glass-card" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            textAlign: 'center', 
            padding: '35px 25px',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            background: 'var(--bg-secondary)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)'
          }}>
            <div style={{ 
              width: '56px', 
              height: '56px', 
              borderRadius: '14px', 
              backgroundColor: 'rgba(16, 185, 129, 0.15)', 
              color: '#10b981', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              marginBottom: '20px' 
            }}>
              <Bot size={28} />
            </div>
            <h4 style={{ fontWeight: 800, fontSize: '1.2rem', marginBottom: '15px', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              {isArabic ? 'مخططات PDF المتجهة' : 'Vector PDF Drawings'}
            </h4>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              {isArabic 
                ? 'تساعدك المنصة في استخراج وحصر أكثر من 50 بنداً إنشائياً ومعمارياً بالاعتماد الكامل على ملفات الـ PDF المتجهة.'
                : 'Helps you in extracting +50 items using (vector) PDF drawings.'}
            </p>
          </div>

          {/* Card 3: UNMATCHED SPEED & ACCURACY */}
          <div className="glass-card" style={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            textAlign: 'center', 
            padding: '35px 25px',
            border: '1px solid var(--border-color)',
            borderRadius: '16px',
            background: 'var(--bg-secondary)',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
            gridColumn: 'span 1'
          }}>
            <div style={{ 
              width: '56px', 
              height: '56px', 
              borderRadius: '14px', 
              backgroundColor: 'rgba(245, 158, 11, 0.15)', 
              color: '#f59e0b', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center', 
              marginBottom: '20px' 
            }}>
              <TrendingUp size={28} />
            </div>
            <h4 style={{ fontWeight: 800, fontSize: '1.2rem', marginBottom: '15px', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              {isArabic ? 'سرعة ودقة غير مسبوقة' : 'UNMATCHED SPEED & ACCURACY'}
            </h4>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <p>
                {isArabic 
                  ? 'احصل على جدول كمياتك (BOQ) جاهزاً في غضون دقائق، وليس أياماً.'
                  : 'Get your BOQ ready in minutes, not days.'}
              </p>
              <p>
                {isArabic 
                  ? 'تضمن لك المنصة تحسينات مستمرة في الدقة من مشروع إلى آخر.'
                  : 'Continuous accuracy improvements from one project to the next.'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Tiers Section */}
      <section style={{ width: '100%', maxWidth: '1000px', marginBottom: '60px' }}>
        <h3 style={{
          fontSize: '1.8rem',
          fontWeight: 800,
          textAlign: 'center',
          marginBottom: '35px',
          fontFamily: 'var(--font-display)'
        }}>
          {isArabic ? 'خطط الاشتراك والأسعار' : 'Pricing & Subscription'}
        </h3>
        
        <div className="pricing-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid var(--primary)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>TIER 1</span>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '10px 0 5px' }}>50 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? 'مشروع واحد' : '1 Project'}</h4>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid var(--primary)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>TIER 2</span>
            <div style={{ textDecoration: 'line-through', opacity: 0.5, fontSize: '0.9rem', marginTop: '5px' }}>120 AED</div>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '5px 0', color: 'var(--success)' }}>60 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? '3 مشاريع حصر' : '3 Projects'}</h4>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', fontSize: '0.75rem', fontWeight: 800, padding: '4px 8px', borderRadius: '10px', marginTop: '10px', display: 'inline-block' }}>
              🔥 {isArabic ? 'خصم 50% لأول شهر' : '50% OFF 1ST MONTH'}
            </div>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid var(--primary)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>TIER 3</span>
            <div style={{ textDecoration: 'line-through', opacity: 0.5, fontSize: '0.9rem', marginTop: '5px' }}>250 AED</div>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '5px 0', color: 'var(--success)' }}>125 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? '8 مشاريع حصر' : '8 Projects'}</h4>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', fontSize: '0.75rem', fontWeight: 800, padding: '4px 8px', borderRadius: '10px', marginTop: '10px', display: 'inline-block' }}>
              🔥 {isArabic ? 'خصم 50% لأول شهر' : '50% OFF 1ST MONTH'}
            </div>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid var(--primary)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>TIER 4</span>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '10px 0 5px' }}>500 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? '20 مشروع حصر' : '20 Projects'}</h4>
          </div>
        </div>
      </section>

      {/* Footer policy links */}
      <footer style={{
        width: '100%',
        maxWidth: '1200px',
        textAlign: 'center',
        padding: '30px 10px',
        borderTop: '1px solid var(--border-color)',
        marginTop: 'auto'
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginBottom: '15px' }}>
          <button onClick={() => setActiveModal('privacy')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)', textDecoration: 'none' }}>
            {isArabic ? 'سياسة الخصوصية' : 'Privacy Policy'}
          </button>
          <button onClick={() => setActiveModal('terms')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)', textDecoration: 'none' }}>
            {isArabic ? 'شروط الاستخدام' : 'Terms of Use'}
          </button>
          <button onClick={() => setActiveModal('refund')} style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)', textDecoration: 'none' }}>
            {isArabic ? 'سياسة الاسترداد' : 'Refund Policy'}
          </button>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          © 2026 THE QS HUB. All rights reserved. <br />
          For support, contact us at: support@qshub.ae
        </p>
      </footer>

      {/* Modals */}
      <PrivacyModal isOpen={activeModal === 'privacy'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
      <TermsModal isOpen={activeModal === 'terms'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
      <RefundModal isOpen={activeModal === 'refund'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
    </div>
  );
}
