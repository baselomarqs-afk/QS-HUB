// أنواع الفلل — Villa type definitions, base durations and phase value weights.
// Ported from villa-qto (TypeScript) to plain JS for the QS HUB React frontend.

export const VILLA_TYPE_DEFINITIONS = {
  "G+0": { label: "Ground Floor Only", labelAr: "أرضي فقط", ground: 1, upper: 0, basement: false, mezzanine: false },
  "G+1": { label: "Ground + 1st Floor", labelAr: "أرضي + أول", ground: 1, upper: 1, basement: false, mezzanine: false },
  "G+2": { label: "Ground + 2 Floors", labelAr: "أرضي + طابقين", ground: 1, upper: 2, basement: false, mezzanine: false },
  "G+3": { label: "Ground + 3 Floors", labelAr: "أرضي + ٣ طوابق", ground: 1, upper: 3, basement: false, mezzanine: false },
  "G+4": { label: "Ground + 4 Floors", labelAr: "أرضي + ٤ طوابق", ground: 1, upper: 4, basement: false, mezzanine: false },
  "G+M": { label: "Ground + Mezzanine", labelAr: "أرضي + ميزانين", ground: 1, upper: 0, basement: false, mezzanine: true },
  "G+M+1": { label: "Ground + Mezzanine + 1st Floor", labelAr: "أرضي + ميزانين + أول", ground: 1, upper: 1, basement: false, mezzanine: true },
  "G+M+2": { label: "Ground + Mezzanine + 2 Floors", labelAr: "أرضي + ميزانين + طابقين", ground: 1, upper: 2, basement: false, mezzanine: true },
  "B+G": { label: "Basement + Ground Floor", labelAr: "قبو + أرضي", ground: 1, upper: 0, basement: true, mezzanine: false },
  "B+G+1": { label: "Basement + Ground + 1st Floor", labelAr: "قبو + أرضي + أول", ground: 1, upper: 1, basement: true, mezzanine: false },
  "B+G+2": { label: "Basement + Ground + 2 Floors", labelAr: "قبو + أرضي + طابقين", ground: 1, upper: 2, basement: true, mezzanine: false },
  "B+G+3": { label: "Basement + Ground + 3 Floors", labelAr: "قبو + أرضي + ٣ طوابق", ground: 1, upper: 3, basement: true, mezzanine: false },
};

export const BASE_DURATIONS_WEEKS = {
  "G+0": 28, "G+1": 36, "G+2": 44, "G+3": 52,
  "G+4": 60, "G+M": 38, "G+M+1": 48, "G+M+2": 56,
  "B+G": 44, "B+G+1": 52, "B+G+2": 60, "B+G+3": 68,
};

// Share of contract value earned in each phase (sums to ~1.0).
export const PHASE_VALUE_WEIGHTS = {
  P01: 0.02, P02: 0.01, P03: 0.15, P04: 0.20, P05: 0.08, P06: 0.10,
  P07: 0.03, P08: 0.06, P09: 0.07, P10: 0.02, P11: 0.09, P12: 0.06,
  P13: 0.05, P14: 0.03, P15: 0.04, P16: 0.00,
};
