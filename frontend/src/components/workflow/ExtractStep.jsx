import React from 'react';

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
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '25px' }}>
        {isArabic 
          ? 'سنقوم بتشغيل خوارزميات الرؤية الحاسوبية لقراءة الجداول والمقاسات من كل صفحة مصنفة.'
          : 'We will now run computer vision algorithms with AI models to read coordinates, schedules and dimensions.'}
      </p>

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
