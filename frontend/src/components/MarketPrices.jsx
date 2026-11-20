import { useState, useEffect } from 'react';
import { Search, RefreshCw, BarChart2, Globe, CheckCircle2, Info } from 'lucide-react';

export default function MarketPrices({ token, isArabic, user }) {
  const [prices, setPrices] = useState([]);
  const [categories, setCategories] = useState({});
  const [emirates, setEmirates] = useState({});
  const [meta, setMeta] = useState(null);

  const [selectedCat, setSelectedCat] = useState('all');
  const [selectedEm, setSelectedEm] = useState('dubai');
  const [searchQuery, setSearchQuery] = useState('');
  const [compareMode, setCompareMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const [refreshTick, setRefreshTick] = useState(0);

  const isAdmin = user?.role === 'admin';
  const fetchPrices = () => setRefreshTick((n) => n + 1);

  useEffect(() => {
    let active = true;
    (async () => {
      await Promise.resolve();
      if (!active) return;
      setLoading(true);
      try {
        const params = new URLSearchParams({
          category: selectedCat,
          emirate: selectedEm,
          search: searchQuery,
          compare: String(compareMode),
        });
        const res = await fetch(`/api/market/prices?${params.toString()}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        if (active && res.ok) {
          setPrices(data.prices || []);
          setCategories(data.categories || {});
          setEmirates(data.emirates || {});
          setMeta(data.meta || null);
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [selectedCat, selectedEm, searchQuery, compareMode, token, refreshTick]);

  const handleForceUpdate = async () => {
    setMessage('');
    setSyncing(true);
    try {
      const res = await fetch('/api/market/prices/update', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setMessage(data.message || (data.ok
        ? (isArabic ? 'تم تحديث الأسعار الحية من السوق بنجاح!' : 'Live UAE market prices refreshed successfully!')
        : (isArabic ? 'تعذر التحديث الآن.' : 'Could not refresh live prices right now.')));
      if (data.ok) fetchPrices();
    } catch (err) {
      console.error(err);
      setMessage(isArabic ? 'حدث خطأ في الاتصال أثناء التحديث.' : 'Connection error during live sync.');
    } finally {
      setSyncing(false);
    }
  };

  const sourceBadge = (src) => {
    if (src === 'live_google_search') {
      return {
        label: isArabic ? 'محدّث من السوق' : 'Live Web',
        bg: 'rgba(16,185,129,0.12)',
        color: 'var(--success)',
      };
    }
    if (src === 'manual') {
      return {
        label: isArabic ? 'معتمد إدارياً' : 'Admin Verified',
        bg: 'rgba(59,130,246,0.12)',
        color: 'var(--primary)',
      };
    }
    return {
      label: isArabic ? 'مرجعي' : 'Reference',
      bg: 'rgba(245,158,11,0.12)',
      color: 'var(--warning)',
    };
  };

  const marketNote = isArabic ? (meta?.market_note_ar || meta?.market_note_en) : meta?.market_note_en;

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      {/* Title Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 15, marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 800, color: 'var(--primary)', margin: 0 }}>
            {isArabic ? 'أسعار السوق الإماراتي (مواد + عمالة)' : 'UAE Market Prices (Materials & Labor)'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', marginTop: '4px', marginBottom: 0 }}>
            {isArabic
              ? 'أسعار إرشادية لمواد البناء وأجور العمالة عبر الإمارات السبع — تُحدَّث أسبوعياً تلقائياً عبر البحث المباشر في السوق (بالدرهم الإماراتي بدون ضريبة 5%).'
              : 'Construction material & subcontract labor rates across all 7 UAE Emirates — automatically synced weekly via live web market search (AED, Excl. 5% VAT).'}
          </p>
        </div>
        {isAdmin && (
          <button className="btn btn-primary" onClick={handleForceUpdate} disabled={syncing || loading} style={{ gap: '8px' }}>
            <RefreshCw size={16} className={syncing ? 'spin-anim' : ''} />
            {syncing
              ? (isArabic ? 'جاري البحث والتحديث الحي...' : 'Fetching Live Market Rates...')
              : (isArabic ? 'تحديث حي الآن من السوق' : 'Sync Live Rates Now')}
          </button>
        )}
      </div>

      {/* Live Sync Metadata & Real Grounded Sources Banner */}
      {meta && (
        <div className="glass-panel" style={{ padding: '14px 18px', marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.88rem', fontWeight: 700, color: meta.sync_mode === 'live_google_search' ? 'var(--success)' : 'var(--warning)' }}>
              {meta.sync_mode === 'live_google_search' ? <CheckCircle2 size={17} /> : <Info size={17} />}
              <span>
                {meta.sync_mode === 'live_google_search'
                  ? (isArabic ? `تم التحقق المباشر من السوق الإماراتي • آخر تحديث: ${meta.last_live_sync}` : `Live Web-Verified UAE Rates • Last Synced: ${meta.last_live_sync}`)
                  : (isArabic ? 'جاري عرض الأسعار المرجعية الأساسية (سيتم التحديث الحي تلقائياً في الخلفية)' : 'Displaying baseline reference rates (live weekly sync running automatically in background)')}
              </span>
            </div>
            {meta.sources?.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                <Globe size={13} />
                <span>{isArabic ? 'المصادر:' : 'Sources:'}</span>
                {meta.sources.slice(0, 4).map((s, idx) => (
                  <span key={idx} style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 10, padding: '2px 8px' }}>
                    {s.title}
                  </span>
                ))}
              </div>
            )}
          </div>
          {marketNote && (
            <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              📊 {marketNote}
            </p>
          )}
        </div>
      )}

      {message && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(16,185,129,0.1)', color: 'var(--success)', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem', fontWeight: 600 }}>
          {message}
        </div>
      )}

      {/* Filters Grid */}
      <div className="glass-panel" style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '15px', marginBottom: '25px', alignItems: 'center' }}>
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="form-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isArabic ? 'ابحث عن مادة أو عمالة أو رمز...' : 'Search materials, labor, or code...'}
            style={{ paddingLeft: isArabic ? '16px' : '40px', paddingRight: isArabic ? '40px' : '16px' }}
          />
          <Search size={18} style={{
            position: 'absolute',
            top: '50%',
            transform: 'translateY(-50%)',
            left: isArabic ? 'auto' : '14px',
            right: isArabic ? '14px' : 'auto',
            color: 'var(--text-muted)',
          }} />
        </div>

        <select className="form-input" value={selectedCat} onChange={(e) => setSelectedCat(e.target.value)}>
          {Object.entries(categories).map(([key, val]) => (
            <option key={key} value={key}>{isArabic ? val.ar : val.en}</option>
          ))}
        </select>

        <select className="form-input" value={selectedEm} disabled={compareMode} onChange={(e) => setSelectedEm(e.target.value)}>
          {Object.entries(emirates).map(([key, val]) => (
            <option key={key} value={key}>{isArabic ? val.ar : val.en}</option>
          ))}
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          <input
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            style={{ width: '18px', height: '18px' }}
          />
          <BarChart2 size={16} />
          {isArabic ? 'مقارنة الإمارات السبع' : 'Compare All 7 Emirates'}
        </label>
      </div>

      {/* Table Data */}
      {loading && prices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <div className="spin-anim" style={{ width: '40px', height: '40px', border: '4px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 15px' }}></div>
          <p>{isArabic ? 'جاري تحميل أسعار السوق...' : 'Loading UAE market rates...'}</p>
        </div>
      ) : prices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '50px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد نتائج تطابق معايير البحث.' : 'No items found matching criteria.'}</p>
        </div>
      ) : (
        <div className="premium-table-container" style={{ overflowX: 'auto' }}>
          <table className="premium-table">
            <thead>
              <tr>
                <th>{isArabic ? 'الرمز' : 'Code'}</th>
                <th>{isArabic ? 'البند / المادة' : 'Item / Material'}</th>
                <th>{isArabic ? 'الوحدة' : 'Unit'}</th>
                {compareMode ? (
                  <>
                    <th>{isArabic ? 'دبي' : 'Dubai'}</th>
                    <th>{isArabic ? 'أبوظبي' : 'Abu Dhabi'}</th>
                    <th>{isArabic ? 'الشارقة' : 'Sharjah'}</th>
                    <th>{isArabic ? 'عجمان' : 'Ajman'}</th>
                    <th>{isArabic ? 'رأس الخيمة' : 'RAK'}</th>
                    <th>{isArabic ? 'الفجيرة' : 'Fujairah'}</th>
                    <th>{isArabic ? 'أم القيوين' : 'UAQ'}</th>
                  </>
                ) : (
                  <th>{isArabic ? 'السعر (درهم)' : 'Price (AED)'}</th>
                )}
                <th>{isArabic ? 'المصدر' : 'Source'}</th>
                <th>{isArabic ? 'تاريخ التحديث' : 'Updated'}</th>
              </tr>
            </thead>
            <tbody>
              {prices.map((item) => {
                const badge = sourceBadge(item.source_type);
                return (
                  <tr key={item.code}>
                    <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>{item.code}</td>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{isArabic ? item.name_ar : item.name_en}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>{item.unit}</td>
                    {compareMode ? (
                      <>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.dubai ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.abudhabi ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.sharjah ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.ajman ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.rak ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.fujairah ?? 0).toFixed(2)}</td>
                        <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{Number(item.prices?.uaq ?? 0).toFixed(2)}</td>
                      </>
                    ) : (
                      <td style={{ color: 'var(--primary)', fontWeight: 700, fontSize: '0.96rem' }}>{Number(item.price ?? 0).toFixed(2)}</td>
                    )}
                    <td>
                      <span style={{ backgroundColor: badge.bg, color: badge.color, padding: '2px 8px', borderRadius: '12px', fontSize: '0.76rem', fontWeight: 700, whiteSpace: 'nowrap' }}>
                        {badge.label}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.82rem', whiteSpace: 'nowrap', color: 'var(--text-muted)' }}>{item.last_verified}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Disclaimer Banner */}
      <div className="glass-panel" style={{
        marginTop: '25px',
        padding: '16px 20px',
        borderLeft: isArabic ? 'none' : '4px solid var(--warning)',
        borderRight: isArabic ? '4px solid var(--warning)' : 'none',
        backgroundColor: 'rgba(245, 158, 11, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
      }}>
        <h5 style={{ fontWeight: 700, color: 'var(--warning)', fontSize: '0.95rem', margin: 0 }}>
          ⚠️ {isArabic ? 'إخلاء مسؤولية مهني' : 'Professional QS Disclaimer'}
        </h5>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: 0 }}>
          {isArabic
            ? 'جميع الأسعار بالدرهم الإماراتي (بدون ضريبة القيمة المضافة 5%) وتمثل متوسطات السوق الإماراتي الحالية المستقاة من بيانات السوق والموردين. تختلف عروض الأسعار النهائية حسب الكمية، المواصفات الخاصة، شروط التوريد، وموقع المشروع — يُنصح دائماً بالحصول على عروض أسعار رسمية قبل تقديم العطاءات.'
            : 'All rates are in AED (Excl. 5% UAE VAT) and reflect live UAE market averages synced from market sources. Final supplier quotations vary by volume, specifications, delivery terms, and site access — always confirm official quotations before tender submission.'}
        </p>
      </div>

      <style>{`
        .spin-anim { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
