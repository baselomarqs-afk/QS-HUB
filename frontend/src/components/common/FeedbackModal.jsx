import React, { useState } from 'react';
import { Star, X } from 'lucide-react';

const FeedbackModal = ({ isOpen, onClose, toolName, projectName, isArabic, inline = false }) => {
  const [rating, setRating] = useState(0);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (!isOpen && !inline) return null;

  const handleSubmit = async () => {
    if (rating === 0) return;
    if (rating < 4 && !reason.trim()) {
      alert(isArabic ? 'يرجى كتابة سبب التقييم المنخفض لتحسين الخدمة.' : 'Please provide a reason for the low rating to help us improve.');
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          tool_name: toolName,
          project_name: projectName,
          rating: rating,
          reason: reason
        })
      });

      if (res.ok) {
        setSubmitted(true);
        setTimeout(() => {
          if (onClose) onClose();
          // reset state for next time
          setTimeout(() => {
            setRating(0);
            setHoveredRating(0);
            setReason('');
            setSubmitted(false);
          }, 500);
        }, 2000);
      } else {
        alert(isArabic ? 'فشل إرسال التقييم. حاول مرة أخرى.' : 'Failed to submit feedback. Try again.');
      }
    } catch (err) {
      console.error(err);
      alert(isArabic ? 'حدث خطأ غير متوقع.' : 'An unexpected error occurred.');
    } finally {
      setSubmitting(false);
    }
  };

  const cardContent = (
    <div style={{
      background: inline ? 'transparent' : 'var(--bg-secondary)', 
      border: inline ? 'none' : '1px solid var(--border-color)',
      borderRadius: '16px', padding: inline ? '30px 0' : '30px', width: '100%', maxWidth: inline ? '100%' : '400px',
      position: 'relative', textAlign: 'center', 
      boxShadow: inline ? 'none' : '0 20px 40px rgba(0,0,0,0.3)',
      marginTop: inline ? '40px' : '0'
    }}>
      {!inline && onClose && (
        <button 
          onClick={onClose}
          style={{ position: 'absolute', top: '15px', right: '15px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
        >
          <X size={20} />
        </button>
      )}

        {submitted ? (
          <div style={{ padding: '20px 0' }}>
            <h3 style={{ color: 'var(--success)', fontSize: '1.5rem', marginBottom: '10px' }}>
              {isArabic ? 'شكراً لك!' : 'Thank You!'}
            </h3>
            <p style={{ color: 'var(--text-secondary)' }}>
              {isArabic ? 'تم إرسال تقييمك بنجاح.' : 'Your feedback has been submitted successfully.'}
            </p>
          </div>
        ) : (
          <>
            <h3 style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '10px' }}>
              {isArabic ? 'قيّم تجربتك' : 'Rate Your Experience'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
              {isArabic 
                ? `كيف كانت تجربتك في أداة ${toolName} لمشروع ${projectName}؟`
                : `How was your experience using ${toolName} for project ${projectName}?`}
            </p>

            <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '20px' }}>
              {[1, 2, 3, 4, 5].map(star => (
                <button
                  key={star}
                  type="button"
                  style={{
                    background: 'transparent', border: 'none', cursor: 'pointer', padding: 0,
                    transition: 'transform 0.2s',
                    transform: (hoveredRating || rating) >= star ? 'scale(1.2)' : 'scale(1)'
                  }}
                  onMouseEnter={() => setHoveredRating(star)}
                  onMouseLeave={() => setHoveredRating(0)}
                  onClick={() => setRating(star)}
                >
                  <Star 
                    size={36} 
                    fill={(hoveredRating || rating) >= star ? '#eab308' : 'transparent'}
                    color={(hoveredRating || rating) >= star ? '#eab308' : 'var(--border-color)'} 
                  />
                </button>
              ))}
            </div>

            {rating > 0 && rating <= 3 && (
              <div style={{ marginBottom: '20px', textAlign: 'left' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                  {isArabic ? 'ما السبب؟ (إلزامي)' : 'Reason (Required)'}
                </label>
                <textarea 
                  className="form-input"
                  style={{ width: '100%', minHeight: '80px', resize: 'none', background: 'var(--bg-primary)' }}
                  placeholder={isArabic ? 'يرجى تزويدنا بتفاصيل المشكلة...' : 'Please tell us what went wrong...'}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px' }}>
              <button 
                className="btn btn-primary" 
                style={{ flex: 1 }}
                onClick={handleSubmit}
                disabled={rating === 0 || submitting}
              >
                {submitting ? (isArabic ? 'جاري الإرسال...' : 'Submitting...') : (isArabic ? 'إرسال' : 'Submit')}
        )}
      </div>
    </div>
  );

  if (inline) return cardContent;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
      backgroundColor: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999
    }}>
      {cardContent}
    </div>
  );
};

export default FeedbackModal;
