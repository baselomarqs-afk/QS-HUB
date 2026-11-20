// تصدير التدفق النقدي — Full UAE FTA-reconciled Cash Flow & S-Curve Excel export.
// Lazy-imported so xlsx stays out of the main bundle.
import * as XLSX from "xlsx-js-style";

const NAVY = "1A3C5E";
const SECTION = "2D6A9F";
const WHITE = "FFFFFF";
const RET_BG = "E8F1FA";

const headerStyle = {
  fill: { fgColor: { rgb: NAVY } },
  font: { color: { rgb: WHITE }, bold: true },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
};
const titleStyle = { font: { bold: true, sz: 15, color: { rgb: NAVY } }, alignment: { horizontal: "center" } };
const labelStyle = { font: { bold: true, color: { rgb: NAVY } } };
const totalStyle = { fill: { fgColor: { rgb: SECTION } }, font: { color: { rgb: WHITE }, bold: true } };
const numStyle = { alignment: { horizontal: "right" }, numFmt: "#,##0" };
const pctStyle = { alignment: { horizontal: "right" }, numFmt: "0.0%" };

function periodSuffix(m) {
  if (!m.isRetentionRelease) return "";
  if (m.retentionTag === "pc_dlp") return " (PC + DLP Ret.)";
  if (m.retentionTag === "pc") return " (PC Retention)";
  if (m.retentionTag === "dlp") return " (DLP Retention)";
  return " (Retention)";
}

export function exportCashFlowToExcel(cfg, result, projectName) {
  const headers = [
    "#",
    "Period",
    "Planned Value",
    "Cum %",
    "Adv. Recovery",
    "Ret. Held",
    "Ret. Released",
    "Net Cert. (Ex. VAT)",
    `VAT (${cfg.vatPct ?? 5}%)`,
    "Received (Inc. VAT)",
    "VAT to FTA",
    "Expenditure",
    "Net Cashflow",
    "Cumulative CF",
  ];
  const lastCol = headers.length - 1;
  const { summary } = result;

  const grid = [];
  const merges = [];

  grid.push([{ v: `Cash-Flow Forecast (UAE FTA Reconciled) — ${projectName}`, s: titleStyle }]);
  merges.push({ s: { r: 0, c: 0 }, e: { r: 0, c: lastCol } });

  const info = [
    ["Contract Value Excl. VAT (AED)", summary.contractValue],
    [`Total VAT @ ${cfg.vatPct ?? 5}% (AED)`, summary.totalVat],
    ["Total Contract Incl. VAT (AED)", summary.totalContractInclVat ?? (summary.contractValue + summary.totalVat)],
    ["Advance Payment Excl. VAT (AED)", summary.advancePayment],
    ["Total Retention Held (AED)", summary.totalRetentionWithheld],
    ["Retention @ Practical Completion (AED)", summary.retentionAtCompletion],
    ["Retention @ End of DLP (AED)", summary.retentionAtDlpEnd],
    ["Working Capital Required (AED)", summary.workingCapitalRequired],
    ["Peak Deficit Month", summary.peakNegativeMonth ? `M${summary.peakNegativeMonth}` : "None"],
    ["2nd Trough Month", summary.secondTroughMonth ? `M${summary.secondTroughMonth}` : "—"],
    ["Payback Month", summary.paybackMonth ? `M${summary.paybackMonth}` : "—"],
    ["Total Expenditure (AED)", summary.totalExpenditure],
    ["Gross Profit (AED)", summary.totalProfit],
    ["Profit Margin %", summary.profitMarginPct],
  ];
  if (Array.isArray(cfg.drawings) && cfg.drawings.length > 0) {
    info.push([
      "Reference Drawings",
      cfg.drawings.map((d) => `${d.name} (${d.pages || 1}p)`).join(" | "),
    ]);
  }
  info.forEach(([k, v]) =>
    grid.push([
      { v: k, s: labelStyle },
      { v: typeof v === "number" ? Math.round(v * 100) / 100 : v, s: typeof v === "number" ? numStyle : { alignment: { horizontal: "right" } } },
    ]),
  );
  grid.push([{ v: "" }]);

  grid.push(headers.map((h) => ({ v: h, s: headerStyle })));

  for (const m of result.rows) {
    const rowFill = m.isRetentionRelease ? { fill: { fgColor: { rgb: RET_BG } } } : {};
    const numCell = { ...numStyle, ...rowFill };
    grid.push([
      { v: m.monthNumber, s: { alignment: { horizontal: "center" }, ...rowFill } },
      { v: m.monthLabel + periodSuffix(m), s: { alignment: { horizontal: "center" }, ...rowFill } },
      { v: Math.round(m.plannedValue), s: numCell },
      { v: m.cumulProgressPct / 100, s: { ...pctStyle, ...rowFill } },
      { v: Math.round(m.advanceRecovery), s: numCell },
      { v: Math.round(m.retentionDeducted), s: numCell },
      { v: Math.round(m.retentionReleased ?? 0), s: numCell },
      { v: Math.round(m.netCertificate), s: numCell },
      { v: Math.round(m.vatOnCert), s: numCell },
      { v: Math.round(m.paymentReceived), s: numCell },
      { v: Math.round(m.vatRemitted ?? 0), s: numCell },
      { v: Math.round(m.expenditure), s: numCell },
      { v: Math.round(m.netCashflow), s: numCell },
      {
        v: Math.round(m.cumulCashflow),
        s: { ...numCell, font: { bold: true, color: { rgb: m.cumulCashflow < 0 ? "C00000" : "1B873F" } } },
      },
    ]);
  }

  const sum = (sel) => Math.round(result.rows.reduce((a, m) => a + sel(m), 0));
  const lastRow = result.rows[result.rows.length - 1];
  grid.push([
    { v: "TOTAL", s: totalStyle },
    { v: "", s: totalStyle },
    { v: Math.round(summary.contractValue), s: { ...numStyle, ...totalStyle } },
    { v: 1, s: { ...pctStyle, ...totalStyle } },
    { v: Math.round(summary.advancePayment), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalRetentionWithheld), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.retentionReleased ?? 0), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.contractValue), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalVat), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalContractInclVat ?? (summary.contractValue + summary.totalVat)), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalVat), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalExpenditure), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(summary.totalProfit), s: { ...numStyle, ...totalStyle } },
    { v: Math.round(lastRow?.cumulCashflow ?? summary.totalProfit), s: { ...numStyle, ...totalStyle } },
  ]);

  const ws = XLSX.utils.aoa_to_sheet(grid.map((line) => line.map((c) => c.v)));
  grid.forEach((line, ri) => {
    line.forEach((cell, ci) => {
      const addr = XLSX.utils.encode_cell({ r: ri, c: ci });
      if (ws[addr] && cell.s) ws[addr].s = cell.s;
    });
  });
  ws["!merges"] = merges;
  ws["!cols"] = [5, 22, 14, 8, 13, 12, 13, 16, 12, 17, 12, 14, 14, 15].map((wch) => ({ wch }));

  // Sheet 2: S-Curve & Cumulative Data (ready for native Excel charts)
  const scHeaders = [
    "Month #", "Period", "Monthly Planned", "Cum. Planned (S-Curve)",
    "Cum. Received (Ex. VAT)", "Cum. Expenditure", "Cumulative Cash Flow", "Cum. Progress %",
  ];
  const scGrid = [
    [{ v: `S-Curve & Cash Flow Curves — ${projectName}`, s: titleStyle }],
    scHeaders.map((h) => ({ v: h, s: headerStyle })),
    ...result.rows.map((m) => [
      { v: m.monthNumber, s: { alignment: { horizontal: "center" } } },
      { v: m.monthLabel, s: { alignment: { horizontal: "center" } } },
      { v: Math.round(m.plannedValue), s: numStyle },
      { v: Math.round(m.cumulPlanned), s: numStyle },
      { v: Math.round(m.cumulReceivedExclVat ?? m.cumulReceived), s: numStyle },
      { v: Math.round(m.cumulExpenditure ?? 0), s: numStyle },
      { v: Math.round(m.cumulCashflow), s: { ...numStyle, font: { color: { rgb: m.cumulCashflow < 0 ? "C00000" : "1B873F" } } } },
      { v: m.cumulProgressPct / 100, s: pctStyle },
    ]),
  ];
  const wsSC = XLSX.utils.aoa_to_sheet(scGrid.map((line) => line.map((c) => c.v)));
  scGrid.forEach((line, ri) => {
    line.forEach((cell, ci) => {
      const addr = XLSX.utils.encode_cell({ r: ri, c: ci });
      if (wsSC[addr] && cell.s) wsSC[addr].s = cell.s;
    });
  });
  wsSC["!merges"] = [{ s: { r: 0, c: 0 }, e: { r: 0, c: scHeaders.length - 1 } }];
  wsSC["!cols"] = [9, 13, 16, 22, 22, 18, 20, 15].map((wch) => ({ wch }));

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Cash Flow");
  XLSX.utils.book_append_sheet(wb, wsSC, "S-Curve Data");
  const safe = (projectName || "Project").replace(/[^\w؀-ۿ -]/g, "").replace(/ /g, "_") || "Project";
  XLSX.writeFile(wb, `CashFlow_${safe}.xlsx`);
}
