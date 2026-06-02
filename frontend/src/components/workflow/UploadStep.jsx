import React from 'react';
import { Upload } from 'lucide-react';

export default function UploadStep({
  strFile,
  setStrFile,
  archFile,
  setArchFile,
  loading,
  handleUpload,
  isArabic
}) {
  return (
    <div className="glass-panel" style={{ padding: '30px', maxWidth: '800px', margin: '0 auto' }}>
      <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>
        {isArabic ? '1. رفع مخططات الفيلا الهندسية' : '1. Upload Villa Drawing Blueprints'}
      </h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '25px' }}>
        {isArabic 
          ? 'يرجى رفع ملفات المخططات الإنشائية والمعمارية بصيغة PDF لتبدأ المنصة بالتقطيع والتعرف.'
          : 'Please upload structural and architectural drawing sheets to initiate quantity estimation.'}
      </p>

      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Structural Drawing */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '30px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>
              {isArabic ? 'المخطط الإنشائي (Structural)' : 'Structural Drawings (PDF)'}
            </h4>
            <input type="file" accept=".pdf" onChange={(e) => setStrFile(e.target.files[0])} />
            {strFile && <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: '8px', fontWeight: 600 }}>✓ {strFile.name}</p>}
          </div>

          {/* Architectural Drawing */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '30px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>
              {isArabic ? 'المخطط المعماري (Architectural)' : 'Architectural Drawings (PDF)'}
            </h4>
            <input type="file" accept=".pdf" onChange={(e) => setArchFile(e.target.files[0])} />
            {archFile && <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: '8px', fontWeight: 600 }}>✓ {archFile.name}</p>}
          </div>
        </div>

        <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px' }} disabled={loading || (!strFile && !archFile)}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <div className="spin-anim" style={{ width: '16px', height: '16px', border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }}></div>
              <span>{isArabic ? 'جاري رفع الملفات ومعالجتها بصرياً...' : 'Uploading & splitting pages...'}</span>
            </div>
          ) : (
            isArabic ? 'رفع المخططات وتصنيفها تلقائياً' : 'Upload & Start Auto-classification'
          )}
        </button>
      </form>
    </div>
  );
}
