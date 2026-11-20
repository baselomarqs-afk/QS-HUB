// محرك التدفق النقدي — UAE / FIDIC-compliant Cash Flow Engine.
// Features:
//  • Pro-rata advance payment recovery (never produces negative IPCs or negative VAT)
//  • Full UAE FTA 5% VAT accounting (VAT on Advance, Monthly Net IPCs, PC & DLP Retention Releases = exact 5% of CV)
//  • Output VAT pass-through remitted to FTA (so contractor cash/profit & working capital are never inflated by tax money)
//  • Exact separation of delayed regular IPCs vs Practical Completion & DLP retention releases

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
  const months = Object.keys(monthlyPlanned || {}).sort();
  const n = months.length;
  const startParts = (cfg.startISO || "").split("-").map(Number);
  const sy = startParts[0] || new Date().getFullYear();
  const sm = startParts[1] || 1;
  const startDate = new Date(sy, sm - 1, 1);

  const cv = Math.max(0, Number(cfg.contractValueAed) || 0);
  const advPct = Math.max(0, Math.min(100, Number(cfg.advancePaymentPct) || 0));
  const retPct = Math.max(0, Math.min(100, Number(cfg.retentionPct) || 0));
  const retPcPct = Math.max(0, Math.min(100, Number(cfg.retentionReleaseAtCompletionPct) || 0));
  const vatPct = Math.max(0, Math.min(100, Number(cfg.vatPct) || 0));
  const certDays = Math.max(0, Number(cfg.certificationPeriodDays) || 0);
  const payDays = Math.max(0, Number(cfg.paymentPeriodDays) || 0);
  const dlpMonths = Math.max(0, Math.round(Number(cfg.defectsLiabilityMonths) || 0));
  const costRatio = Math.max(0, Math.min(2, Number(cfg.contractorCostRatio) || 0));

  const paymentDelay = certDays + payDays > 0 ? Math.ceil((certDays + payDays) / 30) : 0;
  const advance = (cv * advPct) / 100;
  const vatOnAdvance = (advance * vatPct) / 100;

  // Separate cash inflow buckets so regular delayed IPCs are NEVER mislabelled as retention
  const ipcExclVatInflow = {};
  const ipcVatInflow = {};
  const retExclVatInflow = {};
  const retVatInflow = {};
  const retEvents = {}; // monthNum -> Set("pc" | "dlp")

  const addBucket = (map, idx, amt) => {
    map[idx] = (map[idx] ?? 0) + amt;
  };
  const markRetEvent = (idx, tag) => {
    if (!retEvents[idx]) retEvents[idx] = new Set();
    retEvents[idx].add(tag);
  };

  // Find last construction month with positive planned value to clear any sub-fils advance residual cleanly
  let lastActiveMonthIdx = -1;
  for (let i = n - 1; i >= 0; i--) {
    if ((monthlyPlanned[months[i]] ?? 0) > 0.01) {
      lastActiveMonthIdx = i;
      break;
    }
  }

  const bills = [];
  let advanceOutstanding = advance;
  let totalRetention = 0;
  let totalVatOnCerts = 0;

  months.forEach((ym, i) => {
    const monthNum = i + 1;
    const pv = Math.max(0, monthlyPlanned[ym] ?? 0);
    const retention = (pv * retPct) / 100;

    // Standard UAE / FIDIC pro-rata advance recovery: advance% of each IPC, never exceeding remaining advance or (pv - retention)
    let recovery = 0;
    if (pv > 0 && advanceOutstanding > 0) {
      const proRata = (pv * advPct) / 100;
      const maxSafe = Math.max(0, pv - retention);
      if (i === lastActiveMonthIdx && advanceOutstanding <= maxSafe) {
        recovery = advanceOutstanding;
      } else {
        recovery = Math.min(proRata, advanceOutstanding, maxSafe);
      }
      advanceOutstanding = Math.max(0, advanceOutstanding - recovery);
    }

    const net = Math.max(0, pv - retention - recovery);
    const vat = (net * vatPct) / 100;
    totalRetention += retention;
    totalVatOnCerts += vat;

    bills.push({ pv, gross: pv, retention, recovery, net, vat });
    addBucket(ipcExclVatInflow, monthNum + paymentDelay, net);
    addBucket(ipcVatInflow, monthNum + paymentDelay, vat);
  });

  // Retention releases (UAE FTA: 5% VAT is due upon retention invoicing/release)
  const retAtPc = (totalRetention * retPcPct) / 100;
  const retAtDlp = Math.max(0, totalRetention - retAtPc);
  const vatOnRetPc = (retAtPc * vatPct) / 100;
  const vatOnRetDlp = (retAtDlp * vatPct) / 100;

  const pcReleaseMonth = n + paymentDelay;
  const dlpReleaseMonth = n + dlpMonths;

  if (retAtPc > 0) {
    addBucket(retExclVatInflow, pcReleaseMonth, retAtPc);
    addBucket(retVatInflow, pcReleaseMonth, vatOnRetPc);
    markRetEvent(pcReleaseMonth, "pc");
  }
  if (retAtDlp > 0) {
    addBucket(retExclVatInflow, dlpReleaseMonth, retAtDlp);
    addBucket(retVatInflow, dlpReleaseMonth, vatOnRetDlp);
    markRetEvent(dlpReleaseMonth, "dlp");
  }

  const allMonths = [
    n + paymentDelay,
    n + dlpMonths,
    ...Object.keys(ipcExclVatInflow).map(Number),
    ...Object.keys(retExclVatInflow).map(Number),
  ];
  const lastMonth = Math.max(n, ...allMonths.filter((x) => Number.isFinite(x)));

  const rows = [];

  // Month 0: Advance Payment (Client pays Advance + VAT; Output VAT is pass-through to FTA)
  const advInclVat = advance + vatOnAdvance;
  rows.push({
    monthNumber: 0,
    monthLabel: "Advance",
    plannedValue: 0,
    cumulPlanned: 0,
    advanceReceived: round2(advance),
    advanceRecovery: 0,
    grossCertificate: 0,
    retentionDeducted: 0,
    retentionReleased: 0,
    netCertificate: round2(advance),
    vatOnCert: round2(vatOnAdvance),
    vatRemitted: round2(vatOnAdvance),
    paymentReceivedExclVat: round2(advance),
    paymentReceived: round2(advInclVat),
    cumulReceivedExclVat: round2(advance),
    cumulReceived: round2(advInclVat),
    expenditure: 0,
    cumulExpenditure: 0,
    netCashflow: round2(advance),
    cumulCashflow: round2(advance),
    progressPct: 0,
    cumulProgressPct: 0,
    isRetentionRelease: false,
    retentionTag: "",
  });

  let cumulPlanned = 0;
  let cumulReceivedExclVat = advance;
  let cumulReceived = advInclVat;
  let cumulExpenditure = 0;
  let cumulCashflow = advance;
  let cumulProgress = 0;
  let totalExpenditure = 0;
  let peakNeg = cumulCashflow;
  let peakNegMonth = 0;

  for (let monthNum = 1; monthNum <= lastMonth; monthNum++) {
    const bill = monthNum <= n ? bills[monthNum - 1] : undefined;
    const pv = bill?.pv ?? 0;
    const progress = cv > 0 ? (pv / cv) * 100 : 0;
    cumulPlanned += pv;
    cumulProgress += progress;

    const expenditure = pv * costRatio;
    totalExpenditure += expenditure;
    cumulExpenditure += expenditure;

    const ipcExcl = ipcExclVatInflow[monthNum] ?? 0;
    const ipcVat = ipcVatInflow[monthNum] ?? 0;
    const retExcl = retExclVatInflow[monthNum] ?? 0;
    const retVat = retVatInflow[monthNum] ?? 0;

    const receivedExclVat = ipcExcl + retExcl;
    const receivedVat = ipcVat + retVat;
    const receivedInclVat = receivedExclVat + receivedVat;

    // VAT collected from client is pass-through to UAE FTA — contractor net cashflow uses Excl. VAT inflows
    // so government VAT is never counted as contractor profit or working capital!
    const vatRemitted = receivedVat;
    cumulReceivedExclVat += receivedExclVat;
    cumulReceived += receivedInclVat;

    const netCashflow = receivedInclVat - expenditure - vatRemitted; // === receivedExclVat - expenditure
    cumulCashflow += netCashflow;

    if (cumulCashflow < peakNeg) {
      peakNeg = cumulCashflow;
      peakNegMonth = monthNum;
    }

    const evSet = retEvents[monthNum];
    const isRetentionRelease = Boolean(evSet && evSet.size > 0);
    let retentionTag = "";
    if (evSet?.has("pc") && evSet?.has("dlp")) retentionTag = "pc_dlp";
    else if (evSet?.has("pc")) retentionTag = "pc";
    else if (evSet?.has("dlp")) retentionTag = "dlp";

    // VAT column shows VAT certified/invoiced in this month (IPC VAT + any retention release VAT)
    const vatBilledThisMonth = (bill?.vat ?? 0) + retVat;

    rows.push({
      monthNumber: monthNum,
      monthLabel: monthLabel(startDate, monthNum - 1),
      plannedValue: round2(pv),
      cumulPlanned: round2(cumulPlanned),
      advanceReceived: 0,
      advanceRecovery: round2(bill?.recovery ?? 0),
      grossCertificate: round2(bill?.gross ?? 0),
      retentionDeducted: round2(bill?.retention ?? 0),
      retentionReleased: round2(retExcl),
      netCertificate: round2((bill?.net ?? 0) + retExcl),
      vatOnCert: round2(vatBilledThisMonth),
      vatRemitted: round2(vatRemitted),
      paymentReceivedExclVat: round2(receivedExclVat),
      paymentReceived: round2(receivedInclVat),
      cumulReceivedExclVat: round2(cumulReceivedExclVat),
      cumulReceived: round2(cumulReceived),
      expenditure: round2(expenditure),
      cumulExpenditure: round2(cumulExpenditure),
      netCashflow: round2(netCashflow),
      cumulCashflow: round2(cumulCashflow),
      progressPct: round2(progress),
      cumulProgressPct: round2(Math.min(cumulProgress, 100)),
      isRetentionRelease,
      retentionTag,
    });
  }

  let paybackMonth = 0;
  if (peakNeg < 0) {
    for (const r of rows) {
      if (r.monthNumber >= peakNegMonth && r.cumulCashflow >= 0) {
        paybackMonth = r.monthNumber;
        break;
      }
    }
  }

  // Detect a SECOND financing trough (the "double dip"): deepest negative point after first recovery
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

  const totalVat = vatOnAdvance + totalVatOnCerts + vatOnRetPc + vatOnRetDlp;
  const totalContractInclVat = cv + totalVat;
  const totalProfit = cv - totalExpenditure;

  const summary = {
    contractValue: round2(cv),
    totalVat: round2(totalVat),
    totalContractInclVat: round2(totalContractInclVat),
    advancePayment: round2(advance),
    advanceVat: round2(vatOnAdvance),
    totalRetentionWithheld: round2(totalRetention),
    retentionAtCompletion: round2(retAtPc),
    retentionAtDlpEnd: round2(retAtDlp),
    peakNegativeCashflow: round2(Math.min(0, peakNeg)),
    peakNegativeMonth: peakNeg < 0 ? peakNegMonth : 0,
    secondTroughCashflow: round2(secondTrough),
    secondTroughMonth,
    hasDoubleDip: secondTroughMonth > 0,
    paybackMonth,
    workingCapitalRequired: round2(Math.max(0, -peakNeg)),
    totalExpenditure: round2(totalExpenditure),
    totalProfit: round2(totalProfit),
    profitMarginPct: cv > 0 ? round2((totalProfit / cv) * 100) : 0,
    constructionMonths: n,
    totalMonths: lastMonth,
  };

  return { rows, summary };
}

/**
 * Standalone monthly planned-value distribution via a smooth construction S-curve.
 * @returns { "YYYY-MM": planned value } summing to the contract value.
 */
export function generateSCurve(contractValue, months, startISO) {
  const monthly = {};
  const m = Math.max(1, Math.round(months));
  const [sy, sm] = (startISO || "").split("-").map(Number);
  let prevCum = 0;
  for (let t = 1; t <= m; t++) {
    const cum = 0.5 * (1 - Math.cos((Math.PI * t) / m));
    const portion = cum - prevCum;
    prevCum = cum;
    const d = new Date(sy || new Date().getFullYear(), (sm || 1) - 1 + (t - 1), 1);
    const ym = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    monthly[ym] = portion * contractValue;
  }
  return monthly;
}

/** Currency formatter for the UAE dirham. */
export function fmtAed(v) {
  return new Intl.NumberFormat("en-AE", { maximumFractionDigits: 0 }).format(Math.round(v || 0));
}
