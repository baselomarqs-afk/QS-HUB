import React from 'react';
import { X } from 'lucide-react';

const ModalBase = ({ isOpen, onClose, title, isArabic, children }) => {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: 'var(--bg-primary)',
        width: '100%',
        maxWidth: '800px',
        maxHeight: '90vh',
        borderRadius: '16px',
        border: '1px solid var(--border-color)',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
        direction: isArabic ? 'rtl' : 'ltr',
        textAlign: isArabic ? 'right' : 'left',
      }}>
        <div style={{
          padding: '20px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--text-primary)' }}>{title}</h2>
          <button 
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              padding: '5px',
              display: 'flex'
            }}
          >
            <X size={24} />
          </button>
        </div>
        
        <div style={{
          padding: '20px 30px',
          overflowY: 'auto',
          color: 'var(--text-secondary)',
          lineHeight: '1.7',
          fontSize: '0.95rem'
        }}>
          {children}
        </div>
        
        <div style={{
          padding: '20px',
          borderTop: '1px solid var(--border-color)',
          textAlign: isArabic ? 'left' : 'right'
        }}>
          <button className="btn btn-primary" onClick={onClose}>
            {isArabic ? 'إغلاق' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
};

export const PrivacyModal = ({ isOpen, onClose, isArabic }) => (
  <ModalBase 
    isOpen={isOpen} 
    onClose={onClose} 
    isArabic={isArabic} 
    title={isArabic ? 'سياسة الخصوصية' : 'Privacy Policy'}
  >
    {isArabic ? (
      <div>
        <p><strong>تاريخ آخر تحديث:</strong> مايو 2026</p>
        <p>توضح هذه السياسة كيفية جمع واستخدام وحماية بيانات المستخدمين داخل THE QS HUB.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>1. البيانات التي قد نجمعها</h3>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>البريد الإلكتروني وبيانات الحساب.</li>
          <li>ملفات PDF والمخططات التي يرفعها المستخدم.</li>
          <li>سجلات الاستخدام مثل عدد المشاريع وطلبات الذكاء الاصطناعي والتصدير.</li>
        </ul>

        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>2. مشاركة البيانات</h3>
        <p>لا يتم بيع بيانات المستخدمين أبداً. قد تتم مشاركة بيانات محدودة مع مزودي خدمات ضروريين مثل مزود الدفع Dodo Payments ومزود الذكاء الاصطناعي لمعالجة المخططات فقط.</p>
      </div>
    ) : (
      <div>
        <p><strong>Last Updated:</strong> May 2026</p>
        <p>This policy explains how we collect, use, and protect user data within THE QS HUB.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>1. Data We Collect</h3>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>Email and account details.</li>
          <li>PDF files and blueprints uploaded by the user.</li>
          <li>Usage logs like project count and AI requests.</li>
          <li>Payment history.</li>
        </ul>

        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>2. Data Sharing</h3>
        <p>We NEVER sell user data. Limited data may be shared with essential service providers like Dodo Payments for payments and AI providers solely to process drawings.</p>
      </div>

    )}
  </ModalBase>
);

export const TermsModal = ({ isOpen, onClose, isArabic }) => (
  <ModalBase 
    isOpen={isOpen} 
    onClose={onClose} 
    isArabic={isArabic} 
    title={isArabic ? 'شروط الاستخدام' : 'Terms of Use'}
  >
    {isArabic ? (
      <div>
        <p><strong>تاريخ آخر تحديث:</strong> مايو 2026</p>
        <p>باستخدام منصة THE QS HUB، يوافق المستخدم على هذه الشروط.</p>
        
        <h3 style={{color: 'var(--error)', marginTop:'20px'}}>إخلاء المسؤولية الهندسية</h3>
        <p>المخرجات الناتجة من المنصة هي مخرجات <strong>مساعدة وليست اعتماداً هندسياً نهائياً</strong>. يتحمل المستخدم، المهندس، أو مهندس الكميات كامل المسؤولية عن تدقيق واعتماد الكميات قبل استخدامها في العطاءات أو العقود المالية.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>حدود الدقة</h3>
        <p>تعتمد جودة النتائج على جودة ملفات PDF ووضوحها، وقد تحتوي النتائج على هلوسات ذكاء اصطناعي أو أخطاء تحتاج مراجعة.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>الاستخدام المحظور</h3>
        <p>يحظر رفع ملفات لا يملك المستخدم حقوقها، أو التحايل على حدود الاشتراك.</p>
      </div>
    ) : (
      <div>
        <p><strong>Last Updated:</strong> May 2026</p>
        <p>By using THE QS HUB, you agree to these terms.</p>
        
        <h3 style={{color: 'var(--error)', marginTop:'20px'}}>Engineering Disclaimer</h3>
        <p>The outputs generated by the platform are <strong>assistive and do NOT constitute final engineering approval</strong>. The user takes full responsibility for auditing the quantities before using them in tenders or contracts.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>Accuracy Limits</h3>
        <p>Output quality depends heavily on PDF quality. AI hallucinations or errors may occur and require human review.</p>
        
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>Prohibited Use</h3>
        <p>Do not upload files you do not own, or attempt to bypass subscription limits.</p>
      </div>
    )}
  </ModalBase>
);

export const RefundModal = ({ isOpen, onClose, isArabic }) => (
  <ModalBase 
    isOpen={isOpen} 
    onClose={onClose} 
    isArabic={isArabic} 
    title={isArabic ? 'سياسة الاسترداد' : 'Refund Policy'}
  >
    {isArabic ? (
      <div>
        <p><strong>تاريخ آخر تحديث:</strong> مايو 2026</p>
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>حالات الاسترداد</h3>
        <p>يمكن دراسة طلبات الاسترداد في الحالات التالية فقط:</p>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>تم خصم المبلغ مرتين عن طريق الخطأ التقني.</li>
          <li>فشل جوهري ومستمر في خوادم الخدمة منعك من استخدام الاشتراك بالكامل.</li>
        </ul>

        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>لا يوجد استرداد في الحالات التالية:</h3>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>استخدام المنصة الفعلي واستهلاك الحصص (المشاريع والذكاء الاصطناعي).</li>
          <li>الأخطاء الهندسية الناتجة عن عدم المراجعة البشرية للمخرجات.</li>
          <li>المخططات غير المقروءة أو المسدودة بخط اليد والتي فشل الذكاء في حلها.</li>
        </ul>
      </div>
    ) : (
      <div>
        <p><strong>Last Updated:</strong> May 2026</p>
        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>Refund Conditions</h3>
        <p>Refunds may only be considered if:</p>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>You were double-charged due to a technical error.</li>
          <li>A catastrophic platform failure prevented any usage of your subscription.</li>
        </ul>

        <h3 style={{color: 'var(--text-primary)', marginTop:'20px'}}>No Refunds for:</h3>
        <ul style={{paddingInlineStart: '20px'}}>
          <li>Consumed quotas (used AI tokens or created projects).</li>
          <li>Engineering losses due to failing to manually audit the AI outputs.</li>
          <li>Failure to parse illegible, hand-drawn, or extremely poor-quality blueprints.</li>
        </ul>
      </div>
    )}
  </ModalBase>
);
