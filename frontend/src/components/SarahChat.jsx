// نافذة خدمة العملاء — Official Customer Support widget for THE QS HUB.
// Account-aware (reads THIS user's real plans/credits/projects across all 3 tools),
// multi-turn memory, zero personal alias, and real ticket escalation to Admin.
import { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, X, Headset, Trash2 } from 'lucide-react';

export default function CustomerSupportChat({ token, isArabic }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const welcomeMsg = {
    sender: 'assistant',
    message: isArabic
      ? 'أهلاً بك في **خدمة عملاء THE QS HUB** 👋\nكيف يمكننا مساعدتك اليوم؟ يمكنك الاستفسار عن اشتراكك ورصيد مشاريعك، أو طريقة استخدام أدوات حصر الكميات والجدول الزمني والتدفق النقدي، أو الإبلاغ عن أي مشكلة.'
      : 'Welcome to **THE QS HUB Customer Support** 👋\nHow can we help you today? Ask about your active plans & remaining projects, how to use QTO / Work Programme / Cash Flow, or report an issue.',
  };

  useEffect(() => {
    if (!isOpen || !token) return;
    let active = true;
    (async () => {
      try {
        const res = await fetch('/api/agents/history?role=cc', {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (!active) return;
        if (res.ok) {
          setMessages(data.length === 0 ? [welcomeMsg] : data);
        }
      } catch (err) {
        console.error(err);
      }
    })();
    return () => { active = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, token, isArabic]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const sendMessage = async (text) => {
    const userMsg = (text ?? input).trim();
    if (!userMsg || loading) return;

    if (text === undefined) setInput('');
    setMessages((prev) => [...prev, { sender: 'user', message: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch('/api/agents/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ prompt: userMsg, role: 'cc' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to reply.');
      setMessages((prev) => [...prev, { sender: 'assistant', message: data.reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { sender: 'assistant', message: `${isArabic ? 'عذراً:' : 'Error:'} ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    try {
      await fetch('/api/agents/history?role=cc', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* ignore */ }
    setMessages([welcomeMsg]);
  };

  const quickActions = isArabic
    ? [
        { label: '📊 رصيدي واشتراكي', q: 'ما هي حالة اشتراكي الحالية وكم مشروع متبقٍ لي في كل أداة؟' },
        { label: '🛠️ شرح الأدوات الـ 3', q: 'كيف أستخدم أدوات حصر الكميات والجدول الزمني والتدفق النقدي؟' },
        { label: '🚨 الإبلاغ عن مشكلة', q: 'لدي مشكلة أرغب في فتح تذكرة دعم فني لها.' },
      ]
    : [
        { label: '📊 My Plan & Credits', q: 'What is my current subscription status and how many projects do I have left per tool?' },
        { label: '🛠️ How the 3 Tools Work', q: 'How do QTO Workflow, Work Programme, and Cash Flow work?' },
        { label: '🚨 Report an Issue', q: 'I have an issue and want to log a support ticket.' },
      ];

  return (
    <div style={{ position: 'fixed', bottom: '28px', right: '28px', zIndex: 999999, fontFamily: 'var(--font-main)' }}>
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          title={isArabic ? 'خدمة العملاء' : 'Customer Support'}
          style={{
            width: '62px',
            height: '62px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--primary), var(--primary-hover))',
            color: 'white',
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 8px 24px rgba(37, 99, 235, 0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 0.2s ease',
          }}
          onMouseEnter={(e) => { e.currentTarget.style.transform = 'scale(1.08) translateY(-3px)'; }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
        >
          <MessageCircle size={27} />
        </button>
      )}

      {isOpen && (
        <div className="glass-panel" style={{
          width: '375px',
          maxWidth: 'calc(100vw - 32px)',
          height: '530px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 12px 36px rgba(0,0,0,0.2)',
          overflow: 'hidden',
          animation: 'fadeInUp 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
        }}>
          {/* Header */}
          <div style={{
            padding: '14px 18px',
            background: 'linear-gradient(135deg, var(--primary), var(--primary-hover))',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '36px', height: '36px', borderRadius: '50%',
                backgroundColor: 'rgba(255,255,255,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Headset size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '0.96rem', fontWeight: 700 }}>
                  {isArabic ? 'خدمة العملاء' : 'Customer Support'}
                </h4>
                <span style={{ fontSize: '0.74rem', opacity: 0.85 }}>
                  {isArabic ? 'دعم مباشر لحسابك والأدوات' : 'THE QS HUB Live Help Desk'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                onClick={handleClear}
                title={isArabic ? 'محادثة جديدة' : 'Clear Chat'}
                style={{ background: 'transparent', border: 'none', color: 'rgba(255,255,255,0.85)', cursor: 'pointer', padding: 4 }}
              >
                <Trash2 size={16} />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 4 }}
              >
                <X size={20} />
              </button>
            </div>
          </div>

          {/* Quick help chips */}
          <div style={{ padding: '8px 12px', display: 'flex', flexWrap: 'wrap', gap: 6, background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-color)', direction: isArabic ? 'rtl' : 'ltr' }}>
            {quickActions.map((qa, i) => (
              <button
                key={i}
                type="button"
                disabled={loading}
                onClick={() => sendMessage(qa.q)}
                style={{
                  fontSize: '0.72rem', padding: '4px 9px', borderRadius: 14,
                  border: '1px solid var(--border-color)', background: 'var(--bg-primary)',
                  color: 'var(--text-primary)', cursor: 'pointer',
                }}
              >
                {qa.label}
              </button>
            ))}
          </div>

          {/* Messages body */}
          <div style={{
            flex: 1,
            padding: '16px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            backgroundColor: 'var(--bg-primary)',
          }}>
            {messages.map((msg, i) => {
              const isUser = msg.sender === 'user';
              return (
                <div
                  key={i}
                  style={{
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '84%',
                    backgroundColor: isUser ? 'var(--primary)' : 'var(--bg-secondary)',
                    color: isUser ? 'white' : 'var(--text-primary)',
                    padding: '10px 14px',
                    borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                    fontSize: '0.86rem',
                    lineHeight: '1.5',
                    whiteSpace: 'pre-wrap',
                    border: isUser ? 'none' : '1px solid var(--border-color)',
                    textAlign: isArabic ? 'right' : 'left',
                    direction: isArabic ? 'rtl' : 'ltr',
                  }}
                >
                  {msg.message}
                </div>
              );
            })}

            {loading && (
              <div style={{
                alignSelf: 'flex-start',
                backgroundColor: 'var(--bg-secondary)',
                padding: '12px 16px',
                borderRadius: '16px 16px 16px 2px',
                border: '1px solid var(--border-color)',
                display: 'flex', gap: '4px', alignItems: 'center',
              }}>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out' }}></span>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out 0.2s' }}></span>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out 0.4s' }}></span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Form input */}
          <form onSubmit={(e) => { e.preventDefault(); sendMessage(); }} style={{
            padding: '12px 14px',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            gap: '8px',
            backgroundColor: 'var(--bg-secondary)',
          }}>
            <input
              type="text"
              className="form-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isArabic ? 'اكتب استفسارك لخدمة العملاء...' : 'Ask Customer Support...'}
              style={{ flex: 1, padding: '9px 14px', borderRadius: '24px' }}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !input.trim()}
              style={{
                width: '40px', height: '40px', borderRadius: '50%',
                padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1.0); }
        }
      `}</style>
    </div>
  );
}
