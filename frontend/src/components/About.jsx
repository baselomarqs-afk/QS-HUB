// About / Overview page — a professional, engineer-facing walkthrough of the
// platform and its three tools. Fully bilingual (Arabic / English).
import React from 'react';
import { Play, CalendarDays, Wallet, Bot, BarChart2, Eye, CheckCircle2, ArrowRight } from 'lucide-react';

export default function About({ isArabic, onNavigate }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const dir = isArabic ? 'rtl' : 'ltr';
  const align = isArabic ? 'right' : 'left';

  const card = {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-color)',
    borderRadius: '16px',
    padding: '24px',
  };
  const h2 = { fontFamily: 'var(--font-display)', fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 6px' };
  const p = { color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.96rem' };

  const tools = [
    {
      icon: <Play size={22} fill="var(--primary)" color="var(--primary)" />,
      color: 'var(--primary)',
      name: t('QTO — Quantity Take-Off', 'حصر الكميات — QTO'),
      desc: t(
        'Automated Bill of Quantities from PDF drawings via a 5-stage guided flow: Upload → Classify → Extract → Verify → BOQ. A hybrid engine reads each sheet — AI vision for interpretation, PyMuPDF vector geometry for exact measurement, and OCR/OpenCV for text — using documented UAE villa formulas. Every value is sanity-checked and shown for your review before it becomes a quantity. Exports to Excel.',
        'توليد جدول كميات آلي من مخططات PDF عبر 5 مراحل موجّهة: رفع ← تصنيف ← استخراج ← مراجعة ← BOQ. محرّك هجين بيقرأ كل ورقة — رؤية AI للفهم، وهندسة متجهة (PyMuPDF) للقياس الدقيق، وOCR/OpenCV للنصوص — بصيغ فيلا إماراتية موثّقة. كل قيمة بتتفحص منطقياً وبتتعرض لمراجعتك قبل ما تبقى كمية. تصدير Excel.'
      ),
    },
    {
      icon: <CalendarDays size={22} color="var(--success)" />,
      color: 'var(--success)',
      name: t('Work Programme', 'البرنامج الزمني'),
      desc: t(
        'Generates a realistic construction programme (schedule / Gantt) from villa type, built-up area, complexity and dates. A CPM scheduler with predecessor logic, an all-works-complete gate before hand-over, and a fit-to-handover constraint. Durations are calibrated by area, floor count and complexity. Fully deterministic. Exports to Excel.',
        'بيولّد برنامج تنفيذ واقعي (جدول زمني / Gantt) من نوع الفيلا ومساحة البناء والتعقيد والتواريخ. مجدول CPM بمنطق الأسبقيات، وبوابة اكتمال الأعمال قبل التسليم، وقيد الضبط على تاريخ التسليم. المدد معايَرة بالمساحة وعدد الأدوار والتعقيد. حتمي بالكامل. تصدير Excel.'
      ),
    },
    {
      icon: <Wallet size={22} color="var(--warning)" />,
      color: 'var(--warning)',
      name: t('Cash Flow', 'التدفق النقدي'),
      desc: t(
        'Turns the programme into a month-by-month cash-flow forecast using real UAE contract mechanics: advance & recovery, retention (held and released at PC and DLP end), VAT, and certification + payment delays. Produces the S-curve plus working-capital requirement, peak-deficit month, payback month, profit margin and double-dip detection. Exports to Excel.',
        'بيحوّل البرنامج لتوقّع تدفق نقدي شهري بآليات عقود الإمارات: دفعة مقدمة واستردادها، محتجزات (تُحتجز وتُفرج عند التسليم ونهاية الصيانة)، VAT، وتأخير الاعتماد والسداد. بيطلّع منحنى S-curve ورأس المال العامل وشهر أقصى عجز وشهر الاسترداد وهامش الربح وكشف الهبوط المزدوج. تصدير Excel.'
      ),
    },
  ];

  const steps = [
    ['1', t('Upload', 'الرفع'), t('Architectural + Structural PDF sets.', 'مجموعتا المخططات المعمارية + الإنشائية.')],
    ['2', t('Classify', 'التصنيف'), t('Each sheet is auto-detected; you confirm.', 'كل ورقة تُكتشف تلقائياً؛ وإنت بتأكّد.')],
    ['3', t('Extract', 'الاستخراج'), t('Hybrid AI + vector geometry reads every sheet.', 'هجين AI + هندسة متجهة بيقرأ كل ورقة.')],
    ['4', t('Verify', 'المراجعة'), t('Review every value with confidence & sanity flags.', 'راجع كل قيمة بمؤشرات ثقة وتحذيرات منطقية.')],
    ['5', t('BOQ', 'الـ BOQ'), t('Spec-compliant formulas build the bilingual BOQ.', 'صيغ مطابقة للمواصفات تبني الـ BOQ ثنائي اللغة.')],
  ];

  const features = [
    [<Bot size={18} />, t('QS Assistant', 'مساعد QS'), t('AI chat for quantity-surveying questions.', 'مساعد AI لأسئلة حصر الكميات.')],
    [<BarChart2 size={18} />, t('Market Prices', 'أسعار السوق'), t('Editable UAE material rates, per emirate.', 'أسعار مواد إماراتية قابلة للتعديل لكل إمارة.')],
    [<Eye size={18} />, t('Plan Comparison', 'مقارنة المخططات'), t('Visual diff between two drawing revisions.', 'فرق بصري بين نسختين من المخطط.')],
    [<CheckCircle2 size={18} />, t('Spec Pre-fill', 'التعبئة من المواصفات'), t('AI reads a spec PDF and pre-fills the project.', 'الـ AI يقرأ ملف المواصفات ويملأ المشروع.')],
  ];

  const plans = [
    [t('Free', 'مجاني'), '1', t('1st project / tool', 'مشروع أول / أداة')],
    ['Professional', '3', t('projects / month', 'مشاريع / شهر')],
    ['Business', '8', t('projects / month', 'مشاريع / شهر')],
    ['Studio', '20', t('projects / month', 'مشاريع / شهر')],
  ];

  return (
    <div style={{ padding: '32px clamp(16px, 4vw, 48px)', maxWidth: 1150, margin: '0 auto', direction: dir, textAlign: align }}>

      {/* Hero */}
      <div className="glass-panel" style={{ padding: '32px', marginBottom: 28, borderLeft: isArabic ? 'none' : '4px solid var(--primary)', borderRight: isArabic ? '4px solid var(--primary)' : 'none' }}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 10px' }}>
          {t('THE QS HUB 🏗️', 'THE QS HUB 🏗️')}
        </h1>
        <p style={{ ...p, fontSize: '1.05rem', margin: 0 }}>
          {t(
            'An AI-assisted Quantity Surveying platform built specifically for villa projects in the UAE. It takes you from engineering drawings → certified BOQ → construction programme → cash-flow forecast in one integrated, bilingual workspace — work that normally needs three separate desktop packages.',
            'منصة حصر كميات مدعومة بالذكاء الاصطناعي، متخصصة في مشاريع الفلل بالإمارات. بتاخدك من المخططات الهندسية ← جدول كميات معتمد ← برنامج زمني ← توقّع تدفق نقدي، في مساحة عمل واحدة متكاملة ثنائية اللغة — شغل عادةً بيحتاج 3 برامج منفصلة.'
          )}
        </p>
        <p style={{ ...p, marginTop: 12, marginBottom: 0, fontWeight: 600, color: 'var(--text-primary)' }}>
          {t('Core principle: the AI does the heavy lifting — the engineer stays in control.',
             'المبدأ الأساسي: الذكاء الاصطناعي بيعمل الشغل الثقيل — والمهندس هو صاحب القرار.')}
        </p>
      </div>

      {/* Three tools */}
      <h2 style={h2}>{t('The Three Tools', 'الأدوات الثلاث')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20, margin: '16px 0 32px' }}>
        {tools.map((tool, i) => (
          <div key={i} style={{ ...card, borderTop: `3px solid ${tool.color}` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
              <div style={{ width: 44, height: 44, borderRadius: 12, background: 'var(--bg-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{tool.icon}</div>
              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)' }}>{tool.name}</h3>
            </div>
            <p style={{ ...p, margin: 0, fontSize: '0.9rem' }}>{tool.desc}</p>
          </div>
        ))}
      </div>

      {/* QTO workflow */}
      <h2 style={h2}>{t('The QTO Workflow', 'مسار حصر الكميات')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, margin: '16px 0 32px' }}>
        {steps.map(([n, title, desc]) => (
          <div key={n} style={{ ...card, padding: 18 }}>
            <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'var(--primary)', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, marginBottom: 8 }}>{n}</div>
            <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>{title}</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{desc}</div>
          </div>
        ))}
      </div>

      {/* Methodology note */}
      <div style={{ ...card, background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.25)', marginBottom: 32 }}>
        <h3 style={{ margin: '0 0 8px', color: 'var(--primary)', fontSize: '1.05rem', fontWeight: 800 }}>
          {t('Engineering methodology', 'المنهجية الهندسية')}
        </h3>
        <p style={{ ...p, margin: 0, fontSize: '0.9rem' }}>
          {t(
            'Quantities are derived from documented UAE villa formulas. Measurements are taken from the real vector geometry of the drawing (not from pixels) and calibrated to the drawing scale, then cross-validated against a database of real UAE villa BOQs and flagged when any value falls outside typical ranges.',
            'الكميات مشتقة من صيغ فيلا إماراتية موثّقة. القياسات مأخوذة من الهندسة المتجهة الحقيقية للمخطط (مش من البكسل) ومعايَرة على مقياس الرسم، وبتتقارن مع قاعدة BOQ فيلل إماراتية حقيقية، وبتتعلّم عند أي قيمة خارجة عن المعتاد.'
          )}
        </p>
      </div>

      {/* Supporting features */}
      <h2 style={h2}>{t('Supporting Features', 'مميزات مساندة')}</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14, margin: '16px 0 32px' }}>
        {features.map(([icon, title, desc], i) => (
          <div key={i} style={{ ...card, padding: 18, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{ color: 'var(--primary)', marginTop: 2 }}>{icon}</div>
            <div>
              <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: 3 }}>{title}</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{desc}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Plans */}
      <h2 style={h2}>{t('Plans', 'الباقات')}</h2>
      <p style={{ ...p, margin: '4px 0 16px', fontSize: '0.9rem' }}>
        {t('Each tool is sold independently across three monthly tiers, plus a one-time “extra project” add-on. Every new user gets their first project free on each tool — no subscription needed to start.',
           'كل أداة تُباع مستقلة عبر ثلاث باقات شهرية، بالإضافة لمشروع إضافي لمرة واحدة. كل مستخدم جديد بياخد مشروعه الأول مجاناً على كل أداة — من غير اشتراك.')}
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 32 }}>
        {plans.map(([name, n, unit]) => (
          <div key={name} style={{ ...card, textAlign: 'center', padding: 20 }}>
            <div style={{ fontWeight: 800, color: 'var(--primary)', marginBottom: 6 }}>{name}</div>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)' }}>{n}</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{unit}</div>
          </div>
        ))}
      </div>

      {/* Who it's for + CTA */}
      <div className="glass-panel" style={{ padding: 28, display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ maxWidth: 640 }}>
          <h3 style={{ margin: '0 0 6px', color: 'var(--text-primary)', fontSize: '1.1rem', fontWeight: 800 }}>
            {t('Who it’s for', 'لمين مصممة')}
          </h3>
          <p style={{ ...p, margin: 0, fontSize: '0.92rem' }}>
            {t('UAE contractors, QS consultants and site engineers who need fast, affordable, bilingual take-off, programming and cash-flow for villa projects — without enterprise-software cost or training.',
               'المقاولون واستشاريو حصر الكميات ومهندسو المواقع في الإمارات اللي محتاجين حصر وبرمجة وتدفق نقدي سريع واقتصادي وثنائي اللغة لمشاريع الفلل — من غير تكلفة أو تدريب برامج المؤسسات.')}
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => onNavigate && onNavigate('dashboard')} style={{ padding: '12px 22px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
          {t('Go to Dashboard', 'اذهب للوحة التحكم')} <ArrowRight size={16} style={{ transform: isArabic ? 'scaleX(-1)' : 'none' }} />
        </button>
      </div>
    </div>
  );
}
