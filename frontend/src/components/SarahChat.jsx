import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, X, Headset } from 'lucide-react';

export default function SarahChat({ token, isArabic }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (isOpen && token) {
      fetchChatHistory();
    }
  }, [isOpen]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const fetchChatHistory = async () => {
    try {
      const res = await fetch("/api/agents/history?role=cc", {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        if (data.length === 0) {
          setMessages([
            {
              sender: 'assistant',
              message: isArabic 
                ? "أهلاً بك! أنا سارة من فريق خدمة العملاء. كيف يمكنني مساعدتك اليوم؟" 
                : "Welcome! I am Sarah from Customer Support. How can I assist you today?"
            }
          ]);
        } else {
          setMessages(data);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages(prev => [...prev, { sender: 'user', message: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch("/api/agents/chat", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ prompt: userMsg, role: 'cc' })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to reply.');
      
      setMessages(prev => [...prev, { sender: 'assistant', message: data.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { sender: 'assistant', message: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div style={{ position: 'fixed', bottom: '30px', right: '30px', zIndex: 999999, fontFamily: 'var(--font-main)' }}>
      {/* Floating Action Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            width: '65px',
            height: '65px',
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
          onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.08) translateY(-3px)'}
          onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
        >
          <MessageCircle size={28} />
        </button>
      )}

      {/* Chat Window Popup */}
      {isOpen && (
        <div className="glass-panel" style={{
          width: '360px',
          height: '500px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 12px 36px rgba(0,0,0,0.15)',
          overflow: 'hidden',
          animation: 'fadeInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        }}>
          {/* Header */}
          <div style={{
            padding: '16px 20px',
            background: 'linear-gradient(135deg, var(--primary), var(--primary-hover))',
            color: 'white',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: 'rgba(255,255,255,0.2)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Headset size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>Sarah (سارة)</h4>
                <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>{isArabic ? 'خدمة العملاء' : 'Customer Support'}</span>
              </div>
            </div>
            <button 
              onClick={() => setIsOpen(false)}
              style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Messages body */}
          <div style={{
            flex: 1,
            padding: '20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '15px',
            backgroundColor: 'var(--bg-primary)',
          }}>
            {messages.map((msg, i) => {
              const isUser = msg.sender === 'user';
              return (
                <div 
                  key={i} 
                  style={{
                    alignSelf: isUser ? 'flex-end' : 'flex-start',
                    maxWidth: '80%',
                    backgroundColor: isUser ? 'var(--primary)' : 'var(--bg-secondary)',
                    color: isUser ? 'white' : 'var(--text-primary)',
                    padding: '10px 14px',
                    borderRadius: isUser ? '16px 16px 2px 16px' : '16px 16px 16px 2px',
                    fontSize: '0.9rem',
                    lineHeight: '1.4',
                    border: isUser ? 'none' : '1px solid var(--border-color)',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.02)',
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
                display: 'flex',
                gap: '4px',
                alignItems: 'center',
              }}>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out' }}></span>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out 0.2s' }}></span>
                <span style={{ width: '6px', height: '6px', backgroundColor: 'var(--text-secondary)', borderRadius: '50%', animation: 'bounce 1.4s infinite ease-in-out 0.4s' }}></span>
              </div>
            )}
            
            <div ref={chatEndRef} />
          </div>

          {/* Form input */}
          <form onSubmit={handleSend} style={{
            padding: '15px',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            gap: '10px',
            backgroundColor: 'var(--bg-secondary)',
          }}>
            <input
              type="text"
              className="form-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isArabic ? 'اكتب رسالتك للدعم الفني...' : 'Type support message...'}
              style={{ flex: 1, padding: '10px 14px', borderRadius: '24px' }}
            />
            <button
              type="submit"
              className="btn btn-primary"
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                padding: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}

      {/* Simple style inject for bouncing loader & slide up */}
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
