import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader, HelpCircle, RefreshCw } from 'lucide-react';

export default function QsAssistant({ token, isArabic }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/agents/history?role=qs', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.length > 0) {
          const formatted = data.map(m => ({
            role: m.sender === 'user' ? 'user' : 'assistant',
            content: m.message
          }));
          setMessages(formatted);
        } else {
          // Welcome message
          setMessages([
            {
              role: 'assistant',
              content: isArabic
                ? 'مرحباً بك باشمهندس باسل! أنا مساعد حصر الكميات الذكي (QS Assistant).\nيمكنك سؤالي عن معادلات الحصر وصيغ الكميات، أو طلب تحديث أسعار مواد البناء بالامارات.'
                : 'Hello Eng. Basel! I am your Quantity Surveyor Assistant. Ask me about villa takeoff formulas, structural components, or request UAE market rates update!'
            }
          ]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (textToSend) => {
    const prompt = textToSend || input;
    if (!prompt.trim()) return;

    if (!textToSend) setInput('');
    setMessages(prev => [...prev, { role: 'user', content: prompt }]);
    setLoading(true);

    try {
      const res = await fetch('/api/agents/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ prompt, role: 'qs' })
      });
      const data = await res.json();
      if (res.ok) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: isArabic ? 'عذراً، واجهت مشكلة في معالجة طلبك.' : 'Error generating response.' }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: isArabic ? 'فشل الاتصال بالخادم.' : 'Connection failed.' }]);
    } finally {
      setLoading(false);
    }
  };

  const quickQuestions = isArabic ? [
    { label: '🏗️ حساب الحفر والردم', q: 'ما هي معادلة حصر الحفر والردم للفلل؟' },
    { label: '📐 خرسانة ونظافة القواعد', q: 'كيف يتم حساب خرسانة ونظافة القواعد؟' },
    { label: '🔗 حساب الميدة (Tie Beams)', q: 'كيف نحسب كمرات الميدة والبيتومين لها؟' },
    { label: '💰 تحديث أسعار السوق الحرة', q: 'قم بتحديث أسعار السوق الآن' }
  ] : [
    { label: '🏗️ Excavation & Backfill', q: 'What is the formula for excavation and backfill?' },
    { label: '📐 Footings & Blinding', q: 'How to calculate concrete for footing and PCC blinding?' },
    { label: '🔗 Tie Beams Calculation', q: 'Explain tie beams and bitumen quantity formulas' },
    { label: '💰 Sync UAE Market Rates', q: 'update prices' }
  ];

  return (
    <div style={{ padding: '30px', maxWidth: '900px', margin: '0 auto', height: 'calc(100vh - 60px)', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '20px', marginBottom: '20px' }}>
        <div style={{
          width: '50px',
          height: '50px',
          borderRadius: '12px',
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          color: 'var(--primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Bot size={28} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
            {isArabic ? 'مساعد حصر الكميات الذكي (QS Assistant)' : 'Quantity Surveying AI Assistant'}
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', marginTop: '3px' }}>
            {isArabic ? 'مستشارك الهندسي لمعادلات الحصر، كميات الفلل وأسعار السوق بالإمارات.' : 'AI expert in Dubai Building Code, takeoff formulas, and market rates.'}
          </p>
        </div>
      </div>

      {/* Quick query tags */}
      <div style={{ marginBottom: '20px' }}>
        <p style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase' }}>
          {isArabic ? '💡 استفسارات سريعة' : '💡 Quick Operations'}
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {quickQuestions.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(item.q)}
              disabled={loading}
              style={{
                padding: '8px 14px',
                fontSize: '0.82rem',
                borderRadius: '20px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                hover: { background: 'var(--primary-glow)', color: 'var(--primary)' }
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="glass-panel" style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '20px',
        overflow: 'hidden'
      }}>
        
        {/* Messages Feed */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          paddingRight: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '15px'
        }}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '80%',
              background: msg.role === 'user' ? 'var(--primary-glow)' : 'var(--bg-secondary)',
              color: msg.role === 'user' ? 'var(--primary)' : 'var(--text-primary)',
              padding: '12px 18px',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              whiteSpace: 'pre-line'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '0.75rem', marginBottom: '4px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                {msg.role === 'user' ? (isArabic ? 'المهندس باسل' : 'Eng. Basel') : (isArabic ? 'مستشار الحصر' : 'QS Engineer')}
              </div>
              {msg.content}
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 18px', background: 'var(--bg-secondary)', borderRadius: '12px' }}>
              <Loader size={16} className="spin-anim" />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{isArabic ? 'جاري التحليل الحسابي وتأكيد المعادلات...' : 'QS AI calculating volume formulas...'}</span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '15px' }}>
          <input
            type="text"
            className="form-input"
            placeholder={isArabic ? 'اسأل عن حجم الخرسانة، الحديد، الردم...' : 'Ask about concrete blinding, tie beams perimeter, market prices...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '10px 20px' }} disabled={loading}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
