import React, { useState, useEffect } from 'react';
import { Search, MapPin, RefreshCw, BarChart2 } from 'lucide-react';

export default function MarketPrices({ token, isArabic }) {
  const [prices, setPrices] = useState([]);
  const [categories, setCategories] = useState({});
  const [emirates, setEmirates] = useState({});
  
  const [selectedCat, setSelectedCat] = useState('all');
  const [selectedEm, setSelectedEm] = useState('dubai');
  const [searchQuery, setSearchQuery] = useState('');
  const [compareMode, setCompareMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchPrices();
  }, [selectedCat, selectedEm, searchQuery, compareMode]);

  const fetchPrices = async () => {
    setLoading(true);
    try {
      const url = `/api/market/prices?category=${selectedCat}&emirate=${selectedEm}&search=${searchQuery}&compare=${compareMode}`;
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (res.ok) {
        setPrices(data.prices || []);
        setCategories(data.categories || {});
        setEmirates(data.emirates || {});
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleForceUpdate = async () => {
    setMessage('');
    setLoading(true);
    try {
      const res = await fetch("/api/market/prices/update", {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      if (data.ok) {
        setMessage(isArabic ? 'تم تحديث الأسعار أسبوعياً بنجاح!' : 'Weekly prices updated successfully!');
        fetchPrices();
      } else {
        setMessage(data.message);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '30px', textAlign: isArabic ? 'right' : 'left', direction: isArabic ? 'rtl' : 'ltr' }}>
      {/* Title Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '25px' }}>
        <div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.8rem', fontWeight: 800, color: 'var(--primary)' }}>
            {isArabic ? 'أسعار السوق (الإمارات)' : 'Market Prices (UAE)'}
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            {isArabic ? 'أسعار مباشرة ومؤتمتة لمواد البناء وأجور العمالة يغذيها وكيل الذكاء الاصطناعي.' : 'Live, automated construction material and labor rates driven by AI.'}
          </p>
        </div>
        <button className="btn btn-secondary" onClick={handleForceUpdate} disabled={loading} style={{ gap: '8px' }}>
          <RefreshCw size={16} className={loading ? 'spin-anim' : ''} />
          {isArabic ? 'تحديث الأسعار' : 'Sync Prices'}
        </button>
      </div>

      {message && (
        <div style={{ padding: '12px 16px', backgroundColor: 'rgba(16,185,129,0.1)', color: 'var(--success)', borderRadius: '8px', marginBottom: '20px', fontSize: '0.9rem' }}>
          {message}
        </div>
      )}

      {/* Filters Grid */}
      <div className="glass-panel" style={{ padding: '20px', display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '15px', marginBottom: '30px', alignItems: 'center' }}>
        {/* Search */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="form-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={isArabic ? 'البحث عن المواد...' : 'Search materials...'}
            style={{ paddingLeft: isArabic ? '16px' : '40px', paddingRight: isArabic ? '40px' : '16px' }}
          />
          <Search size={18} style={{
            position: 'absolute',
            top: '50%',
            transform: 'translateY(-50%)',
            left: isArabic ? 'auto' : '14px',
            right: isArabic ? '14px' : 'auto',
            color: 'var(--text-muted)'
          }} />
        </div>

        {/* Category */}
        <select 
          className="form-input"
          value={selectedCat}
          onChange={(e) => setSelectedCat(e.target.value)}
        >
          {Object.entries(categories).map(([key, val]) => (
            <option key={key} value={key}>{isArabic ? val.ar : val.en}</option>
          ))}
        </select>

        {/* Emirate */}
        <select 
          className="form-input"
          value={selectedEm}
          disabled={compareMode}
          onChange={(e) => setSelectedEm(e.target.value)}
        >
          {Object.entries(emirates).map(([key, val]) => (
            <option key={key} value={key}>{isArabic ? val.ar : val.en}</option>
          ))}
        </select>

        {/* Compare Checkbox */}
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          <input 
            type="checkbox"
            checked={compareMode}
            onChange={(e) => setCompareMode(e.target.checked)}
            style={{ width: '18px', height: '18px' }}
          />
          <BarChart2 size={16} />
          {isArabic ? 'مقارنة الإمارات' : 'Compare Emirates'}
        </label>
      </div>

      {/* Table Data */}
      {loading && prices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <div className="spin-anim" style={{ width: '40px', height: '40px', border: '4px solid var(--border-color)', borderTopColor: 'var(--primary)', borderRadius: '50%', margin: '0 auto 15px' }}></div>
          <p>{isArabic ? 'جاري تحميل أسعار المواد...' : 'Loading market rates...'}</p>
        </div>
      ) : prices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '50px', backgroundColor: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
          <p style={{ color: 'var(--text-secondary)' }}>{isArabic ? 'لا توجد نتائج تطابق معايير البحث.' : 'No materials found matching criteria.'}</p>
        </div>
      ) : (
        <div className="premium-table-container">
          <table className="premium-table">
            <thead>
              <tr>
                <th style={{ width: '10%' }}>{isArabic ? 'الرمز' : 'Code'}</th>
                <th style={{ width: '40%' }}>{isArabic ? 'المادة' : 'Material'}</th>
                <th style={{ width: '10%' }}>{isArabic ? 'الوحدة' : 'Unit'}</th>
                {compareMode ? (
                  <>
                    <th>{isArabic ? 'دبي' : 'Dubai'}</th>
                    <th>{isArabic ? 'أبو ظبي' : 'Abu Dhabi'}</th>
                    <th>{isArabic ? 'الشارقة' : 'Sharjah'}</th>
                    <th>{isArabic ? 'عجمان' : 'Ajman'}</th>
                  </>
                ) : (
                  <th>{isArabic ? 'السعر (درهم)' : 'Price (AED)'}</th>
                )}
                <th>{isArabic ? 'الدقة' : 'Accuracy'}</th>
                <th>{isArabic ? 'آخر تحقق' : 'Verified'}</th>
              </tr>
            </thead>
            <tbody>
              {prices.map((item, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{item.code}</td>
                  <td style={{ color: 'var(--text-primary)' }}>{isArabic ? item.name_ar : item.name_en}</td>
                  <td>{item.unit}</td>
                  {compareMode ? (
                    <>
                      <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{item.prices.dubai.toFixed(2)}</td>
                      <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{item.prices.abudhabi.toFixed(2)}</td>
                      <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{item.prices.sharjah.toFixed(2)}</td>
                      <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{item.prices.ajman.toFixed(2)}</td>
                    </>
                  ) : (
                    <td style={{ color: 'var(--primary)', fontWeight: 600 }}>{item.price.toFixed(2)}</td>
                  )}
                  <td>
                    <span style={{
                      backgroundColor: 'rgba(16,185,129,0.1)',
                      color: 'var(--success)',
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '0.8rem',
                      fontWeight: 600
                    }}>
                      {item.accuracy}%
                    </span>
                  </td>
                  <td style={{ fontSize: '0.85rem' }}>{item.last_verified}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Disclaimer Banner */}
      <div className="glass-panel" style={{
        marginTop: '30px',
        padding: '16px 20px',
        borderLeft: isArabic ? 'none' : '4px solid var(--warning)',
        borderRight: isArabic ? '4px solid var(--warning)' : 'none',
        backgroundColor: 'rgba(245, 158, 11, 0.05)',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
      }}>
        <h5 style={{ fontWeight: 700, color: 'var(--warning)', fontSize: '0.95rem' }}>
          ⚠️ {isArabic ? 'إخلاء مسؤولية هام' : 'Important Disclaimer'}
        </h5>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          {isArabic 
            ? 'الأسعار المعروضة هنا هي أسعار إرشادية تقريبية مبنية على معدلات السوق الإماراتية. قد تختلف الأسعار الفعلية حسب الكميات، وموردي المواد، وموقع المشروع والتسليم. يرجى دائماً التحقق من الأسعار مباشرة قبل اتخاذ القرارات النهائية للعقود.'
            : 'Prices shown are approximate and represent average UAE market rates. Actual costs will vary based on project scale, bulk volumes, custom specifications, delivery terms, and specific supplier quotations. Always confirm final prices directly before bidding.'
          }
        </p>
      </div>

      <style>{`
        .spin-anim {
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
