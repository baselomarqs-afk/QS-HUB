import { useEffect, useState } from 'react';

// In-memory Blob URL cache so switching pages back and forth is instant without re-fetching.
const blobCache = new Map();

function AuthImageInner({ src, alt, style, isArabic, showSpinner = true }) {
  const isProtected = Boolean(src && src.startsWith('/cache/'));
  const cachedInitial = isProtected ? blobCache.get(src) || '' : (src || '');
  const [blobUrl, setBlobUrl] = useState(cachedInitial);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isProtected || blobCache.has(src)) return undefined;

    let cancelled = false;
    let timerId = null;
    let attempts = 0;
    const maxAttempts = 20;

    const loadImage = async () => {
      attempts += 1;
      try {
        const token = localStorage.getItem('qto_token') || '';
        const res = await fetch(src, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (cancelled) return;
        if (res.ok) {
          const blob = await res.blob();
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          if (blobCache.size > 60) {
            const oldestKey = blobCache.keys().next().value;
            const oldestUrl = blobCache.get(oldestKey);
            blobCache.delete(oldestKey);
            if (oldestUrl) URL.revokeObjectURL(oldestUrl);
          }
          blobCache.set(src, url);
          setBlobUrl(url);
          setFailed(false);
          return;
        }
        if (res.status === 404 && attempts < maxAttempts) {
          timerId = setTimeout(loadImage, 1500);
          return;
        }
        setFailed(true);
      } catch {
        if (cancelled) return;
        if (attempts < maxAttempts) {
          timerId = setTimeout(loadImage, 1500);
        } else {
          setFailed(true);
        }
      }
    };

    loadImage();

    return () => {
      cancelled = true;
      if (timerId) clearTimeout(timerId);
    };
  }, [src, isProtected]);

  if (!blobUrl) {
    if (failed) {
      return (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', padding: '16px', textAlign: 'center' }}>
          {isArabic ? 'تعذّر تحميل معاينة المخطط.' : 'Could not load drawing preview.'}
        </div>
      );
    }
    if (!showSpinner) return null;
    return (
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%', minHeight: '120px' }}>
        <div style={{ color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
          <div className="spinner" style={{ width: '30px', height: '30px', border: '3px solid rgba(59, 130, 246, 0.3)', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <span>{isArabic ? 'جاري تجهيز الصورة...' : 'Processing image...'}</span>
          <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  return <img src={blobUrl} alt={alt} style={style} />;
}

/**
 * Fetches protected `/cache/...` engineering drawing previews strictly using the
 * `Authorization: Bearer` header (NEVER leaking JWT tokens in URL query strings)
 * and renders via Blob URL. Keyed by `src` so switching pages resets state cleanly.
 */
export default function AuthImage(props) {
  return <AuthImageInner key={props.src || 'empty'} {...props} />;
}
