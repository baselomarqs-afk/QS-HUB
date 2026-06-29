// تصدير برنامج الأعمال — Phase-coloured week-by-week Gantt export (Excel).
// Ported from villa-qto. Lazy-import this module so xlsx stays out of the main bundle.
import * as XLSX from "xlsx-js-style";
import { fmtDate } from "./scheduler";

const NAVY = "1A3C5E";
const WHITE = "FFFFFF";

const headerStyle = { fill: { fgColor: { rgb: NAVY } }, font: { color: { rgb: WHITE }, bold: true }, alignment: { horizontal: "center", vertical: "center", wrapText: true } };
const titleStyle = { font: { bold: true, sz: 15, color: { rgb: NAVY } }, alignment: { horizontal: "center" } };
const centerStyle = { alignment: { horizontal: "center" } };

export function exportProgrammeToExcel(out, projectName) {
  const weeks = out.totalWeeks;
  const weekCols = Array.from({ length: weeks }, (_, i) => `W${i + 1}`);
  const headers = ["#", "ID", "Activity", "النشاط", "Phase", "Wks", "Start", "Finish", "CP", ...weekCols];
  const lastCol = headers.length - 1;

  const grid = [];
  const merges = [];

  grid.push([{ v: `Construction Programme — ${projectName}`, s: titleStyle }]);
  grid.push([{ v: `Start: ${fmtDate(out.startDate)}   •   Finish: ${fmtDate(out.finishDate)}   •   Duration: ${out.totalDays} days (${weeks} weeks)`, s: { font: { italic: true, color: { rgb: "666666" } }, alignment: { horizontal: "center" } } }]);
  grid.push([{ v: "" }]);
  merges.push({ s: { r: 0, c: 0 }, e: { r: 0, c: lastCol } });
  merges.push({ s: { r: 1, c: 0 }, e: { r: 1, c: lastCol } });

  grid.push(headers.map((h) => ({ v: h, s: headerStyle })));

  let prevPhase = "";
  let r = grid.length;
  let no = 1;
  for (const s of out.scheduled) {
    const a = s.activity;
    if (a.phaseId !== prevPhase) {
      grid.push([{ v: `▌ ${a.phaseName} | ${a.phaseNameAr}`, s: { fill: { fgColor: { rgb: a.phaseColor } }, font: { color: { rgb: WHITE }, bold: true } } }]);
      merges.push({ s: { r, c: 0 }, e: { r, c: lastCol } });
      r += 1;
      prevPhase = a.phaseId;
    }
    const startWeek = s.startWeek - 1;
    const endWeek = s.finishWeek - 1;
    const barStyle = { fill: { fgColor: { rgb: a.phaseColor } } };
    const bars = weekCols.map((_, wi) => (wi >= startWeek && wi <= endWeek ? { v: "", s: barStyle } : { v: "" }));
    grid.push([
      { v: no, s: centerStyle },
      { v: a.id, s: centerStyle },
      { v: a.name },
      { v: a.nameAr, s: { alignment: { horizontal: "right" } } },
      { v: a.phaseName },
      { v: a.durationWeeks, s: centerStyle },
      { v: fmtDate(s.startDate), s: centerStyle },
      { v: fmtDate(s.finishDate), s: centerStyle },
      { v: s.isCritical ? "●" : "", s: { alignment: { horizontal: "center" }, font: { color: { rgb: "C00000" }, bold: true } } },
      ...bars,
    ]);
    r += 1;
    no += 1;
  }

  const ws = XLSX.utils.aoa_to_sheet(grid.map((line) => line.map((c) => c.v)));
  grid.forEach((line, ri) => {
    line.forEach((cell, ci) => {
      const addr = XLSX.utils.encode_cell({ r: ri, c: ci });
      if (ws[addr] && cell.s) ws[addr].s = cell.s;
    });
  });
  ws["!merges"] = merges;
  ws["!cols"] = [4, 6, 40, 30, 22, 5, 12, 12, 4, ...weekCols.map(() => 2.6)].map((wch) => ({ wch }));

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Work Program");
  const safe = (projectName || "Project").replace(/[^\w؀-ۿ -]/g, "").replace(/ /g, "_") || "Project";
  XLSX.writeFile(wb, `WorkProgram_${safe}.xlsx`);
}
