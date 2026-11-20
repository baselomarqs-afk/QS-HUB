// الرسوم البيانية للتدفق النقدي — Zero-dependency responsive SVG charts:
//  (1) S-Curve: Cumulative Planned Value vs Cumulative Received (Excl. VAT) vs Cumulative Expenditure
//  (2) Cash Flow Profile: Monthly Cash In vs Out bars + Cumulative Cash Flow curve with zero baseline
import { useState } from 'react';
import { fmtAed } from '../engine/cashflow';

function compactAed(v) {
  const abs = Math.abs(v);
  const sign = v < 0 ? '-' : '';
  if (abs >= 1_000_000) return `${sign}${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}${(abs / 1_000).toFixed(0)}k`;
  return `${Math.round(v)}`;
}

function buildPolyline(points) {
  return points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
}

export default function CashFlowCharts({ rows, summary, isArabic }) {
  const t = (en, ar) => (isArabic ? ar : en);
  const [hoverSC, setHoverSC] = useState(null);
  const [hoverCF, setHoverCF] = useState(null);

  if (!rows || rows.length < 2) return null;

  const W = 540;
  const H = 240;
  const pad = { top: 20, right: 18, bottom: 38, left: 56 };
  const plotW = W - pad.left - pad.right;
  const plotH = H - pad.top - pad.bottom;
  const n = rows.length;
  const xFor = (i) => pad.left + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2);

  // ---- Chart 1: S-Curve (Cumulative Planned / Received Excl. VAT / Expenditure) ----
  const maxSC = Math.max(
    summary.contractValue || 1,
    ...rows.map((r) => Math.max(r.cumulPlanned || 0, r.cumulReceivedExclVat ?? r.cumulReceived ?? 0, r.cumulExpenditure || 0)),
  ) * 1.08;
  const ySC = (v) => pad.top + plotH - (Math.max(0, v) / maxSC) * plotH;

  const plannedPts = rows.map((r, i) => ({ x: xFor(i), y: ySC(r.cumulPlanned) }));
  const rcvdPts = rows.map((r, i) => ({ x: xFor(i), y: ySC(r.cumulReceivedExclVat ?? r.cumulReceived) }));
  const expPts = rows.map((r, i) => ({ x: xFor(i), y: ySC(r.cumulExpenditure ?? 0) }));
  const scTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({ val: maxSC * f, y: ySC(maxSC * f) }));

  // ---- Chart 2: Monthly Cash In / Out + Cumulative Cash Flow ----
  const cfVals = rows.flatMap((r) => [
    r.cumulCashflow,
    r.paymentReceivedExclVat ?? r.paymentReceived,
    -(r.expenditure || 0),
  ]);
  const maxCF = Math.max(1000, ...cfVals) * 1.12;
  const minCF = Math.min(-1000, ...cfVals) * 1.15;
  const spanCF = Math.max(1, maxCF - minCF);
  const yCF = (v) => pad.top + ((maxCF - v) / spanCF) * plotH;
  const yZero = yCF(0);
  const cumCFPts = rows.map((r, i) => ({ x: xFor(i), y: yCF(r.cumulCashflow) }));
  const cfTicks = [minCF, minCF / 2, 0, maxCF / 2, maxCF].map((val) => ({ val, y: yCF(val) }));
  const barW = Math.max(3, Math.min(12, (plotW / n) * 0.36));

  // X-axis label stride so labels never overlap
  const labelStride = Math.max(1, Math.ceil(n / 8));

  const boxStyle = {
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-color)',
    borderRadius: 12,
    padding: '14px 16px',
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 16, marginBottom: 20 }}>
      {/* Chart 1: Construction S-Curve */}
      <div style={boxStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
          <strong style={{ color: 'var(--text-primary)', fontSize: '0.92rem' }}>
            📈 {t('S-Curve — Cumulative Progress & Cash (AED)', 'منحنى S-Curve — الإنجاز والتدفق التراكمي (درهم)')}
          </strong>
          <div style={{ display: 'flex', gap: 10, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span style={{ color: '#3b82f6' }}>● {t('Planned', 'المخطط')}</span>
            <span style={{ color: '#10b981' }}>● {t('Received', 'المستلم')}</span>
            <span style={{ color: '#f59e0b' }}>● {t('Cost', 'التكلفة')}</span>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block', direction: 'ltr' }}>
          {scTicks.map((tk, idx) => (
            <g key={idx}>
              <line x1={pad.left} y1={tk.y} x2={W - pad.right} y2={tk.y} stroke="var(--border-color)" strokeDasharray="3,3" />
              <text x={pad.left - 8} y={tk.y + 3} textAnchor="end" fontSize="10" fill="var(--text-muted)">
                {compactAed(tk.val)}
              </text>
            </g>
          ))}

          <polyline fill="none" stroke="#3b82f6" strokeWidth="2.4" points={buildPolyline(plannedPts)} />
          <polyline fill="none" stroke="#10b981" strokeWidth="2.4" points={buildPolyline(rcvdPts)} />
          <polyline fill="none" stroke="#f59e0b" strokeWidth="2" strokeDasharray="5,3" points={buildPolyline(expPts)} />

          {rows.map((r, i) => {
            const x = xFor(i);
            const showLbl = i === 0 || i === n - 1 || i % labelStride === 0;
            return (
              <g key={r.monthNumber} onMouseEnter={() => setHoverSC(i)} onMouseLeave={() => setHoverSC(null)}>
                <rect x={x - plotW / (2 * n)} y={pad.top} width={plotW / n} height={plotH} fill="transparent" style={{ cursor: 'crosshair' }} />
                {showLbl && (
                  <text x={x} y={H - 12} textAnchor="middle" fontSize="9.5" fill="var(--text-muted)">
                    M{r.monthNumber}
                  </text>
                )}
              </g>
            );
          })}

          {hoverSC !== null && rows[hoverSC] && (
            <g>
              <line x1={xFor(hoverSC)} y1={pad.top} x2={xFor(hoverSC)} y2={pad.top + plotH} stroke="var(--text-muted)" strokeDasharray="2,2" />
              <circle cx={plannedPts[hoverSC].x} cy={plannedPts[hoverSC].y} r="4" fill="#3b82f6" />
              <circle cx={rcvdPts[hoverSC].x} cy={rcvdPts[hoverSC].y} r="4" fill="#10b981" />
              <circle cx={expPts[hoverSC].x} cy={expPts[hoverSC].y} r="4" fill="#f59e0b" />
            </g>
          )}
        </svg>

        <div style={{ minHeight: 20, fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: 4, textAlign: 'center' }}>
          {hoverSC !== null && rows[hoverSC] ? (
            <>
              <strong>M{rows[hoverSC].monthNumber} ({rows[hoverSC].monthLabel})</strong> —{' '}
              <span style={{ color: '#3b82f6' }}>{t('Planned', 'المخطط')}: {fmtAed(rows[hoverSC].cumulPlanned)}</span> •{' '}
              <span style={{ color: '#10b981' }}>{t('Received', 'المستلم')}: {fmtAed(rows[hoverSC].cumulReceivedExclVat ?? rows[hoverSC].cumulReceived)}</span> •{' '}
              <span style={{ color: '#f59e0b' }}>{t('Cost', 'التكلفة')}: {fmtAed(rows[hoverSC].cumulExpenditure ?? 0)}</span>
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>{t('Hover over any month to inspect values (Excl. VAT)', 'مرّر المؤشر على أي شهر لعرض القيم (بدون الضريبة)')}</span>
          )}
        </div>
      </div>

      {/* Chart 2: Monthly In/Out & Cumulative Cash Flow */}
      <div style={boxStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
          <strong style={{ color: 'var(--text-primary)', fontSize: '0.92rem' }}>
            💸 {t('Monthly Cash In / Out & Cumulative Cash Flow', 'التدفق الشهري (داخل/خارج) والرصيد التراكمي')}
          </strong>
          <div style={{ display: 'flex', gap: 10, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <span style={{ color: '#10b981' }}>■ {t('Cash In', 'وارد')}</span>
            <span style={{ color: '#ef4444' }}>■ {t('Cost Out', 'منصرف')}</span>
            <span style={{ color: '#8b5cf6' }}>● {t('Cumulative', 'تراكمي')}</span>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto', display: 'block', direction: 'ltr' }}>
          {cfTicks.map((tk, idx) => (
            <g key={idx}>
              <line
                x1={pad.left} y1={tk.y} x2={W - pad.right} y2={tk.y}
                stroke={tk.val === 0 ? 'var(--text-secondary)' : 'var(--border-color)'}
                strokeWidth={tk.val === 0 ? 1.4 : 1}
                strokeDasharray={tk.val === 0 ? '' : '3,3'}
              />
              <text x={pad.left - 8} y={tk.y + 3} textAnchor="end" fontSize="10" fill="var(--text-muted)">
                {compactAed(tk.val)}
              </text>
            </g>
          ))}

          {rows.map((r, i) => {
            const x = xFor(i);
            const cashIn = r.paymentReceivedExclVat ?? r.paymentReceived ?? 0;
            const cashOut = r.expenditure || 0;
            const inH = Math.max(0, yZero - yCF(cashIn));
            const outH = Math.max(0, yCF(-cashOut) - yZero);
            const showLbl = i === 0 || i === n - 1 || i % labelStride === 0;
            return (
              <g key={r.monthNumber} onMouseEnter={() => setHoverCF(i)} onMouseLeave={() => setHoverCF(null)}>
                {inH > 0 && <rect x={x - barW} y={yZero - inH} width={barW} height={inH} fill="rgba(16,185,129,0.55)" rx="1" />}
                {outH > 0 && <rect x={x} y={yZero} width={barW} height={outH} fill="rgba(239,68,68,0.55)" rx="1" />}
                <rect x={x - plotW / (2 * n)} y={pad.top} width={plotW / n} height={plotH} fill="transparent" style={{ cursor: 'crosshair' }} />
                {showLbl && (
                  <text x={x} y={H - 12} textAnchor="middle" fontSize="9.5" fill="var(--text-muted)">
                    M{r.monthNumber}
                  </text>
                )}
              </g>
            );
          })}

          <polyline fill="none" stroke="#8b5cf6" strokeWidth="2.5" points={buildPolyline(cumCFPts)} />

          {/* Peak Deficit marker */}
          {summary.peakNegativeMonth > 0 && cumCFPts[summary.peakNegativeMonth] && (
            <circle
              cx={cumCFPts[summary.peakNegativeMonth].x}
              cy={cumCFPts[summary.peakNegativeMonth].y}
              r="4.5"
              fill="#ef4444"
              stroke="#fff"
              strokeWidth="1.5"
            />
          )}

          {hoverCF !== null && rows[hoverCF] && (
            <g>
              <line x1={xFor(hoverCF)} y1={pad.top} x2={xFor(hoverCF)} y2={pad.top + plotH} stroke="var(--text-muted)" strokeDasharray="2,2" />
              <circle cx={cumCFPts[hoverCF].x} cy={cumCFPts[hoverCF].y} r="4.5" fill="#8b5cf6" />
            </g>
          )}
        </svg>

        <div style={{ minHeight: 20, fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: 4, textAlign: 'center' }}>
          {hoverCF !== null && rows[hoverCF] ? (
            <>
              <strong>M{rows[hoverCF].monthNumber} ({rows[hoverCF].monthLabel})</strong> —{' '}
              <span style={{ color: '#10b981' }}>{t('In', 'وارد')}: {fmtAed(rows[hoverCF].paymentReceivedExclVat ?? rows[hoverCF].paymentReceived)}</span> •{' '}
              <span style={{ color: '#ef4444' }}>{t('Out', 'منصرف')}: {fmtAed(rows[hoverCF].expenditure)}</span> •{' '}
              <span style={{ color: rows[hoverCF].cumulCashflow < 0 ? '#ef4444' : '#8b5cf6', fontWeight: 700 }}>
                {t('Cum.', 'تراكمي')}: {fmtAed(rows[hoverCF].cumulCashflow)} AED
              </span>
            </>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>
              {summary.peakNegativeMonth > 0
                ? t(`Red dot = Peak Deficit at M${summary.peakNegativeMonth} (${fmtAed(summary.workingCapitalRequired)} AED)`, `النقطة الحمراء = أقصى عجز في M${summary.peakNegativeMonth} (${fmtAed(summary.workingCapitalRequired)} درهم)`)
                : t('Positive cash flow across all months', 'تدفق نقدي موجب طوال المشروع')}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
