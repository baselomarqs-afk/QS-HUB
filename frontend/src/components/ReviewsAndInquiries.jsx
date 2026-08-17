import React, { useState, useEffect } from 'react';
import { 
  Star, MessageSquare, Send, CheckCircle2, ShieldCheck, 
  ThumbsUp, Sparkles, Building2, User, Mail, HelpCircle, 
  Clock, AlertCircle, Filter, ArrowRight, ArrowLeft 
} from 'lucide-react';

export default function ReviewsAndInquiries({ isArabic, user, onBack, initialTab = 'reviews' }) {
  const [activeTab, setActiveTab] = useState(initialTab); // 'reviews' | 'inquiries'
  const [reviewsData, setReviewsData] = useState({ reviews: [], stats: { total_reviews: 0, avg_rating: 5.0 } });
  const [loadingReviews, setLoadingReviews] = useState(true);

  // Review Modal state
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewForm, setReviewForm] = useState({
    user_name: user?.name || '',
    user_role: '',
    company: '',
    rating: 5,
    review_title: '',
    review_text: ''
  });
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewSubmittedMsg, setReviewSubmittedMsg] = useState(null);

  // Inquiry Form state
  const [inquiryForm, setInquiryForm] = useState({
    name: user?.name || '',
    email: user?.email || '',
    subject: '',
    category: 'general',
    message: ''
  });
  const [submittingInquiry, setSubmittingInquiry] = useState(false);
  const [inquirySuccessMsg, setInquirySuccessMsg] = useState(null);
  const [inquiryErrorMsg, setInquiryErrorMsg] = useState(null);

  useEffect(() => {
    fetchPublicReviews();
  }, []);

  const fetchPublicReviews = async () => {
    try {
      setLoadingReviews(true);
      const res = await fetch('/api/reviews/public');
      if (res.ok) {
        const data = await res.json();
        setReviewsData(data);
      }
    } catch (err) {
      console.error('Failed to fetch reviews:', err);
    } finally {
      setLoadingReviews(false);
    }
  };

  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!reviewForm.user_name || !reviewForm.review_text) {
      alert(isArabic ? 'يرجى ملء الاسم ونص التقييم' : 'Please provide your name and review text.');
      return;
    }

    try {
      setSubmittingReview(true);
      const res = await fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reviewForm)
      });
      const data = await res.json();
      if (res.ok) {
        setReviewSubmittedMsg(
          isArabic 
            ? 'شكراً لك! تم إرسال تقييمك بنجاح وسيتم نشره بعد مراجعة الإدارة.' 
            : 'Thank you! Your review has been submitted and will appear publicly after admin approval.'
        );
        setReviewForm({
          user_name: user?.name || '',
          user_role: '',
          company: '',
          rating: 5,
          review_title: '',
          review_text: ''
        });
      } else {
        alert(data.detail || (isArabic ? 'حدث خطأ أثناء إرسال التقييم' : 'Error submitting review.'));
      }
    } catch (err) {
      console.error(err);
      alert(isArabic ? 'فشل الاتصال بالخادم' : 'Connection failed.');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleInquirySubmit = async (e) => {
    e.preventDefault();
    setInquirySuccessMsg(null);
    setInquiryErrorMsg(null);

    if (!inquiryForm.email || !inquiryForm.subject || !inquiryForm.message) {
      setInquiryErrorMsg(isArabic ? 'يرجى ملء جميع الحقول المطلوبة' : 'Please fill in all required fields.');
      return;
    }

    try {
      setSubmittingInquiry(true);
      const res = await fetch('/api/inquiries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(inquiryForm)
      });
      const data = await res.json();
      if (res.ok) {
        setInquirySuccessMsg(
          isArabic 
            ? 'تم استلام استفسارك بنجاح! سيقوم فريق الدعم الهندسي بالرد عليك عبر البريد الإلكتروني في أقرب وقت.' 
            : 'Your inquiry has been received! Our engineering support team will respond via email shortly.'
        );
        setInquiryForm({
          name: user?.name || '',
          email: user?.email || '',
          subject: '',
          category: 'general',
          message: ''
        });
      } else {
        setInquiryErrorMsg(data.detail || (isArabic ? 'حدث خطأ أثناء إرسال الاستفسار' : 'Failed to send inquiry.'));
      }
    } catch (err) {
      console.error(err);
      setInquiryErrorMsg(isArabic ? 'فشل الاتصال بالخادم' : 'Server connection failed.');
    } finally {
      setSubmittingInquiry(false);
    }
  };

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: '30px 20px',
      direction: isArabic ? 'rtl' : 'ltr',
      textAlign: isArabic ? 'right' : 'left',
      color: 'var(--text-primary)',
      fontFamily: 'var(--font-main)'
    }}>
      
      {/* Top Header & Navigation */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '35px',
        flexWrap: 'wrap',
        gap: '15px'
      }}>
        <div>
          {onBack && (
            <button 
              onClick={onBack}
              className="btn btn-secondary" 
              style={{ padding: '6px 14px', fontSize: '0.85rem', marginBottom: '12px', gap: '6px' }}
            >
              {isArabic ? <ArrowRight size={15} /> : <ArrowLeft size={15} />}
              {isArabic ? 'العودة للوحة التحكم' : 'Back to Dashboard'}
            </button>
          )}
          <h1 style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
            {isArabic ? 'المراجعات والاستفسارات' : 'Reviews & Inquiries Hub'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '6px' }}>
            {isArabic 
              ? 'آراء المهندسين والمستخدمين وتواصل الدعم الفني المباشر' 
              : 'Verified engineer testimonials, customer feedback, and official inquiry desk'}
          </p>
        </div>

        {/* Tab Toggle */}
        <div style={{
          display: 'flex',
          background: 'var(--bg-secondary)',
          padding: '5px',
          borderRadius: '14px',
          border: '1px solid var(--border-color)',
          gap: '6px'
        }}>
          <button
            onClick={() => setActiveTab('reviews')}
            style={{
              padding: '10px 22px',
              borderRadius: '10px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.9rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s',
              background: activeTab === 'reviews' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'reviews' ? 'white' : 'var(--text-secondary)'
            }}
          >
            <Star size={16} />
            {isArabic ? 'آراء وتقييمات العملاء' : 'Reviews & Testimonials'}
          </button>
          <button
            onClick={() => setActiveTab('inquiries')}
            style={{
              padding: '10px 22px',
              borderRadius: '10px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: '0.9rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s',
              background: activeTab === 'inquiries' ? 'var(--primary)' : 'transparent',
              color: activeTab === 'inquiries' ? 'white' : 'var(--text-secondary)'
            }}
          >
            <MessageSquare size={16} />
            {isArabic ? 'إرسال استفسار / دعم' : 'Send Inquiry / Support'}
          </button>
        </div>
      </div>

      {/* ────────────────────────────────────────────────────────── */}
      {/* 1. REVIEWS SECTION */}
      {/* ────────────────────────────────────────────────────────── */}
      {activeTab === 'reviews' && (
        <div>
          {/* Top KPI Showcase Banner */}
          <div className="glass-card" style={{
            padding: '30px',
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(16, 185, 129, 0.05) 100%)',
            marginBottom: '35px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '20px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
              <div style={{
                width: '75px',
                height: '75px',
                borderRadius: '18px',
                background: 'rgba(234, 179, 8, 0.15)',
                color: '#eab308',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '2rem',
                fontWeight: 900
              }}>
                {reviewsData.stats?.avg_rating || '5.0'}
              </div>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '6px' }}>
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star key={s} size={20} fill="#eab308" color="#eab308" />
                  ))}
                </div>
                <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {isArabic ? 'تقييم ممتاز وموثوق من مهندسي الإمارات' : 'Top-Rated by UAE Quantity Surveyors & Contractors'}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  {isArabic 
                    ? `بناءً على ${reviewsData.stats?.total_reviews || 5} تقييم معتمد من مكاتب الاستشارات والمقاولات`
                    : `Based on ${reviewsData.stats?.total_reviews || 5} verified reviews from consulting & contracting firms`}
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                setReviewSubmittedMsg(null);
                setShowReviewModal(true);
              }}
              className="btn btn-primary"
              style={{
                padding: '12px 24px',
                fontSize: '0.95rem',
                fontWeight: 700,
                borderRadius: '12px',
                boxShadow: '0 4px 15px rgba(59, 130, 246, 0.3)',
                gap: '8px'
              }}
            >
              <Sparkles size={18} />
              {isArabic ? 'أضف تقييمك وتجربتك' : 'Write a Review'}
            </button>
          </div>

          {/* Reviews Grid */}
          {loadingReviews ? (
            <div style={{ textAlign: 'center', padding: '50px', color: 'var(--text-secondary)' }}>
              <Clock size={30} className="spin" style={{ margin: '0 auto 15px' }} />
              <p>{isArabic ? 'جاري تحميل المراجعات...' : 'Loading verified reviews...'}</p>
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
              gap: '22px'
            }}>
              {reviewsData.reviews.map((r) => (
                <div 
                  key={r.id} 
                  className="glass-card"
                  style={{
                    padding: '24px',
                    borderRadius: '16px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-secondary)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    position: 'relative'
                  }}
                >
                  {r.is_featured === 1 && (
                    <div style={{
                      position: 'absolute',
                      top: '16px',
                      [isArabic ? 'left' : 'right']: '16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '3px 8px',
                      borderRadius: '10px',
                      fontSize: '0.72rem',
                      fontWeight: 800,
                      background: 'rgba(16, 185, 129, 0.15)',
                      color: 'var(--success)'
                    }}>
                      <ShieldCheck size={13} />
                      {isArabic ? 'مراجعة مميزة' : 'Featured'}
                    </div>
                  )}

                  <div>
                    {/* Stars */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '3px', marginBottom: '14px' }}>
                      {[...Array(r.rating || 5)].map((_, i) => (
                        <Star key={i} size={17} fill="#eab308" color="#eab308" />
                      ))}
                    </div>

                    {/* Title */}
                    {r.review_title && (
                      <h4 style={{
                        fontSize: '1.05rem',
                        fontWeight: 800,
                        marginBottom: '10px',
                        color: 'var(--text-primary)',
                        lineHeight: '1.4'
                      }}>
                        "{r.review_title}"
                      </h4>
                    )}

                    {/* Review text */}
                    <p style={{
                      fontSize: '0.92rem',
                      color: 'var(--text-secondary)',
                      lineHeight: '1.6',
                      marginBottom: '20px'
                    }}>
                      {r.review_text}
                    </p>
                  </div>

                  {/* Reviewer signature */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    paddingTop: '15px',
                    borderTop: '1px solid var(--border-color)'
                  }}>
                    <div style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, var(--primary) 0%, #6366f1 100%)',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 800,
                      fontSize: '1rem'
                    }}>
                      {r.user_name ? r.user_name.charAt(0).toUpperCase() : 'U'}
                    </div>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '0.92rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                        {r.user_name}
                        <CheckCircle2 size={14} color="var(--primary)" />
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        {r.user_role && <span>{r.user_role}</span>}
                        {r.company && <span> • {r.company}</span>}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* 2. INQUIRIES & CONTACT SECTION */}
      {/* ────────────────────────────────────────────────────────── */}
      {activeTab === 'inquiries' && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '30px',
          alignItems: 'start'
        }}>
          {/* Form Card */}
          <div className="glass-card" style={{
            padding: '35px 30px',
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            background: 'var(--bg-secondary)'
          }}>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: '8px', color: 'var(--text-primary)' }}>
              {isArabic ? 'إرسال استفسار أو طلب مخصص' : 'Submit an Inquiry / Request Support'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginBottom: '25px', lineHeight: '1.5' }}>
              {isArabic 
                ? 'لديك سؤال حول حصر مشروع معين، خطط الأسعار، أو واجهت أي استفسار تقني؟ أرسل لنا رسالتك مباشرة.' 
                : 'Have questions regarding custom project takeoffs, enterprise billing, or technical features? Send us a direct message.'}
            </p>

            {inquirySuccessMsg && (
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                background: 'rgba(16, 185, 129, 0.12)',
                border: '1px solid var(--success)',
                color: 'var(--success)',
                fontSize: '0.9rem',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <CheckCircle2 size={20} />
                <span>{inquirySuccessMsg}</span>
              </div>
            )}

            {inquiryErrorMsg && (
              <div style={{
                padding: '16px',
                borderRadius: '12px',
                background: 'rgba(239, 68, 68, 0.12)',
                border: '1px solid var(--error)',
                color: 'var(--error)',
                fontSize: '0.9rem',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}>
                <AlertCircle size={20} />
                <span>{inquiryErrorMsg}</span>
              </div>
            )}

            <form onSubmit={handleInquirySubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                  {isArabic ? 'الاسم الكامل (اختياري)' : 'Full Name (Optional)'}
                </label>
                <input
                  type="text"
                  value={inquiryForm.name}
                  onChange={(e) => setInquiryForm({ ...inquiryForm, name: e.target.value })}
                  placeholder={isArabic ? 'م. أحمد...' : 'Eng. Ahmed...'}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.92rem'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                  {isArabic ? 'البريد الإلكتروني *' : 'Email Address *'}
                </label>
                <input
                  type="email"
                  required
                  value={inquiryForm.email}
                  onChange={(e) => setInquiryForm({ ...inquiryForm, email: e.target.value })}
                  placeholder="name@company.com"
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.92rem'
                  }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                    {isArabic ? 'نوع الاستفسار' : 'Category'}
                  </label>
                  <select
                    value={inquiryForm.category}
                    onChange={(e) => setInquiryForm({ ...inquiryForm, category: e.target.value })}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.92rem'
                    }}
                  >
                    <option value="general">{isArabic ? 'استفسار عام' : 'General Inquiry'}</option>
                    <option value="pricing">{isArabic ? 'الاشتراكات والأسعار' : 'Pricing & Plans'}</option>
                    <option value="technical">{isArabic ? 'دعم فني ومخططات' : 'Technical Support'}</option>
                    <option value="feature_request">{isArabic ? 'اقتراح ميزة جديدة' : 'Feature Request'}</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                    {isArabic ? 'الموضوع *' : 'Subject *'}
                  </label>
                  <input
                    type="text"
                    required
                    value={inquiryForm.subject}
                    onChange={(e) => setInquiryForm({ ...inquiryForm, subject: e.target.value })}
                    placeholder={isArabic ? 'موضوع الاستفسار' : 'Inquiry subject'}
                    style={{
                      width: '100%',
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.92rem'
                    }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                  {isArabic ? 'نص الرسالة / الاستفسار *' : 'Inquiry Details / Message *'}
                </label>
                <textarea
                  required
                  rows={5}
                  value={inquiryForm.message}
                  onChange={(e) => setInquiryForm({ ...inquiryForm, message: e.target.value })}
                  placeholder={isArabic ? 'اكتب استفسارك بالتفصيل هنا...' : 'Describe your inquiry or requirement in detail...'}
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.92rem',
                    resize: 'vertical'
                  }}
                />
              </div>

              <button
                type="submit"
                disabled={submittingInquiry}
                className="btn btn-primary"
                style={{
                  padding: '14px',
                  borderRadius: '12px',
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  gap: '8px',
                  marginTop: '10px'
                }}
              >
                <Send size={17} />
                {submittingInquiry 
                  ? (isArabic ? 'جاري الإرسال...' : 'Sending...') 
                  : (isArabic ? 'إرسال الاستفسار الآن' : 'Submit Inquiry')}
              </button>
            </form>
          </div>

          {/* Information & SLA Sidecard */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="glass-card" style={{
              padding: '30px',
              borderRadius: '20px',
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)'
            }}>
              <div style={{
                width: '50px',
                height: '50px',
                borderRadius: '14px',
                background: 'rgba(59, 130, 246, 0.15)',
                color: 'var(--primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '18px'
              }}>
                <Mail size={24} />
              </div>
              <h4 style={{ fontSize: '1.15rem', fontWeight: 800, marginBottom: '10px', color: 'var(--text-primary)' }}>
                {isArabic ? 'الدعم الهندسي المباشر' : 'Direct Engineering Support'}
              </h4>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.6', marginBottom: '18px' }}>
                {isArabic
                  ? 'يقوم فريق المهندسين وحصر الكميات بمراجعة جميع الاستفسارات والرد خلال 24 ساعة كحد أقصى.'
                  : 'Our quantity surveyors and engineering support review all inquiries promptly with a maximum 24-hour turnaround.'}
              </p>
              <div style={{
                padding: '14px',
                background: 'var(--bg-primary)',
                borderRadius: '12px',
                border: '1px solid var(--border-color)',
                fontSize: '0.85rem'
              }}>
                <span style={{ color: 'var(--text-secondary)' }}>Email: </span>
                <a href="mailto:support@qshub.online" style={{ color: 'var(--primary)', fontWeight: 700, textDecoration: 'none' }}>
                  support@qshub.online
                </a>
              </div>
            </div>

            <div className="glass-card" style={{
              padding: '25px',
              borderRadius: '20px',
              border: '1px solid var(--border-color)',
              background: 'var(--bg-secondary)'
            }}>
              <h4 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '12px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <HelpCircle size={18} color="var(--primary)" />
                {isArabic ? 'أسئلة شائعة سريعة' : 'Quick FAQ'}
              </h4>
              <ul style={{ paddingLeft: isArabic ? '0' : '20px', paddingRight: isArabic ? '20px' : '0', color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.8' }}>
                <li>{isArabic ? 'هل الحصر متوافق مع بلديات الإمارات؟ نعم، يدعم دبي، الشارقة، عجمان وغيرها.' : 'Compatible with Dubai, Sharjah, & Ajman municipality plans.'}</li>
                <li>{isArabic ? 'هل يمكن تخصيص أسعار المواد؟ نعم، من تبويب أسعار السوق.' : 'Customizable unit rates from the Market Prices tab.'}</li>
                <li>{isArabic ? 'هل أول مشروع مجاني بالكامل؟ نعم، لكل أداة بدون بطاقة دفع.' : 'First project is completely free for all tools.'}</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────────────────────────── */}
      {/* WRITE REVIEW MODAL */}
      {/* ────────────────────────────────────────────────────────── */}
      {showReviewModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(5px)',
          zIndex: 9999,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '20px'
        }}>
          <div className="glass-card" style={{
            width: '100%',
            maxWidth: '560px',
            maxHeight: '90vh',
            overflowY: 'auto',
            background: 'var(--bg-secondary)',
            borderRadius: '20px',
            border: '1px solid var(--border-color)',
            padding: '30px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ fontSize: '1.3rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                {isArabic ? '⭐ شاركنا تقييمك ورأيك' : '⭐ Write Your Review'}
              </h3>
              <button 
                onClick={() => setShowReviewModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '1.2rem', fontWeight: 'bold' }}
              >
                ✕
              </button>
            </div>

            {reviewSubmittedMsg ? (
              <div style={{ textAlign: 'center', padding: '30px 10px' }}>
                <div style={{
                  width: '60px',
                  height: '60px',
                  borderRadius: '50%',
                  background: 'rgba(16, 185, 129, 0.15)',
                  color: 'var(--success)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 18px'
                }}>
                  <CheckCircle2 size={32} />
                </div>
                <h4 style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '10px' }}>
                  {isArabic ? 'تم الاستلام بنجاح!' : 'Review Submitted!'}
                </h4>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginBottom: '25px' }}>
                  {reviewSubmittedMsg}
                </p>
                <button 
                  onClick={() => setShowReviewModal(false)}
                  className="btn btn-primary"
                  style={{ padding: '10px 24px', borderRadius: '10px' }}
                >
                  {isArabic ? 'إغلاق' : 'Close'}
                </button>
              </div>
            ) : (
              <form onSubmit={handleReviewSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* Admin Approval Notice Banner */}
                <div style={{
                  padding: '12px 14px',
                  borderRadius: '10px',
                  background: 'rgba(59, 130, 246, 0.1)',
                  border: '1px solid rgba(59, 130, 246, 0.25)',
                  color: 'var(--primary)',
                  fontSize: '0.82rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <ShieldCheck size={18} />
                  <span>
                    {isArabic 
                      ? 'ملاحظة: سيتم نشر المراجعة في الموقع بعد مراجعة الإدارة.' 
                      : 'Notice: Your review will be published after verification by our moderation team.'}
                  </span>
                </div>

                {/* Rating Selector */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '8px' }}>
                    {isArabic ? 'التقييم بالنجوم *' : 'Your Rating *'}
                  </label>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        type="button"
                        key={star}
                        onClick={() => setReviewForm({ ...reviewForm, rating: star })}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          cursor: 'pointer',
                          padding: '4px',
                          transform: reviewForm.rating >= star ? 'scale(1.1)' : 'scale(1)',
                          transition: 'transform 0.15s'
                        }}
                      >
                        <Star 
                          size={28} 
                          fill={reviewForm.rating >= star ? '#eab308' : 'none'} 
                          color="#eab308" 
                        />
                      </button>
                    ))}
                  </div>
                </div>

                {/* Name */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                    {isArabic ? 'الاسم الكامل أو المسمى *' : 'Your Name *'}
                  </label>
                  <input
                    type="text"
                    required
                    value={reviewForm.user_name}
                    onChange={(e) => setReviewForm({ ...reviewForm, user_name: e.target.value })}
                    placeholder={isArabic ? 'م. باسل عمر' : 'Eng. John Smith'}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                      {isArabic ? 'المسمى الوظيفي' : 'Job Role'}
                    </label>
                    <input
                      type="text"
                      value={reviewForm.user_role}
                      onChange={(e) => setReviewForm({ ...reviewForm, user_role: e.target.value })}
                      placeholder={isArabic ? 'مهندس حصر كميات' : 'Senior QS'}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '10px',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                        fontSize: '0.9rem'
                      }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                      {isArabic ? 'الشركة / الإمارة' : 'Company / City'}
                    </label>
                    <input
                      type="text"
                      value={reviewForm.company}
                      onChange={(e) => setReviewForm({ ...reviewForm, company: e.target.value })}
                      placeholder={isArabic ? 'دبي، الإمارات' : 'Dubai, UAE'}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '10px',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                        fontSize: '0.9rem'
                      }}
                    />
                  </div>
                </div>

                {/* Review Title */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                    {isArabic ? 'عنوان موجز للتقييم' : 'Review Headline / Title'}
                  </label>
                  <input
                    type="text"
                    value={reviewForm.review_title}
                    onChange={(e) => setReviewForm({ ...reviewForm, review_title: e.target.value })}
                    placeholder={isArabic ? 'سرعة فائقة ودقة في حصر الخرسانات' : 'Fast and accurate takeoff'}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem'
                    }}
                  />
                </div>

                {/* Review Text */}
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '6px' }}>
                    {isArabic ? 'تفاصيل رأيك وتجربتك *' : 'Review Details *'}
                  </label>
                  <textarea
                    required
                    rows={4}
                    value={reviewForm.review_text}
                    onChange={(e) => setReviewForm({ ...reviewForm, review_text: e.target.value })}
                    placeholder={isArabic ? 'كيف ساعدتك المنصة في توفير الوقت أو التسعير...' : 'How did THE QS HUB help your estimation workflow...'}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '10px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem',
                      resize: 'vertical'
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                  <button
                    type="button"
                    onClick={() => setShowReviewModal(false)}
                    className="btn btn-secondary"
                    style={{ padding: '10px 18px', borderRadius: '10px' }}
                  >
                    {isArabic ? 'إلغاء' : 'Cancel'}
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="btn btn-primary"
                    style={{ padding: '10px 22px', borderRadius: '10px', fontWeight: 700 }}
                  >
                    {submittingReview 
                      ? (isArabic ? 'جاري الإرسال...' : 'Submitting...') 
                      : (isArabic ? 'إرسال التقييم' : 'Submit Review')}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
