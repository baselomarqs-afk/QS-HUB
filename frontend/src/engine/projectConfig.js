// إعدادات المشروع — Shared project configuration for the Programme & Cash-Flow
// windows. Ported from villa-qto to plain JS.

/** Standard UAE villa programme length (~70% of cases): 13 months total,
 *  including one month of mobilization. Used to suggest a default handover date. */
export const STANDARD_DURATION_MONTHS = 13;

/** Format a Date to YYYY-MM-DD using local components (no UTC shift). */
function fmtISO(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Add N calendar months to a YYYY-MM-DD date. */
export function addMonths(iso, months) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const base = new Date(y, (m || 1) - 1, d || 1);
  base.setMonth(base.getMonth() + months);
  return fmtISO(base);
}

/** Suggested handover date = start + standard villa duration (editable default). */
export function suggestedHandover(startISO) {
  return addMonths(startISO, STANDARD_DURATION_MONTHS);
}

const TODAY_ISO = fmtISO(new Date());

// Defaults: project-specific quantities start EMPTY (the user must enter them).
// Only standard UAE contract conventions are pre-filled as editable starting points.
export const DEFAULT_CONFIG = {
  projectName: "",
  clientName: "",
  plotNumber: "",
  location: "Dubai",
  consultantName: "",
  contractorName: "",
  preparedBy: "",
  revisionNumber: "00",

  villaType: "",
  buaPerFloor: 0,
  basementArea: 0,
  mezzanineArea: 0,
  hasPool: false,
  poolArea: 0,
  hasBoundaryWall: false,
  boundaryWallLength: 0,
  hasRoofGarden: false,
  hasExternalLandscape: false,
  hasDemolition: false,

  startISO: TODAY_ISO,
  handoverISO: suggestedHandover(TODAY_ISO),
  complexityFactor: 1.0,

  contractValueAed: 0,

  advancePaymentPct: 10,
  retentionPct: 5,
  retentionReleaseAtCompletionPct: 50,
  vatPct: 5,
  certificationPeriodDays: 14,
  paymentPeriodDays: 30,
  defectsLiabilityMonths: 12,
  contractorCostRatio: 0.85,
};

/** Numeric coercion mirroring Python's float(x or 0). */
export function num(v) {
  if (v === null || v === undefined || v === "") return 0;
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isFinite(n) ? n : 0;
}

/** Parse num upper floors + basement/mezzanine flags from a villa type string. */
export function parseVillaType(villaType) {
  let vt = (villaType || "").toUpperCase().trim();
  let hasBasement = false;
  if (vt.startsWith("B+")) {
    hasBasement = true;
    vt = vt.slice(2);
  }
  const hasMezzanine = vt.includes("+M") || vt === "G+M";
  const parts = vt.replace("+M", "").split("+");
  const upper = parts.slice(1).filter((p) => /^\d+$/.test(p));
  const numUpperFloors = upper.length ? parseInt(upper[0], 10) : 0;
  return { numUpperFloors, hasBasement, hasMezzanine };
}

/** Compute the derived villa geometry (floors + total BUA). */
export function deriveVilla(cfg) {
  const { numUpperFloors, hasBasement, hasMezzanine } = parseVillaType(cfg.villaType);
  let bua = cfg.buaPerFloor * (1 + numUpperFloors);
  if (hasBasement) bua += cfg.basementArea > 0 ? cfg.basementArea : cfg.buaPerFloor;
  if (hasMezzanine) bua += cfg.mezzanineArea > 0 ? cfg.mezzanineArea : cfg.buaPerFloor * 0.4;
  let totalFloors = 1 + numUpperFloors;
  if (hasMezzanine) totalFloors += 0.5;
  return {
    numUpperFloors,
    hasBasement,
    hasMezzanine,
    totalBua: Math.round(bua * 10) / 10,
    totalFloors,
  };
}
