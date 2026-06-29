// محرك المدد — Duration engine. Filters the master activity DB to the activities
// applicable to a villa, then calibrates each duration by floor area, floor count
// and complexity. Ported from villa-qto.

import { deriveVilla } from "./projectConfig";
import { PHASES } from "./activitiesDb";
import { BASE_DURATIONS_WEEKS } from "./villaTypes";

const REFERENCE_BUA = 300.0;
const AREA_EXPONENT = 0.6;
const AREA_EXPONENT_FINISHES = 0.7;

/** Return the activities applicable to this villa configuration. */
export function getApplicableActivities(cfg) {
  const vt = cfg.villaType;
  const out = [];
  for (const phase of PHASES) {
    for (const act of phase.activities) {
      const at = act.applicableTo;
      const meta = { phaseId: phase.id, phaseName: phase.name, phaseNameAr: phase.nameAr, phaseColor: phase.color };
      if (at.length === 0) out.push({ ...act, ...meta });
      else if (at.includes("POOL") && cfg.hasPool) out.push({ ...act, ...meta });
      else if (at.includes("DEMOLITION_ONLY") && cfg.hasDemolition) out.push({ ...act, ...meta });
      else if (at.includes(vt)) out.push({ ...act, ...meta });
    }
  }
  return out;
}

/** Scale a single activity's duration (weeks) by area, floors and complexity. */
export function scaleDuration(act, cfg) {
  const derived = deriveVilla(cfg);
  let dur = act.durationBaseWeeks;

  if (act.areaSensitive) {
    const bua = Math.max(cfg.buaPerFloor, 50);
    const exp = act.category === "finishes" || act.category === "mep" ? AREA_EXPONENT_FINISHES : AREA_EXPONENT;
    dur *= Math.pow(bua / REFERENCE_BUA, exp);
  }

  if (act.floorMult) {
    let totalFloors = 1 + derived.numUpperFloors;
    if (derived.hasMezzanine) totalFloors += 0.5;
    dur *= 0.5 + 0.5 * totalFloors;
  }

  dur *= cfg.complexityFactor;
  dur = Math.round(dur * 2) / 2;
  return Math.max(0.5, Math.min(dur, 16.0));
}

/** Build the calibrated activity list for a project configuration. */
export function buildActivityList(cfg) {
  return getApplicableActivities(cfg).map((act) => {
    const durWeeks = scaleDuration(act, cfg);
    return {
      id: act.id,
      name: act.name,
      nameAr: act.nameAr,
      phaseId: act.phaseId,
      phaseName: act.phaseName,
      phaseNameAr: act.phaseNameAr,
      phaseColor: act.phaseColor,
      category: act.category,
      durationWeeks: durWeeks,
      durationDays: Math.round(durWeeks * 7),
      predecessorId: act.predecessor,
      lagDays: act.lagDays,
      startOffsetDays: act.startOffsetDays,
    };
  });
}

/** Recommended total project duration in weeks (used as a sanity figure). */
export function autoCalculateTotalWeeks(cfg) {
  const derived = deriveVilla(cfg);
  const base = BASE_DURATIONS_WEEKS[cfg.villaType] ?? 40;
  let extra = 0;
  if (cfg.hasPool) extra += 4;
  if (cfg.hasRoofGarden) extra += 3;
  if (cfg.hasDemolition) extra += 3;
  if (derived.totalBua > 800) extra += Math.floor((derived.totalBua - 800) / 100);
  return Math.max(24, Math.round((base + extra) * cfg.complexityFactor));
}
