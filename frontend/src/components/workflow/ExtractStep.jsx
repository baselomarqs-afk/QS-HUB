import React from 'react';
import { Info } from 'lucide-react';

export default function ExtractStep({
  loading,
  isArabic,
  handleRunExtraction
}) {
  return (
    <div className="glass-panel" style={{ padding: '30px', maxWidth: '600px', margin: '0 auto', textAlign: 'center' }}>
      <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>
        {isArabic ? '3. استخراج البيانات بالذكاء الاصطناعي' : '3. AI Quantity Data Extraction'}
      </h3>
      <div style={{ padding: '15px 20px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '25px', textAlign: isArabic ? 'right' : 'left' }}>
        <div style={{ color: '#3b82f6', marginTop: '2px' }}><Info size={20} /></div>
        <div>
          <h4 style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', fontSize: '0.95rem' }}>
            {isArabic ? 'ما المطلوب في هذه الخطوة؟' : 'What to do in this step?'}
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, lineHeight: '1.5' }}>
            {isArabic 
              ? 'كل ما عليك فعله هنا هو الضغط على زر التشغيل. ستقوم خوارزميات الذكاء الاصطناعي والرؤية الحاسوبية بقراءة الجداول الهندسية، استخراج مقاسات القواعد والأعمدة والأبواب بدقة عالية وتجهيزها لك.'
              : 'Simply click the run button. The AI and Computer Vision algorithms will automatically read the engineering schedules, extract dimensions for footings, columns, doors, and prepare the takeoff data.'}
          </p>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '30px 0' }}>
          <div className="spin-anim" style={{ width: '45px', height: '45px', border: '4px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 15px' }}></div>
          <p style={{ fontWeight: 600 }}>{isArabic ? 'جاري استخراج وتحليل المقاسات عبر الذكاء الاصطناعي...' : 'Extracting dimensions and door schedules via AI Vision...'}</p>
        </div>
      ) : (
        <button className="btn btn-primary" onClick={handleRunExtraction} style={{ width: '100%', padding: '12px' }}>
          {isArabic ? 'تشغيل استخراج البيانات الهندسية' : 'Run AI Takeoff Extraction'}
        </button>
      )}
    </div>
  );
}
