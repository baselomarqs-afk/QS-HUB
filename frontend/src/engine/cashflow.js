// محرك التدفق النقدي — Turns the schedule's monthly planned values into a
// certified-payment forecast (advance + recovery, retention held/released, VAT,
// payment delay) and derives the working-capital summary. Ported from villa-qto.

function monthLabel(start, offset) {
  const d = new Date(start.getFullYear(), start.getMonth() + offset, 1);
  return d.toLocaleDateString("en-GB", { month: "short", year: "2-digit" }).replace(" ", "-");
}

function round2(v) {
  return Math.round((v + Number.EPSILON) * 100) / 100;
}

/**
 * @param cfg            project configuration (financial terms)
 * @param monthlyPlanned { "YYYY-MM": planned value } from the scheduler
 */
export function computeCashFlow(cfg, monthlyPlanned) {
  const months = Object.keys(monthlyPlanned).sort();
  const n = months.length;
  const [sy, sm] = cfg.startISO.split("-").map(Number);
  const startDate = new Date(sy, (sm || 1) - 1, 1);

  const cv = cfg.contractValueAed;
  const paymentDelay = Math.ceil((cfg.certificationPeriodDays + cfg.paymentPeriodDays) / 30);
  const advance = (cv * cfg.advancePaymentPct) / 100;
  const monthlyRecovery = advance / Math.max(n - 1, 1);
  const dlpMonths = cfg.defectsLiabilityMonths;

  const inflow = {};
  const addInflow = (idx, amt) => { inflow[idx] = (inflow[idx] ?? 0) + amt; };

  const bills = [];
  let advanceOutstanding = advance;
  let totalRetention = 0;
  months.forEach((ym, i) => {
    const monthNum = i + 1;
    const pv = monthlyPlanned[ym] ?? 0;
    const retention = (pv * cfg.retentionPct) / 100;
    const recovery = monthNum > 1 ? Math.min(monthlyRecovery, advanceOutstanding) : 0;
    advanceOutstanding -= recovery;
    const net = pv - retention - recovery;
    const vat = (net * cfg.vatPct) / 100;
    totalRetention += retention;
    bills.push({ pv, gross: pv, retention, recovery, net, vat });
    addInflow(monthNum + paymentDelay, net + vat);
  });

  const retAtPc = (totalRetention * cfg.retentionReleaseAtCompletionPct) / 100;
  const retAtDlp = totalRetention - retAtPc;
  addInflow(n + paymentDelay, retAtPc);
  addInflow(n + dlpMonths, retAtDlp);

  const lastMonth = Math.max(n + paymentDelay, n + dlpMonths, ...Object.keys(inflow).map(Number));

  const rows = [];

  rows.push({
    monthNumber: 0, monthLabel: "Advance",
    plannedValue: 0, cumulPlanned: 0,
    advanceReceived: round2(advance), advanceRecovery: 0,
    grossCertificate: 0, retentionDeducted: 0, netCertificate: 0, vatOnCert: 0,
    paymentReceived: round2(advance), cumulReceived: round2(advance),
    expenditure: 0, netCashflow: round2(advance), cumulCashflow: round2(advance),
    progressPct: 0, cumulProgressPct: 0,
    isRetentionRelease: false,
  });

  let cumulPlanned = 0;
  let cumulReceived = advance;
  let cumulCashflow = advance;
  let cumulProgress = 0;
  let totalExpenditure = 0;
  let totalVat = 0;
  let peakNeg = cumulCashflow;
  let peakNegMonth = 0;

  for (let monthNum = 1; monthNum <= lastMonth; monthNum++) {
    const bill = monthNum <= n ? bills[monthNum - 1] : undefined;
    const pv = bill?.pv ?? 0;
    const progress = cv ? (pv / cv) * 100 : 0;
    cumulPlanned += pv;
    cumulProgress += progress;

    const expenditure = pv * cfg.contractorCostRatio;
    totalExpenditure += expenditure;
    const received = inflow[monthNum] ?? 0;
    cumulReceived += received;
    const netCashflow = received - expenditure;
    cumulCashflow += netCashflow;
    if (bill) totalVat += bill.vat;

    if (cumulCashflow < peakNeg) { peakNeg = cumulCashflow; peakNegMonth = monthNum; }

    // A month past construction that still receives money is a retention release.
    const isRetentionRelease = monthNum > n && received > 0;

    rows.push({
      monthNumber: monthNum,
      monthLabel: monthLabel(startDate, monthNum - 1),
      plannedValue: round2(pv),
      cumulPlanned: round2(cumulPlanned),
      advanceReceived: 0,
      advanceRecovery: round2(bill?.recovery ?? 0),
      grossCertificate: round2(bill?.gross ?? 0),
      retentionDeducted: round2(bill?.retention ?? 0),
      netCertificate: round2(bill?.net ?? 0),
      vatOnCert: round2(bill?.vat ?? 0),
      paymentReceived: round2(received),
      cumulReceived: round2(cumulReceived),
      expenditure: round2(expenditure),
      netCashflow: round2(netCashflow),
      cumulCashflow: round2(cumulCashflow),
      progressPct: round2(progress),
      cumulProgressPct: round2(Math.min(cumulProgress, 100)),
      isRetentionRelease,
    });
  }

  let paybackMonth = 0;
  for (const r of rows) {
    if (r.monthNumber >= peakNegMonth && r.cumulCashflow >= 0) { paybackMonth = r.monthNumber; break; }
  }

  // Detect a SECOND financing trough (the "double dip"): the deepest negative
  // point that occurs after the cash flow first recovers past the main trough.
  let secondTrough = 0;
  let secondTroughMonth = 0;
  let recoveredOnce = false;
  for (const r of rows) {
    if (r.monthNumber <= peakNegMonth) continue;
    if (r.cumulCashflow >= 0) recoveredOnce = true;
    if (recoveredOnce && r.cumulCashflow < 0 && r.cumulCashflow < secondTrough) {
      secondTrough = r.cumulCashflow;
      secondTroughMonth = r.monthNumber;
    }
  }

  const totalProfit = cv - totalExpenditure;
  const summary = {
    contractValue: round2(cv),
    totalVat: round2(totalVat),
    advancePayment: round2(advance),
    totalRetentionWithheld: round2(totalRetention),
    retentionAtCompletion: round2(retAtPc),
    retentionAtDlpEnd: round2(retAtDlp),
    peakNegativeCashflow: round2(peakNeg),
    peakNegativeMonth: peakNegMonth,
    secondTroughCashflow: round2(secondTrough),
    secondTroughMonth,
    hasDoubleDip: secondTroughMonth > 0,
    paybackMonth,
    workingCapitalRequired: round2(Math.max(0, -peakNeg)),
    totalExpenditure: round2(totalExpenditure),
    totalProfit: round2(totalProfit),
    profitMarginPct: cv ? round2((totalProfit / cv) * 100) : 0,
    constructionMonths: n,
    totalMonths: lastMonth,
  };

  return { rows, summary };
}

/**
 * Standalone monthly planned-value distribution via a smooth construction
 * S-curve — used so the Cash Flow window is INDEPENDENT of the Work Programme.
 * Cumulative % at month t follows 0.5·(1 − cos(π·t/M)); monthly = the increment.
 * @returns { "YYYY-MM": planned value } summing to the contract value.
 */
export function generateSCurve(contractValue, months, startISO) {
  const monthly = {};
  const m = Math.max(1, Math.round(months));
  const [sy, sm] = startISO.split("-").map(Number);
  let prevCum = 0;
  for (let t = 1; t <= m; t++) {
    const cum = 0.5 * (1 - Math.cos((Math.PI * t) / m));
    const portion = cum - prevCum;
    prevCum = cum;
    const d = new Date(sy, (sm || 1) - 1 + (t - 1), 1);
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    monthly[ym] = portion * contractValue;
  }
  return monthly;
}

/** Currency formatter for the UAE dirham. */
export function fmtAed(v) {
  return new Intl.NumberFormat("en-AE", { maximumFractionDigits: 0 }).format(Math.round(v));
}
