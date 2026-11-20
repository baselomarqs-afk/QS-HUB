import { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader, Trash2 } from 'lucide-react';

export default function QsAssistant({ token, isArabic }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const welcomeMessage = {
    role: 'assistant',
    content: isArabic
      ? 'مرحباً بك يا مهندس! أنا **مهندس حصر كميات أول (Senior UAE QS Engineer)** بخبرة شاملة في سوق الإمارات.\n\nأستطيع مساعدتك بشكل فعلي ومفصّل في:\n• عقود **FIDIC (1999 & 2017)** — التغييرات، تمديد الوقت (EOT)، المطالبات وإشعار الـ 28 يوماً، إطالة المدة، والمستخلصات\n• قواعد القياس **POMI / NRM2** وكود دبي للبناء **DBC** وقانون المعاملات المدنية وضريبة الـ 5% **FTA**\n• تحليل الأسعار (`Rate Build-Up`)، نسب الحديد (`kg/m³`)، ومعادلات الحصر التفصيلية للفلل\n• الاستعلام عن **أسعار السوق الإماراتي الحالية** المباشرة وحساب التكلفة التقديرية لبنودك'
      : 'Welcome Engineer! I am your **Senior UAE Quantity Surveyor (MRICS / UAE QS Expert)**.\n\nI can help you with real, calculation-backed guidance on:\n• **FIDIC 1999 & 2017** (Variations, EOT Clause 8.4, 28-Day Notice Clause 20.1/20.2, Prolongation, IPCs, Advance & Retention)\n• **POMI / NRM2**, Dubai Building Code (**DBC**), UAE Civil Code (Muqawala), and **UAE FTA 5% VAT**\n• Detailed **Rate Build-Up Analysis**, structural rebar ratios (`kg/m³`), and villa QTO formulas\n• **Live UAE Market Prices** & instant cost estimates from our market database and live web search',
  };

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await fetch('/api/agents/history?role=qs', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!active) return;
        if (res.ok) {
          const data = await res.json();
          if (!active) return;
          if (data.length > 0) {
            setMessages(data.map((m) => ({
              role: m.sender === 'user' ? 'user' : 'assistant',
              content: m.message,
            })));
          } else {
            setMessages([welcomeMessage]);
          }
        }
      } catch (err) {
        console.error(err);
      }
    })();
    return () => { active = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isArabic]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const prompt = textToSend || input;
    if (!prompt.trim() || loading) return;

    if (!textToSend) setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: prompt }]);
    setLoading(true);

    try {
      const res = await fetch('/api/agents/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ prompt, role: 'qs' }),
      });
      const data = await res.json();
      if (res.ok) {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.reply }]);
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', content: data.detail || (isArabic ? 'عذراً، واجهت مشكلة في معالجة طلبك.' : 'Error generating response.') }]);
      }
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: isArabic ? 'فشل الاتصال بالخادم.' : 'Connection failed.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = async () => {
    try {
      await fetch('/api/agents/history?role=qs', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch { /* ignore */ }
    setMessages([welcomeMessage]);
  };

  const quickQuestions = isArabic ? [
    { label: '⚖️ FIDIC: شروط مطالبة EOT (بند 20.1)', q: 'اشرح لي شروط تقديم مطالبة تمديد الوقت (EOT) وإشعار الـ 28 يوماً وفق عقد FIDIC 1999 و2017 مع مثال عملي لفيلا في دبي.' },
    { label: '📊 تحليل سعر متر اللياسة والبلوك', q: 'اعمل لي Rate Build-Up (تحليل سعر تفصيلي بالدرهم الإماراتي) لمتر مربع لياسة داخلية سماكة 20 مم ومتر مربع طابوق عازل 200 مم حسب أسعار السوق الإماراتي الحالية.' },
    { label: '🏗️ نسب الحديد kg/m³ في الفلل', q: 'ما هي نسب حديد التسليح القياسية (kg/m³) لكل عنصر إنشائي في فلل الإمارات (قواعد، ميدات، أعمدة، بلاطات) وكيف نحسب تكلفتها بالأسعار الحالية؟' },
    { label: '🧾 ضريبة 5% FTA على المستخلصات', q: 'كيف تُحسب ضريبة القيمة المضافة الإماراتية 5% (FTA VATP011) على الدفعة المقدمة والمستخلصات الشهرية وإفراج المحتجزات؟ أعطني مثالاً رقمياً.' },
    { label: '💰 أسعار الحديد والخرسانة اليوم بالإمارات', q: 'ما هي أحدث أسعار حديد التسليح والخرسانة الجاهزة C30/C40 والبلوك حالياً في دبي وأبوظبي والشارقة؟' },
  ] : [
    { label: '⚖️ FIDIC EOT & 28-Day Notice (Cl. 20.1)', q: 'Explain Extension of Time (EOT) and the 28-day notice time-bar under FIDIC 1999 vs 2017 Red Book, and how UAE Civil Code affects time-bar clauses.' },
    { label: '📊 Rate Build-Up: Plaster & Blockwork', q: 'Prepare a detailed UAE AED Rate Build-Up (Material + Waste + Labor + OH&P) per m² for 20mm internal plaster and 200mm thermal blockwork using current UAE market rates.' },
    { label: '🏗️ Villa Rebar Ratios (kg/m³)', q: 'What are standard UAE villa rebar ratios (kg/m³) for footings, tie beams, columns, and slabs, and estimate total steel cost for 180 m³ of concrete at live Dubai rates?' },
    { label: '🧾 UAE FTA 5% VAT on IPCs & Retention', q: 'How does UAE FTA VAT (VATP011) apply to Advance Payment, pro-rata recovery, monthly IPCs, and PC/DLP retention releases? Give a worked numeric example.' },
    { label: '💰 Live UAE Rebar & Concrete Rates', q: 'What are the current UAE market rates for Emirates Steel rebar, C30/C40 ready-mix concrete, and villa turnkey AED/m² across Dubai and Abu Dhabi?' },
  ];

  return (
    <div style={{ padding: '26px', maxWidth: '960px', margin: '0 auto', height: 'calc(100vh - 50px)', display: 'flex', flexDirection: 'column', direction: isArabic ? 'rtl' : 'ltr' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '15px', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', marginBottom: '16px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '48px', height: '48px', borderRadius: '12px',
            backgroundColor: 'rgba(59, 130, 246, 0.15)', color: 'var(--primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Bot size={26} />
          </div>
          <div>
            <h1 style={{ fontSize: '1.42rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
              {isArabic ? 'مهندس حصر الكميات الذكي (Senior UAE QS)' : 'Senior UAE QS Engineer Assistant'}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '3px', marginBottom: 0 }}>
              {isArabic ? 'متخصص في FIDIC، قواعد POMI/NRM2، كود دبي، ضريبة FTA، وأسعار السوق الإماراتي الحية.' : 'FIDIC 1999/2017, POMI/NRM2, Dubai Building Code, UAE FTA VAT & live market rates.'}
            </p>
          </div>
        </div>
        <button className="btn btn-secondary" onClick={handleClear} disabled={loading} style={{ fontSize: '0.8rem', padding: '7px 12px', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Trash2 size={14} /> {isArabic ? 'محادثة جديدة' : 'New Chat'}
        </button>
      </div>

      {/* Quick query chips */}
      <div style={{ marginBottom: '14px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {quickQuestions.map((item, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(item.q)}
              disabled={loading}
              style={{
                padding: '7px 12px', fontSize: '0.79rem', borderRadius: '20px',
                border: '1px solid var(--border-color)', background: 'var(--bg-secondary)',
                color: 'var(--text-primary)', cursor: 'pointer', transition: 'all 0.2s ease',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="glass-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '18px', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', paddingInlineEnd: '8px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {messages.map((msg, idx) => (
            <div key={idx} style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '86%',
              background: msg.role === 'user' ? 'var(--primary-glow)' : 'var(--bg-secondary)',
              color: msg.role === 'user' ? 'var(--primary)' : 'var(--text-primary)',
              padding: '12px 16px',
              borderRadius: '12px',
              border: '1px solid var(--border-color)',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
              fontSize: '0.9rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 700, fontSize: '0.74rem', marginBottom: '5px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                {msg.role === 'user' ? <User size={12} /> : <Bot size={12} />}
                {msg.role === 'user' ? (isArabic ? 'أنت' : 'You') : (isArabic ? 'مهندس QS أول' : 'Senior UAE QS')}
              </div>
              {msg.content}
            </div>
          ))}
          {loading && (
            <div style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
              <Loader size={16} className="spin-anim" />
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {isArabic ? 'جاري البحث والتحليل الهندسي (FIDIC / أسعار السوق)...' : 'Analyzing QS rules, FIDIC clauses & live UAE market rates...'}
              </span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} style={{ display: 'flex', gap: '10px', marginTop: '14px', borderTop: '1px solid var(--border-color)', paddingTop: '14px' }}>
          <input
            type="text"
            className="form-input"
            placeholder={isArabic ? 'اسأل عن FIDIC، تحليل الأسعار، POMI، حصر الكميات، أو أسعار السوق...' : 'Ask about FIDIC clauses, rate build-up, POMI/NRM2, takeoff formulas, or UAE prices...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            style={{ flex: 1 }}
            disabled={loading}
          />
          <button type="submit" className="btn btn-primary" style={{ padding: '10px 20px' }} disabled={loading || !input.trim()}>
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
