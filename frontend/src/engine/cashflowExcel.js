// تصدير التدفق النقدي — Full monthly certificate schedule export (Excel).
// Ported from villa-qto. Lazy-import so xlsx stays out of the main bundle.
import * as XLSX from "xlsx-js-style";

const NAVY = "1A3C5E";
const SECTION = "2D6A9F";
const WHITE = "FFFFFF";

const headerStyle = { fill: { fgColor: { rgb: NAVY } }, font: { color: { rgb: WHITE }, bold: true }, alignment: { horizontal: "center", vertical: "center", wrapText: true } };
const titleStyle = { font: { bold: true, sz: 15, color: { rgb: NAVY } }, alignment: { horizontal: "center" } };
const labelStyle = { font: { bold: true, color: { rgb: NAVY } } };
const totalStyle = { fill: { fgColor: { rgb: SECTION } }, font: { color: { rgb: WHITE }, bold: true } };
const numStyle = { alignment: { horizontal: "right" }, numFmt: "#,##0" };

export function exportCashFlowToExcel(cfg, result, projectName) {
  const headers = ["#", "Month", "Planned", "Cum %", "Advance Rec.", "Retention", "Net Cert.", "VAT", "Received", "Expenditure", "Net Cashflow", "Cumulative"];
  const lastCol = headers.length - 1;
  const { summary } = result;

  const grid = [];
  const merges = [];

  grid.push([{ v: `Cash-Flow Forecast — ${projectName}`, s: titleStyle }]);
  merges.push({ s: { r: 0, c: 0 }, e: { r: 0, c: lastCol } });

  const info = [
    ["Contract Value (AED)", summary.contractValue],
    ["Advance Payment (AED)", summary.advancePayment],
    ["Total Retention (AED)", summary.totalRetentionWithheld],
    ["Working Capital Required (AED)", summary.workingCapitalRequired],
    ["Peak Negative @ Month", summary.peakNegativeMonth],
    ["2nd Trough @ Month", summary.secondTroughMonth || "—"],
    ["Payback @ Month", summary.paybackMonth],
    ["Total Expenditure (AED)", summary.totalExpenditure],
    ["Gross Profit (AED)", summary.totalProfit],
    ["Profit Margin %", summary.profitMarginPct],
    ["VAT %", cfg.vatPct],
  ];
  info.forEach(([k, v]) => grid.push([{ v: k, s: labelStyle }, { v, s: typeof v === "number" ? numStyle : {} }]));
  grid.push([{ v: "" }]);

  grid.push(headers.map((h) => ({ v: h, s: headerStyle })));

  for (const m of result.rows) {
    grid.push([
      { v: m.monthNumber, s: { alignment: { horizontal: "center" } } },
      { v: m.monthLabel + (m.isRetentionRelease ? " (retention)" : ""), s: { alignment: { horizontal: "center" } } },
      { v: Math.round(m.plannedValue), s: numStyle },
      { v: m.cumulProgressPct / 100, s: { alignment: { horizontal: "right" }, numFmt: "0.0%" } },
      { v: Math.round(m.advanceRecovery), s: numStyle },
      { v: Math.round(m.retentionDeducted), s: numStyle },
      { v: Math.round(m.netCertificate), s: numStyle },
      { v: Math.round(m.vatOnCert), s: numStyle },
      { v: Math.round(m.paymentReceived), s: numStyle },
      { v: Math.round(m.expenditure), s: numStyle },
      { v: Math.round(m.netCashflow), s: numStyle },
      { v: Math.round(m.cumulCashflow), s: { ...numStyle, font: { color: { rgb: m.cumulCashflow < 0 ? "C00000" : "1B873F" } } } },
    ]);
  }

  const sum = (sel) => Math.round(result.rows.reduce((a, m) => a + sel(m), 0));
  grid.push([
    { v: "TOTAL", s: totalStyle }, { v: "", s: totalStyle },
    { v: sum((m) => m.plannedValue), s: { ...numStyle, ...totalStyle } },
    { v: "", s: totalStyle },
    { v: sum((m) => m.advanceRecovery), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.retentionDeducted), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.netCertificate), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.vatOnCert), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.paymentReceived), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.expenditure), s: { ...numStyle, ...totalStyle } },
    { v: sum((m) => m.netCashflow), s: { ...numStyle, ...totalStyle } },
    { v: "", s: totalStyle },
  ]);

  const ws = XLSX.utils.aoa_to_sheet(grid.map((line) => line.map((c) => c.v)));
  grid.forEach((line, ri) => {
    line.forEach((cell, ci) => {
      const addr = XLSX.utils.encode_cell({ r: ri, c: ci });
      if (ws[addr] && cell.s) ws[addr].s = cell.s;
    });
  });
  ws["!merges"] = merges;
  ws["!cols"] = [4, 14, 13, 8, 13, 12, 13, 11, 13, 13, 14, 14].map((wch) => ({ wch }));

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Cash Flow");
  const safe = (projectName || "Project").replace(/[^\w؀-ۿ -]/g, "").replace(/ /g, "_") || "Project";
  XLSX.writeFile(wb, `CashFlow_${safe}.xlsx`);
}
