// تصدير برنامج الأعمال — Phase-coloured week-by-week CPM Gantt export (Excel).
// Includes Predecessors, Total Float (days), genuine Critical Path markers (●)
// with crimson critical-path Gantt bars, and bilingual Arabic/English activity names.
import * as XLSX from "xlsx-js-style";
import { fmtDate } from "./scheduler";

const NAVY = "1A3C5E";
const WHITE = "FFFFFF";
const CRIT_RED = "C00000";

const headerStyle = {
  fill: { fgColor: { rgb: NAVY } },
  font: { color: { rgb: WHITE }, bold: true },
  alignment: { horizontal: "center", vertical: "center", wrapText: true },
};
const titleStyle = { font: { bold: true, sz: 15, color: { rgb: NAVY } }, alignment: { horizontal: "center" } };
const centerStyle = { alignment: { horizontal: "center" } };

export function exportProgrammeToExcel(out, projectName, drawings = []) {
  const weeks = out.totalWeeks;
  const weekCols = Array.from({ length: weeks }, (_, i) => `W${i + 1}`);
  const headers = [
    "#", "ID", "Activity", "النشاط", "Phase", "Pred.", "Wks", "Start", "Finish", "Float (d)", "CP", ...weekCols,
  ];
  const lastCol = headers.length - 1;
  const critCount = out.criticalCount ?? out.scheduled.filter((s) => s.isCritical).length;

  const grid = [];
  const merges = [];

  grid.push([{ v: `Construction Work Programme (CPM) — ${projectName}`, s: titleStyle }]);
  grid.push([{
    v: `Start: ${fmtDate(out.startDate)}   •   Finish: ${fmtDate(out.finishDate)}   •   Duration: ${out.totalDays} days (${weeks} weeks)   •   Activities: ${out.scheduled.length}   •   Critical Path: ${critCount} tasks (Red bars = Critical)`,
    s: { font: { italic: true, color: { rgb: "555555" } }, alignment: { horizontal: "center" } },
  }]);
  merges.push({ s: { r: 0, c: 0 }, e: { r: 0, c: lastCol } });
  merges.push({ s: { r: 1, c: 0 }, e: { r: 1, c: lastCol } });

  if (Array.isArray(drawings) && drawings.length > 0) {
    const refList = drawings.map((d) => `${d.name} (${d.pages || 1}p)`).join("  |  ");
    grid.push([{
      v: `Reference Drawings: ${refList}`,
      s: { font: { italic: true, color: { rgb: "1A3C5E" } }, alignment: { horizontal: "center" } },
    }]);
    merges.push({ s: { r: 2, c: 0 }, e: { r: 2, c: lastCol } });
  }
  grid.push([{ v: "" }]);

  grid.push(headers.map((h) => ({ v: h, s: headerStyle })));

  let prevPhase = "";
  let r = grid.length;
  let no = 1;
  for (const s of out.scheduled) {
    const a = s.activity;
    if (a.phaseId !== prevPhase) {
      grid.push([{
        v: `▌ ${a.phaseName} | ${a.phaseNameAr}`,
        s: { fill: { fgColor: { rgb: a.phaseColor } }, font: { color: { rgb: WHITE }, bold: true } },
      }]);
      merges.push({ s: { r, c: 0 }, e: { r, c: lastCol } });
      r += 1;
      prevPhase = a.phaseId;
    }
    const startWeek = s.startWeek - 1;
    const endWeek = s.finishWeek - 1;
    const barColor = s.isCritical ? CRIT_RED : a.phaseColor;
    const barStyle = { fill: { fgColor: { rgb: barColor } } };
    const bars = weekCols.map((_, wi) => (wi >= startWeek && wi <= endWeek ? { v: "", s: barStyle } : { v: "" }));
    const predText = (s.predecessorIds && s.predecessorIds.length) ? s.predecessorIds.join(", ") : "—";
    const floatVal = s.totalFloatDays ?? 0;

    grid.push([
      { v: no, s: centerStyle },
      { v: a.id, s: { ...centerStyle, font: s.isCritical ? { bold: true, color: { rgb: CRIT_RED } } : {} } },
      { v: a.name, s: s.isCritical ? { font: { bold: true } } : {} },
      { v: a.nameAr, s: { alignment: { horizontal: "right" }, font: s.isCritical ? { bold: true } : {} } },
      { v: a.phaseName },
      { v: predText, s: centerStyle },
      { v: a.durationWeeks, s: centerStyle },
      { v: fmtDate(s.startDate), s: centerStyle },
      { v: fmtDate(s.finishDate), s: centerStyle },
      { v: floatVal, s: { ...centerStyle, font: { color: { rgb: floatVal === 0 ? CRIT_RED : "2E75B6" }, bold: floatVal === 0 } } },
      { v: s.isCritical ? "●" : "", s: { alignment: { horizontal: "center" }, font: { color: { rgb: CRIT_RED }, bold: true } } },
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
  ws["!cols"] = [4, 7, 42, 34, 22, 13, 6, 12, 12, 8, 4, ...weekCols.map(() => 2.6)].map((wch) => ({ wch }));

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Work Program");
  const safe = (projectName || "Project").replace(/[^\w؀-ۿ -]/g, "").replace(/ /g, "_") || "Project";
  XLSX.writeFile(wb, `WorkProgram_${safe}.xlsx`);
}
