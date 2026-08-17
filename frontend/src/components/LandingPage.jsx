import React, { useState, useEffect } from 'react';
import { Sparkles, Zap, Smartphone, BarChart2, Globe, Bot, TrendingUp, CalendarDays, Wallet, Star, MessageSquare, CheckCircle2, ShieldCheck, ArrowRight, ArrowLeft } from 'lucide-react';
import logoImg from '../assets/logo.png';
import { PrivacyModal, TermsModal, RefundModal } from './LegalModals';

export default function LandingPage({ isArabic, setIsArabic, onGetStarted, onOpenReviews }) {
  const [activeModal, setActiveModal] = useState(null);
  const [featuredReviews, setFeaturedReviews] = useState([]);

  useEffect(() => {
    fetch('/api/reviews/public?featured_only=true')
      .then(res => res.json())
      .then(data => {
        if (data.reviews && data.reviews.length > 0) {
          setFeaturedReviews(data.reviews);
        }
      })
      .catch(() => {});
  }, []);

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
        
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          {onOpenReviews && (
            <button
              className="btn btn-secondary"
              onClick={() => onOpenReviews('reviews')}
              style={{ padding: '6px 14px', fontSize: '0.85rem', gap: '6px' }}
            >
              <Star size={14} color="#eab308" />
              {isArabic ? 'المراجعات والدعم' : 'Reviews & Support'}
            </button>
          )}
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
            ? 'مساعد ذكي مدعوم بالذكاء الاصطناعي لحصر الكميات، والتدفق النقدي، والجداول الزمنية لمشاريع الفلل وفقاً لأنظمة واشتراطات دولة الإمارات.'
            : 'AI-powered assistant for quantity takeoff, cash flow & work programs for villa projects as per UAE regulations.'}
        </p>

        <button className="btn btn-primary" onClick={onGetStarted} style={{ padding: '12px 35px', fontSize: '1.05rem', fontWeight: 700 }}>
          {isArabic ? (
            <>ابدأ مشروعك الأول <span style={{ color: '#c62828', fontSize: '1.15em', fontWeight: '900' }}>مجاناً</span></>
          ) : (
            <>Start your 1st project <span style={{ color: '#c62828', fontSize: '1.15em', fontWeight: '900' }}>for free</span></>
          )}
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
          {isArabic ? 'من مهندسى حصر كميات الى مهندسئ حصر الكميات' : 'From quantity surveyors to the quantity surveyors'}
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
              {isArabic ? 'مساعد حصر الكميات الذكي' : 'Your QS Assistant'}
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
              <CalendarDays size={28} />
            </div>
            <h4 style={{ fontWeight: 800, fontSize: '1.2rem', marginBottom: '15px', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              {isArabic ? 'الجدول الزمني' : 'WORK PROGRAMME'}
            </h4>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
              {isArabic 
                ? 'توليد جداول زمنية ومخططات غانت والمراحل الرئيسية للمشروع تلقائياً من الكميات المحصورة.'
                : 'Generate work schedules, Gantt charts, and milestones automatically derived from measured quantities.'}
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
              <Wallet size={28} />
            </div>
            <h4 style={{ fontWeight: 800, fontSize: '1.2rem', marginBottom: '15px', textTransform: 'uppercase', color: 'var(--text-primary)' }}>
              {isArabic ? 'التدفق النقدي' : 'CASH FLOW'}
            </h4>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <p>
                {isArabic 
                  ? 'توقع التدفقات النقدية وجداول الدفعات وتوليد منحنيات S-Curve للتخطيط المالي للمشروع.'
                  : 'Forecast project cash flows, payment schedules, and generate financial S-curves for budget planning.'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Customer Testimonials Section */}
      <section style={{ width: '100%', maxWidth: '1050px', marginBottom: '65px' }}>
        <div style={{ textAlign: 'center', marginBottom: '35px' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 14px',
            borderRadius: '20px',
            background: 'rgba(234, 179, 8, 0.12)',
            color: '#eab308',
            fontWeight: 800,
            fontSize: '0.82rem',
            marginBottom: '10px'
          }}>
            <Star size={14} fill="#eab308" />
            {isArabic ? 'تقييم 5.0 من مهندسي ومقاولي الإمارات' : '5.0 Rating from UAE Engineers & Contractors'}
          </div>
          <h3 style={{
            fontSize: '2rem',
            fontWeight: 800,
            fontFamily: 'var(--font-display)',
            color: 'var(--text-primary)'
          }}>
            {isArabic ? 'ماذا يقول مهندسو حصر الكميات عنا؟' : 'What Estimators & Project Directors Say'}
          </h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginTop: '6px' }}>
            {isArabic ? 'تجارب حقيقية معتمدة من مكاتب الاستشارات وشركات المقاولات' : 'Verified testimonials from construction firms across Dubai, Abu Dhabi, Sharjah & Ajman'}
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))',
          gap: '20px',
          marginBottom: '25px'
        }}>
          {(featuredReviews.length > 0 ? featuredReviews.slice(0, 3) : [
            {
              id: 1,
              user_name: 'Eng. Tariq Al-Mansoor',
              user_role: 'Senior Quantity Surveyor',
              company: 'Dubai',
              rating: 5,
              review_title: 'Saved 3 days of manual takeoff',
              review_text: 'أداة استثنائية لحصر كميات الخرسانة والمباني والتشطيبات بدقة عالية ومقارنتها بأسعار السوق الإماراتي. تصدير BOQ Excel منسق جاهز للاستخدام مباشرة.'
            },
            {
              id: 2,
              user_name: 'Eng. Sarah Khalil',
              user_role: 'Commercial Manager',
              company: 'Abu Dhabi',
              rating: 5,
              review_title: 'Seamless integration with Work Programme',
              review_text: 'The automatic derivation of cash flow and Gantt charts from extracted BOQ quantities is a game changer for estimating tenders in the UAE.'
            },
            {
              id: 3,
              user_name: 'Eng. Mohammed Al-Hashimi',
              user_role: 'Project Director',
              company: 'Sharjah',
              rating: 5,
              review_title: 'دقة قراءة المخططات والـ Schedules',
              review_text: 'متوافق تماماً مع مخططات بلديات دبي والشارقة وعجمان. التعرف على جداول القواعد والميدات والأعمدة تم باحترافية عالية جداً.'
            }
          ]).map(r => (
            <div key={r.id} className="glass-card" style={{
              padding: '24px',
              borderRadius: '16px',
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginBottom: '12px' }}>
                  {[...Array(r.rating || 5)].map((_, i) => (
                    <Star key={i} size={16} fill="#eab308" color="#eab308" />
                  ))}
                </div>
                {r.review_title && (
                  <h4 style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '8px' }}>
                    "{r.review_title}"
                  </h4>
                )}
                <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '18px' }}>
                  {r.review_text}
                </p>
              </div>

              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                paddingTop: '12px',
                borderTop: '1px solid var(--border-color)'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, var(--primary) 0%, #6366f1 100%)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '0.85rem'
                }}>
                  {r.user_name ? r.user_name.charAt(0).toUpperCase() : 'E'}
                </div>
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.88rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    {r.user_name}
                    <CheckCircle2 size={13} color="var(--primary)" />
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {r.user_role} {r.company && `• ${r.company}`}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {onOpenReviews && (
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => onOpenReviews('reviews')}
              className="btn btn-secondary"
              style={{
                padding: '10px 22px',
                borderRadius: '12px',
                fontSize: '0.88rem',
                fontWeight: 700,
                gap: '8px'
              }}
            >
              <MessageSquare size={16} />
              {isArabic ? 'عرض جميع المراجعات أو إرسال استفسار' : 'View All Reviews & Submit Inquiry'}
              {isArabic ? <ArrowLeft size={15} /> : <ArrowRight size={15} />}
            </button>
          </div>
        )}
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
          <div className="glass-card" style={{ position: 'relative', textAlign: 'center', padding: '25px 15px', border: '2px solid #3b82f6', borderRadius: '12px' }}>
            <div style={{
              position: 'absolute',
              top: '-12px',
              left: '50%',
              transform: 'translateX(-50%)',
              backgroundColor: 'var(--success)',
              color: 'white',
              fontSize: '0.85rem',
              fontWeight: 'bold',
              padding: '6px 14px',
              borderRadius: '16px',
              whiteSpace: 'nowrap',
              boxShadow: '0 4px 10px rgba(16, 185, 129, 0.3)',
              zIndex: 10
            }}>
              🌟 {isArabic ? 'ابدأ مجاناً' : 'Start Free'}
            </div>

            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginTop: '10px' }}>FREE</span>

            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '5px 0', color: 'var(--primary)' }}>Free</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل أداة' : 'per tool'}</p>

            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
              <h4 style={{ fontWeight: 800, color: 'var(--success)' }}>{isArabic ? 'مشروعك الأول مجاناً' : 'Your 1st project free'}</h4>
            </div>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid #3b82f6', borderRadius: '12px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>TIER 1</span>
            <div style={{ textDecoration: 'line-through', opacity: 0.5, fontSize: '0.9rem', marginTop: '5px' }}>120 AED</div>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '5px 0', color: 'var(--success)' }}>60 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? '3 مشاريع حصر' : '3 Projects'}</h4>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', fontSize: '0.75rem', fontWeight: 800, padding: '4px 8px', borderRadius: '10px', marginTop: '10px', display: 'inline-block' }}>
              🔥 {isArabic ? 'خصم 50% لأول شهر' : '50% OFF 1ST MONTH'}
              <div style={{ fontSize: '0.65rem', marginTop: '2px', opacity: 0.9 }}>{isArabic ? 'كود الخصم: QTO2026' : 'Code: QTO2026'}</div>
            </div>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid #3b82f6', borderRadius: '12px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>TIER 2</span>
            <div style={{ textDecoration: 'line-through', opacity: 0.5, fontSize: '0.9rem', marginTop: '5px' }}>250 AED</div>
            <h3 style={{ fontSize: '2rem', fontWeight: 800, margin: '5px 0', color: 'var(--success)' }}>125 AED</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '15px' }}>{isArabic ? 'لكل شهر' : 'per month'}</p>
            <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '15px 0' }} />
            <h4 style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{isArabic ? '8 مشاريع حصر' : '8 Projects'}</h4>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', fontSize: '0.75rem', fontWeight: 800, padding: '4px 8px', borderRadius: '10px', marginTop: '10px', display: 'inline-block' }}>
              🔥 {isArabic ? 'خصم 50% لأول شهر' : '50% OFF 1ST MONTH'}
              <div style={{ fontSize: '0.65rem', marginTop: '2px', opacity: 0.9 }}>{isArabic ? 'كود الخصم: QTO2026' : 'Code: QTO2026'}</div>
            </div>
          </div>

          <div className="glass-card" style={{ textAlign: 'center', padding: '25px 15px', border: '2px solid #3b82f6', borderRadius: '12px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-muted)' }}>TIER 3</span>
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
          For support, contact us at: support@qshub.online
        </p>
      </footer>

      {/* Modals */}
      <PrivacyModal isOpen={activeModal === 'privacy'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
      <TermsModal isOpen={activeModal === 'terms'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
      <RefundModal isOpen={activeModal === 'refund'} onClose={() => setActiveModal(null)} isArabic={isArabic} />
    </div>
  );
}
