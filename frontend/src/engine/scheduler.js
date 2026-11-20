// محرك الجدولة — Genuine CPM Scheduler (Forward Pass + Backward Pass + Total Float)
// with multi-predecessor support, an "all-works-complete" gate before closeout,
// protected fixed-duration milestones, normalized 100% phase value weights,
// and persisted manual duration overrides.

import { MASTER_ORDER } from "./activitiesDb";
import { PHASE_VALUE_WEIGHTS } from "./villaTypes";

function addDays(d, n) {
  const r = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  r.setDate(r.getDate() + n);
  return r;
}

/** Closeout activities (final municipal inspection → snagging → handover) must
 *  wait for ALL construction works to finish, not just their listed predecessor. */
function isCloseout(act) {
  return act.phaseId === "P16" && act.category === "admin";
}

function parseStartDate(startISO) {
  if (!startISO || typeof startISO !== "string" || !startISO.includes("-")) {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }
  const [y, m, day] = startISO.split("-").map(Number);
  return new Date(y || new Date().getFullYear(), (m || 1) - 1, day || 1);
}

export class Scheduler {
  constructor(cfg, activities) {
    this.cfg = cfg;
    this.activities = activities;
    this.scheduled = new Map();
    this.resolvedPredMap = new Map(); // id -> Array<{ predId, lagDays }>
    this.gateStartDay = null;
    this.start = parseStartDate(cfg.startISO);
    this.idMap = new Map(activities.map((a) => [a.id, a]));
    this.order = new Map(MASTER_ORDER.map((id, i) => [id, i]));
  }

  resolvePrimaryPredecessorId(act) {
    if (!act.predecessorId) return null;
    if (this.idMap.has(act.predecessorId)) return act.predecessorId;
    const myIdx = this.order.get(act.id) ?? 0;
    let best = null;
    let bestIdx = -1;
    for (const a of this.activities) {
      const idx = this.order.get(a.id) ?? -1;
      if (idx < myIdx && idx > bestIdx) {
        best = a.id;
        bestIdx = idx;
      }
    }
    return best;
  }

  resolvePredecessors(act) {
    if (this.resolvedPredMap.has(act.id)) return this.resolvedPredMap.get(act.id);
    const preds = [];
    const seen = new Set();
    const lag = act.lagDays || 0;

    const primary = this.resolvePrimaryPredecessorId(act);
    if (primary && primary !== act.id) {
      seen.add(primary);
      preds.push({ predId: primary, lagDays: lag });
    }
    for (const extraId of act.extraPredecessors || []) {
      if (extraId && extraId !== act.id && this.idMap.has(extraId) && !seen.has(extraId)) {
        seen.add(extraId);
        preds.push({ predId: extraId, lagDays: lag });
      }
    }
    this.resolvedPredMap.set(act.id, preds);
    return preds;
  }

  scheduleOne(act) {
    const existing = this.scheduled.get(act.id);
    if (existing) return existing;

    const preds = this.resolvePredecessors(act);
    let esDay = 1 + (act.startOffsetDays || 0);

    for (const { predId, lagDays } of preds) {
      if (!this.scheduled.has(predId)) {
        const predAct = this.idMap.get(predId);
        if (predAct) this.scheduleOne(predAct);
      }
      const predSa = this.scheduled.get(predId);
      if (predSa) {
        // Standard Finish-to-Start (FS + lag): successor starts next calendar day + lag
        const candidate = predSa.finishDay + 1 + lagDays;
        if (candidate > esDay) esDay = candidate;
      }
    }

    if (this.gateStartDay !== null && isCloseout(act) && esDay < this.gateStartDay) {
      esDay = this.gateStartDay;
    }

    const dur = Math.max(1, act.durationDays || 1);
    const efDay = esDay + dur - 1;
    const startDt = addDays(this.start, esDay - 1);
    const finishDt = addDays(this.start, efDay - 1);

    const sa = {
      activity: act,
      startDate: startDt,
      finishDate: finishDt,
      startDay: esDay,
      finishDay: efDay,
      lateStartDay: esDay,
      lateFinishDay: efDay,
      totalFloatDays: 0,
      startWeek: Math.ceil(esDay / 7),
      finishWeek: Math.ceil(efDay / 7),
      predecessorIds: preds.map((p) => p.predId),
      isCritical: false,
      valueAed: 0,
    };
    this.scheduled.set(act.id, sa);
    return sa;
  }

  scheduleAll() {
    // 1. Forward Pass — construction & commissioning works
    const nonCloseout = this.activities.filter((a) => !isCloseout(a));
    const closeout = this.activities.filter((a) => isCloseout(a));

    for (const act of nonCloseout) this.scheduleOne(act);

    const worksFinish = this.scheduled.size
      ? Math.max(...Array.from(this.scheduled.values()).map((s) => s.finishDay))
      : 0;
    this.gateStartDay = worksFinish + 1;

    // 2. Forward Pass — closeout gate & handover
    for (const act of closeout) this.scheduleOne(act);

    // 3. Backward Pass — genuine CPM Late Start, Late Finish & Total Float
    this.computeBackwardPass(nonCloseout, closeout);

    const list = Array.from(this.scheduled.values());
    list.sort((a, b) => a.startDay - b.startDay || ((this.order.get(a.activity.id) ?? 0) - (this.order.get(b.activity.id) ?? 0)));
    this.assignValues(list);
    return list;
  }

  computeBackwardPass(nonCloseout, closeout) {
    const allScheduled = Array.from(this.scheduled.values());
    if (!allScheduled.length) return;

    const projectFinish = Math.max(...allScheduled.map((s) => s.finishDay));

    // Build successor adjacency list (including the all-works-complete gate into entry closeout tasks)
    const succs = new Map(allScheduled.map((s) => [s.activity.id, []]));

    for (const s of allScheduled) {
      const preds = this.resolvePredecessors(s.activity);
      for (const { predId, lagDays } of preds) {
        if (succs.has(predId)) {
          succs.get(predId).push({ succId: s.activity.id, lagDays });
        }
      }
    }

    // Entry closeout tasks (e.g., A174) wait for ALL non-closeout works (lag 0)
    const closeoutSet = new Set(closeout.map((a) => a.id));
    const entryCloseout = closeout.filter((act) => {
      const preds = this.resolvePredecessors(act);
      return preds.every((p) => !closeoutSet.has(p.predId));
    });
    for (const u of nonCloseout) {
      const uSuccs = succs.get(u.id);
      for (const c of entryCloseout) {
        if (!uSuccs.some((edge) => edge.succId === c.id)) {
          uSuccs.push({ succId: c.id, lagDays: 0 });
        }
      }
    }

    // Topological order via Kahn's algorithm, then reverse for backward pass
    const inDeg = new Map(allScheduled.map((s) => [s.activity.id, 0]));
    for (const edges of succs.values()) {
      for (const { succId } of edges) {
        inDeg.set(succId, (inDeg.get(succId) ?? 0) + 1);
      }
    }
    const queue = [];
    for (const [id, d] of inDeg.entries()) if (d === 0) queue.push(id);

    const topo = [];
    while (queue.length) {
      const u = queue.shift();
      topo.push(u);
      for (const { succId } of succs.get(u) || []) {
        const nd = (inDeg.get(succId) ?? 1) - 1;
        inDeg.set(succId, nd);
        if (nd === 0) queue.push(succId);
      }
    }
    // Fallback if any node wasn't reached
    for (const s of allScheduled) {
      if (!topo.includes(s.activity.id)) topo.push(s.activity.id);
    }

    // Backward sweep
    for (let i = topo.length - 1; i >= 0; i--) {
      const id = topo[i];
      const sa = this.scheduled.get(id);
      const outEdges = succs.get(id) || [];
      let lf = projectFinish;
      if (outEdges.length > 0) {
        lf = Infinity;
        for (const { succId, lagDays } of outEdges) {
          const succSa = this.scheduled.get(succId);
          if (!succSa) continue;
          const candidateLf = succSa.lateStartDay - 1 - lagDays;
          if (candidateLf < lf) lf = candidateLf;
        }
        if (!Number.isFinite(lf)) lf = projectFinish;
      }
      const dur = Math.max(1, sa.activity.durationDays || 1);
      const ls = lf - dur + 1;
      const totalFloat = Math.max(0, ls - sa.startDay);
      sa.lateFinishDay = lf;
      sa.lateStartDay = ls;
      sa.totalFloatDays = totalFloat;
      sa.isCritical = totalFloat === 0;
    }
  }

  assignValues(list) {
    const cv = this.cfg.contractValueAed || 0;
    const counts = {};
    for (const s of list) counts[s.activity.phaseId] = (counts[s.activity.phaseId] ?? 0) + 1;

    // Re-normalize active phase weights so sum of planned values ALWAYS equals 100.00% of contract value
    const activePhases = Object.keys(counts);
    let totalWeight = 0;
    for (const pid of activePhases) {
      totalWeight += PHASE_VALUE_WEIGHTS[pid] ?? 0.01;
    }
    if (totalWeight <= 0) totalWeight = 1;

    for (const s of list) {
      const rawW = PHASE_VALUE_WEIGHTS[s.activity.phaseId] ?? 0.01;
      const normW = rawW / totalWeight;
      const n = Math.max(counts[s.activity.phaseId] ?? 1, 1);
      s.valueAed = (cv * normW) / n;
    }
  }

  monthlyPlannedValues(list) {
    const monthly = {};
    for (const s of list) {
      const days = Math.max(s.activity.durationDays, 1);
      const daily = s.valueAed / days;
      let cur = s.startDate;
      for (let i = 0; i < days; i++) {
        const ym = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, "0")}`;
        monthly[ym] = (monthly[ym] ?? 0) + daily;
        cur = addDays(cur, 1);
      }
    }
    return monthly;
  }
}

/** Calendar days from start to handover (inclusive), or null if not set/invalid. */
function targetSpanDays(cfg) {
  if (!cfg.handoverISO || !cfg.startISO) return null;
  const start = parseStartDate(cfg.startISO);
  const handover = parseStartDate(cfg.handoverISO);
  const days = Math.round((handover.getTime() - start.getTime()) / 86400000) + 1;
  return days > 1 ? days : null;
}

/** Scale flexible durations/lags so the schedule lands cleanly on the handover date
 *  while preserving technical fixed-duration tasks (7-day curing, 48h flood test, handover). */
function fitToHandover(cfg, activities) {
  const target = targetSpanDays(cfg);
  if (!target || !activities.length) return activities;

  const raw = new Scheduler(cfg, activities).scheduleAll();
  const naturalFinish = Math.max(...raw.map((s) => s.finishDay));
  if (!Number.isFinite(naturalFinish) || naturalFinish <= 0) return activities;

  // Estimate fixed days sitting on the critical path so flexible tasks absorb the scaling
  const fixedCritDays = raw
    .filter((s) => s.isCritical && s.activity.fixedDuration)
    .reduce((acc, s) => acc + s.activity.durationDays, 0);

  const canKeepFixed = target > fixedCritDays + 14 && naturalFinish > fixedCritDays + 7;

  const applyScale = (scaleVal, keepFixed) =>
    activities.map((a) => {
      if (keepFixed && a.fixedDuration) {
        return { ...a };
      }
      const days = Math.max(1, Math.round(a.durationDays * scaleVal));
      return {
        ...a,
        durationDays: days,
        durationWeeks: Math.round((days / 7) * 10) / 10,
        lagDays: Math.round((a.lagDays || 0) * scaleVal),
        startOffsetDays: Math.round((a.startOffsetDays || 0) * scaleVal),
      };
    });

  let scale = canKeepFixed
    ? (target - fixedCritDays) / (naturalFinish - fixedCritDays)
    : target / naturalFinish;
  if (!Number.isFinite(scale) || scale <= 0) return activities;

  let scaled = applyScale(scale, canKeepFixed);

  // Refine up to 3 iterations so rounding & fixed tasks converge smoothly to target
  for (let iter = 0; iter < 3; iter++) {
    const after = new Scheduler(cfg, scaled).scheduleAll();
    const curFinish = Math.max(...after.map((s) => s.finishDay));
    const diff = target - curFinish;
    if (Math.abs(diff) <= 1) break;
    const denom = canKeepFixed ? Math.max(curFinish - fixedCritDays, 7) : curFinish;
    const adjust = (denom + diff) / denom;
    if (!Number.isFinite(adjust) || adjust <= 0.1) break;
    scale *= adjust;
    scaled = applyScale(scale, canKeepFixed);
  }

  // Absorb any remaining small rounding residual into the longest flexible critical activity
  const after = new Scheduler(cfg, scaled).scheduleAll();
  const residual = target - Math.max(...after.map((s) => s.finishDay));
  if (residual !== 0) {
    const flexCrit = after
      .filter((s) => s.isCritical && !s.activity.fixedDuration)
      .sort((a, b) => b.activity.durationDays - a.activity.durationDays);
    const targetAct = flexCrit[0] || after.reduce((m, s) => (s.finishDay > m.finishDay ? s : m), after[0]);
    if (targetAct && targetAct.activity.durationDays + residual >= 1) {
      scaled = scaled.map((a) => {
        if (a.id !== targetAct.activity.id) return a;
        const days = Math.max(1, a.durationDays + residual);
        return { ...a, durationDays: days, durationWeeks: Math.round((days / 7) * 10) / 10 };
      });
    }
  }
  return scaled;
}

/** Apply persisted manual activity duration overrides (after fitting to handover)
 *  so manual edits take effect directly without being overwritten by fitToHandover. */
function applyCustomDurations(activities, customDurations) {
  if (!customDurations || typeof customDurations !== "object") return activities;
  const keys = Object.keys(customDurations);
  if (!keys.length) return activities;
  return activities.map((a) => {
    const ov = customDurations[a.id];
    if (typeof ov === "number" && Number.isFinite(ov) && ov > 0) {
      const days = Math.max(1, Math.round(ov * 7));
      return { ...a, durationWeeks: Math.round(ov * 10) / 10, durationDays: days };
    }
    return a;
  });
}

/** Convenience: fit baseline + apply manual overrides + run full CPM scheduler. */
export function runScheduler(cfg, activities, opts = {}) {
  const fitted = opts.skipFit ? activities : fitToHandover(cfg, activities);
  const acts = applyCustomDurations(fitted, cfg.customDurations);
  const sch = new Scheduler(cfg, acts);
  const scheduled = sch.scheduleAll();
  const startDate = scheduled.length ? scheduled.reduce((m, s) => (s.startDate < m ? s.startDate : m), scheduled[0].startDate) : new Date();
  const finishDate = scheduled.length ? scheduled.reduce((m, s) => (s.finishDate > m ? s.finishDate : m), scheduled[0].finishDate) : new Date();
  const totalDays = Math.round((finishDate.getTime() - startDate.getTime()) / 86400000) + 1;
  const criticalCount = scheduled.filter((s) => s.isCritical).length;
  return {
    scheduled,
    startDate,
    finishDate,
    totalDays,
    totalWeeks: Math.ceil(totalDays / 7),
    criticalCount,
    monthly: sch.monthlyPlannedValues(scheduled),
  };
}

export function fmtDate(d) {
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
