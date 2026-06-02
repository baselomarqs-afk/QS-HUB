import React, { useState } from 'react';
import { FileUp, BarChart2, Eye, Download, Info } from 'lucide-react';

export default function PlanComparison({ token, isArabic }) {
  const [file1, setFile1] = useState(null);
  const [file2, setFile2] = useState(null);
  const [pageNum, setPageNum] = useState(1);
  const [dpi, setDpi] = useState(150);
  
  const [diffUrl, setDiffUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!file1 || !file2) return;

    setLoading(true);
    setError('');
    setDiffUrl('');

    const formData = new FormData();
    formData.append('pdf_1', file1);
    formData.append('pdf_2', file2);
    formData.append('page_num', pageNum);
    formData.append('dpi', dpi);

    try {
      const res = await fetch("/api/workflow/compare", {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      if (!res.ok) {
        const errData = await res.json();
        let errMsg = 'Failed to compare drawings.';
        if (errData.detail) {
          if (typeof errData.detail === 'string') {
            errMsg = errData.detail;
          } else if (Array.isArray(errData.detail)) {
            errMsg = errData.detail.map(e => e.msg || JSON.stringify(e)).join(', ');
          } else if (typeof errData.detail === 'object') {
            errMsg = errData.detail.message || JSON.stringify(errData.detail);
          }
        }
        throw new Error(errMsg);
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setDiffUrl(url);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      <div>
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 800, color: 'var(--primary)' }}>
          {isArabic ? 'مقارنة المخططات بصرياً' : 'Visual Plan Comparison Overlay'}
        </h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          {isArabic 
            ? 'قارن نسختين من المخطط لإظهار التعديلات والإضافات هندسياً. يتم تمييز العناصر المحذوفة باللون الأحمر، والعناصر المضافة باللون الأخضر.'
            : 'Compare two versions of architectural drawings to show edits. Deleted elements in Red, additions in Green.'}
        </p>
      </div>
      <hr style={{ border: 'none', height: '1px', backgroundColor: 'var(--border-color)', margin: '20px 0' }} />

      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
          {error}
        </div>
      )}

      <form onSubmit={handleCompare} className="glass-panel" style={{ padding: '25px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* File 1 */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '25px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <FileUp size={36} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>
              {isArabic ? 'النسخة السابقة/القديمة (PDF)' : 'Version 1: Old Drawing (PDF)'}
            </h4>
            <input 
              type="file" 
              accept=".pdf"
              onChange={(e) => setFile1(e.target.files[0])}
              style={{ fontSize: '0.85rem' }} 
            />
            {file1 && <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: '8px', fontWeight: 600 }}>✓ {file1.name}</p>}
          </div>

          {/* File 2 */}
          <div style={{ border: '2px dashed var(--border-color)', borderRadius: '12px', padding: '25px', textAlign: 'center', backgroundColor: 'var(--bg-primary)' }}>
            <FileUp size={36} color="var(--text-muted)" style={{ marginBottom: '10px' }} />
            <h4 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '8px' }}>
              {isArabic ? 'النسخة الجديدة/المعدلة (PDF)' : 'Version 2: New Drawing (PDF)'}
            </h4>
            <input 
              type="file" 
              accept=".pdf"
              onChange={(e) => setFile2(e.target.files[0])}
              style={{ fontSize: '0.85rem' }} 
            />
            {file2 && <p style={{ fontSize: '0.8rem', color: 'var(--success)', marginTop: '8px', fontWeight: 600 }}>✓ {file2.name}</p>}
          </div>
        </div>

        {/* Options */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
              {isArabic ? 'رقم الصفحة في الملف (تبدأ من 1)' : 'Page Number (1-indexed)'}
            </label>
            <input 
              type="number" 
              className="form-input"
              min={1} 
              value={pageNum}
              onChange={(e) => setPageNum(parseInt(e.target.value))}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '0.9rem', fontWeight: 600 }}>
              {isArabic ? 'دقة و جودة الرسم (DPI)' : 'Rendering Quality (DPI)'}
            </label>
            <input 
              type="range" 
              min={72} 
              max={300} 
              step={10}
              value={dpi}
              onChange={(e) => setDpi(parseInt(e.target.value))}
              style={{ width: '100%', marginTop: '12px' }}
            />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{dpi} DPI</span>
          </div>
        </div>

        <button 
          type="submit" 
          className="btn btn-primary" 
          disabled={!file1 || !file2 || loading} 
          style={{ width: '100%', marginTop: '10px', gap: '8px' }}
        >
          {loading ? (isArabic ? 'جاري مقارنة المخططات هندسياً...' : 'Comparing plans overlay...') : (
            <>
              <Eye size={18} />
              {isArabic ? 'ابدأ المقارنة البصرية وتوليد الفروق' : 'Run Visual Overlay Comparison'}
            </>
          )}
        </button>
      </form>

      {/* Comparison Output Display */}
      {diffUrl && (
        <div className="glass-panel" style={{ marginTop: '40px', padding: '25px', textAlign: 'center' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px', color: 'var(--text-primary)', textAlign: isArabic ? 'right' : 'left' }}>
            {isArabic ? 'تراكب المقارنة البصرية' : 'Visual Comparison Output'}
          </h3>

          {/* Color Code Legend */}
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center', justifyContent: 'center', marginBottom: '20px', fontWeight: 600, fontSize: '0.9rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '16px', height: '16px', backgroundColor: '#ef4444', borderRadius: '4px' }}></div>
              <span>{isArabic ? 'العناصر المحذوفة (النسخة السابقة)' : 'Deletions (items removed)'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '16px', height: '16px', backgroundColor: '#22c55e', borderRadius: '4px' }}></div>
              <span>{isArabic ? 'العناصر المضافة (النسخة الجديدة)' : 'Additions (new elements)'}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <div style={{ width: '16px', height: '16px', backgroundColor: '#cbd5e1', borderRadius: '4px', border: '1px solid #94a3b8' }}></div>
              <span>{isArabic ? 'العناصر غير المعدلة' : 'Unchanged elements'}</span>
            </div>
          </div>

          <div style={{
            border: '1px solid var(--border-color)',
            borderRadius: '12px',
            overflow: 'hidden',
            backgroundColor: 'white',
            display: 'flex',
            justifyContent: 'center',
            padding: '10px',
            marginBottom: '20px'
          }}>
            <img 
              src={diffUrl} 
              alt="Visual plan diff overlay" 
              style={{ maxWidth: '100%', height: 'auto', borderRadius: '8px' }} 
            />
          </div>

          <a 
            href={diffUrl} 
            download={`plan_comparison_diff_page_${pageNum}.png`}
            className="btn btn-success"
            style={{ width: '100%', gap: '8px' }}
          >
            <Download size={18} />
            {isArabic ? 'تحميل صورة الفروقات البصرية' : 'Download Visual Diff Image'}
          </a>
        </div>
      )}
    </div>
  );
}
