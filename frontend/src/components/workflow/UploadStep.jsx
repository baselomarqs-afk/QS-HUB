import React from 'react';
import { Upload, Info } from 'lucide-react';

export default function UploadStep({
  strFiles,
  setStrFiles,
  archFiles,
  setArchFiles,
  loading,
  handleUpload,
  isArabic
}) {
  return (
    <div className="glass-panel" style={{ padding: '30px', maxWidth: '800px', margin: '0 auto' }}>
      <h3 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>
        {isArabic ? '1. رفع مخططات الفيلا الهندسية' : '1. Upload Villa Drawing Blueprints'}
      </h3>
      <div style={{ padding: '15px 20px', backgroundColor: 'rgba(59, 130, 246, 0.1)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '8px', display: 'flex', alignItems: 'flex-start', gap: '12px', marginBottom: '25px' }}>
        <div style={{ color: '#3b82f6', marginTop: '2px' }}><Info size={20} /></div>
        <div>
          <h4 style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px', fontSize: '0.95rem' }}>
            {isArabic ? 'ما المطلوب في هذه الخطوة؟' : 'What to do in this step?'}
          </h4>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0, lineHeight: '1.5' }}>
            {isArabic 
              ? 'يرجى رفع ملفات المخططات الإنشائية والمعمارية بصيغة PDF ليقوم الذكاء الاصطناعي بقراءتها. (المخطط الإنشائي يجب أن يحتوي على جداول القواعد والأعمدة والميد، والمعماري يجب أن يحتوي على المساقط).'
              : 'Please upload the structural and architectural blueprints (PDF format). The structural drawing must contain the schedules (footings, columns, etc.), and the architectural drawing must contain the floor plans.'}
          </p>
        </div>
      </div>

      <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* Structural Drawing */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '30px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              {isArabic ? 'المخطط الإنشائي (Structural)' : 'Structural Drawings (PDF)'}
              <div title={isArabic ? 'يجب أن يحتوي على الجداول الإنشائية (قواعد، أعمدة، ميد، تسليح الأسقف)' : 'Must contain structural schedules (Footings, Columns, Tie Beams, Slabs)'} style={{ cursor: 'help', color: 'var(--primary)' }}>
                <Info size={14} />
              </div>
            </h4>
            <input type="file" multiple accept=".pdf" onChange={(e) => setStrFiles(Array.from(e.target.files))} />
            {strFiles && strFiles.length > 0 && (
              <div style={{ marginTop: '12px', textAlign: 'left' }}>
                {strFiles.map((f, i) => (
                  <p key={i} style={{ fontSize: '0.8rem', color: 'var(--success)', marginBottom: '4px', fontWeight: 600 }}>✓ {f.name}</p>
                ))}
              </div>
            )}
          </div>

          {/* Architectural Drawing */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '30px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <Upload size={32} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
              {isArabic ? 'المخطط المعماري (Architectural)' : 'Architectural Drawings (PDF)'}
              <div title={isArabic ? 'يجب أن يحتوي على المساقط الأفقية للأدوار، وجداول الأبواب والنوافذ' : 'Must contain Floor Plans and Doors & Windows schedules'} style={{ cursor: 'help', color: 'var(--primary)' }}>
                <Info size={14} />
              </div>
            </h4>
            <input type="file" multiple accept=".pdf" onChange={(e) => setArchFiles(Array.from(e.target.files))} />
            {archFiles && archFiles.length > 0 && (
              <div style={{ marginTop: '12px', textAlign: 'left' }}>
                {archFiles.map((f, i) => (
                  <p key={i} style={{ fontSize: '0.8rem', color: 'var(--success)', marginBottom: '4px', fontWeight: 600 }}>✓ {f.name}</p>
                ))}
              </div>
            )}
          </div>
        </div>

        <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px' }} disabled={loading || (strFiles.length === 0 && archFiles.length === 0)}>
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
