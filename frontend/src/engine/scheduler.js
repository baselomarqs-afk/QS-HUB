// محرك الجدولة — CPM scheduler with a robust predecessor fallback, an
// "all-works-complete" gate before closeout, and a fit-to-handover hard
// constraint. Ported from villa-qto.

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

export class Scheduler {
  constructor(cfg, activities) {
    this.cfg = cfg;
    this.activities = activities;
    this.scheduled = new Map();
    this.gateStart = null;
    const [y, m, day] = cfg.startISO.split("-").map(Number);
    this.start = new Date(y, (m || 1) - 1, day || 1);
    this.idMap = new Map(activities.map((a) => [a.id, a]));
    this.order = new Map(MASTER_ORDER.map((id, i) => [id, i]));
  }

  resolvePredecessorId(act) {
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

  resolveStart(act) {
    const base = this.basePredecessorStart(act);
    if (this.gateStart && isCloseout(act) && base < this.gateStart) return this.gateStart;
    return base;
  }

  basePredecessorStart(act) {
    const predId = this.resolvePredecessorId(act);
    if (predId === null) return addDays(this.start, act.startOffsetDays);
    if (!this.scheduled.has(predId)) {
      const pred = this.idMap.get(predId);
      if (pred) this.scheduleOne(pred);
    }
    const predSa = this.scheduled.get(predId);
    return predSa ? addDays(predSa.finishDate, act.lagDays) : this.start;
  }

  scheduleOne(act) {
    const existing = this.scheduled.get(act.id);
    if (existing) return existing;
    const startDt = this.resolveStart(act);
    const finishDt = addDays(startDt, act.durationDays - 1);
    const startDay = Math.round((startDt.getTime() - this.start.getTime()) / 86400000) + 1;
    const finishDay = Math.round((finishDt.getTime() - this.start.getTime()) / 86400000) + 1;
    const sa = {
      activity: act,
      startDate: startDt,
      finishDate: finishDt,
      startDay,
      finishDay,
      startWeek: Math.ceil(startDay / 7),
      finishWeek: Math.ceil(finishDay / 7),
      isCritical: false,
      valueAed: 0,
    };
    this.scheduled.set(act.id, sa);
    return sa;
  }

  scheduleAll() {
    for (const act of this.activities) if (!isCloseout(act)) this.scheduleOne(act);
    const worksFinish = this.scheduled.size
      ? Math.max(...Array.from(this.scheduled.values()).map((s) => s.finishDay))
      : 0;
    this.gateStart = addDays(this.start, worksFinish);
    for (const act of this.activities) if (isCloseout(act)) this.scheduleOne(act);

    const list = Array.from(this.scheduled.values());
    list.sort((a, b) => a.startDay - b.startDay || (this.order.get(a.activity.id) - this.order.get(b.activity.id)));
    this.markCriticalPath(list);
    this.assignValues(list);
    return list;
  }

  markCriticalPath(list) {
    if (!list.length) return;
    const end = Math.max(...list.map((s) => s.finishDay));
    for (const s of list) if (end - s.finishDay <= 3) s.isCritical = true;
  }

  assignValues(list) {
    const cv = this.cfg.contractValueAed;
    const counts = {};
    for (const s of list) counts[s.activity.phaseId] = (counts[s.activity.phaseId] ?? 0) + 1;
    for (const s of list) {
      const w = PHASE_VALUE_WEIGHTS[s.activity.phaseId] ?? 0.01;
      const n = Math.max(counts[s.activity.phaseId] ?? 1, 1);
      s.valueAed = (cv * w) / n;
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
  if (!cfg.handoverISO) return null;
  const [sy, sm, sd] = cfg.startISO.split("-").map(Number);
  const [hy, hm, hd] = cfg.handoverISO.split("-").map(Number);
  const start = new Date(sy, (sm || 1) - 1, sd || 1);
  const handover = new Date(hy, (hm || 1) - 1, hd || 1);
  const days = Math.round((handover.getTime() - start.getTime()) / 86400000) + 1;
  return days > 1 ? days : null;
}

/** Hard constraint: scale durations/lags/offsets so the critical path ends
 *  exactly on the handover date. Unchanged if no handover date is set. */
function fitToHandover(cfg, activities) {
  const target = targetSpanDays(cfg);
  if (!target || !activities.length) return activities;

  const raw = new Scheduler(cfg, activities).scheduleAll();
  const naturalFinish = Math.max(...raw.map((s) => s.finishDay));
  const scale = target / naturalFinish;
  if (!isFinite(scale) || scale <= 0) return activities;

  let scaled = activities.map((a) => {
    const days = Math.max(1, Math.round(a.durationDays * scale));
    return {
      ...a,
      durationDays: days,
      durationWeeks: Math.round((days / 7) * 10) / 10,
      lagDays: Math.round(a.lagDays * scale),
      startOffsetDays: Math.round(a.startOffsetDays * scale),
    };
  });

  const after = new Scheduler(cfg, scaled).scheduleAll();
  const residual = target - Math.max(...after.map((s) => s.finishDay));
  if (residual !== 0) {
    const last = after.reduce((m, s) => (s.finishDay > m.finishDay ? s : m), after[0]);
    scaled = scaled.map((a) => {
      if (a.id !== last.activity.id) return a;
      const days = Math.max(1, a.durationDays + residual);
      return { ...a, durationDays: days, durationWeeks: Math.round((days / 7) * 10) / 10 };
    });
  }
  return scaled;
}

/** Convenience: build + schedule from an activity list. */
export function runScheduler(cfg, activities) {
  const acts = fitToHandover(cfg, activities);
  const sch = new Scheduler(cfg, acts);
  const scheduled = sch.scheduleAll();
  const startDate = scheduled.length ? scheduled.reduce((m, s) => (s.startDate < m ? s.startDate : m), scheduled[0].startDate) : new Date();
  const finishDate = scheduled.length ? scheduled.reduce((m, s) => (s.finishDate > m ? s.finishDate : m), scheduled[0].finishDate) : new Date();
  const totalDays = Math.round((finishDate.getTime() - startDate.getTime()) / 86400000) + 1;
  return {
    scheduled,
    startDate,
    finishDate,
    totalDays,
    totalWeeks: Math.ceil(totalDays / 7),
    monthly: sch.monthlyPlannedValues(scheduled),
  };
}

export function fmtDate(d) {
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
