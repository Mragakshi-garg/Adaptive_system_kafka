export type Reading = {
  subject_id: number;
  timestamp: string;
  heart_rate: number;
  spo2: number;
  systolic_bp: number;
  diastolic_bp: number;
  mean_bp: number;
  warning: 0 | 1;
  risk_score?: number; 
};

export const THRESHOLDS = {
  heart_rate: (v: number) => v < 40 || v > 100,
  spo2: (v: number) => v < 90,
  systolic_bp: (v: number) => v < 90,
  diastolic_bp: (v: number) => v < 60,
  mean_bp: (v: number) => v < 70,
};

export const VITAL_LABELS: Record<keyof typeof THRESHOLDS, string> = {
  heart_rate: "Heart Rate",
  spo2: "SpO₂",
  systolic_bp: "Systolic BP",
  diastolic_bp: "Diastolic BP",
  mean_bp: "MAP",
};

export const VITAL_UNITS: Record<keyof typeof THRESHOLDS, string> = {
  heart_rate: "bpm",
  spo2: "%",
  systolic_bp: "mmHg",
  diastolic_bp: "mmHg",
  mean_bp: "mmHg",
};

// Deterministic pseudo-random generator
function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function generateMockData(): Reading[][] {
  const patients: Reading[][] = [];
  const startTime = Date.now() - 1000 * 60 * 60;
  for (let id = 1; id <= 50; id++) {
    const rand = mulberry32(id * 1000);
    const willDeteriorate = rand() < 0.4;
    const readings: Reading[] = [];
    let hr = 70 + rand() * 20;
    let spo2 = 96 + rand() * 3;
    let sys = 115 + rand() * 15;
    let dia = 70 + rand() * 10;
    for (let i = 0; i < 60; i++) {
      const drift = willDeteriorate && i > 20 ? (i - 20) * 0.3 : 0;
      hr += (rand() - 0.5) * 4 + (willDeteriorate ? drift * 0.4 : 0);
      spo2 += (rand() - 0.5) * 1 - (willDeteriorate ? drift * 0.15 : 0);
      sys += (rand() - 0.5) * 5 - (willDeteriorate ? drift * 0.5 : 0);
      dia += (rand() - 0.5) * 3 - (willDeteriorate ? drift * 0.3 : 0);
      hr = Math.max(30, Math.min(140, hr));
      spo2 = Math.max(75, Math.min(100, spo2));
      sys = Math.max(70, Math.min(180, sys));
      dia = Math.max(40, Math.min(110, dia));
      const map = (sys + 2 * dia) / 3;
      const warn =
        THRESHOLDS.heart_rate(hr) ||
        THRESHOLDS.spo2(spo2) ||
        THRESHOLDS.systolic_bp(sys) ||
        THRESHOLDS.diastolic_bp(dia) ||
        THRESHOLDS.mean_bp(map);
      readings.push({
        subject_id: id,
        timestamp: new Date(startTime + i * 60_000).toISOString(),   // now a string
        heart_rate: Math.round(hr),
        spo2: Math.round(spo2 * 10) / 10,
        systolic_bp: Math.round(sys),
        diastolic_bp: Math.round(dia),
        mean_bp: Math.round(map),
        warning: warn ? 1 : 0,
      });
    }
    patients.push(readings);
  }
  return patients;
}

export function getTriggers(r: Reading): string[] {
  const out: string[] = [];
  if (THRESHOLDS.heart_rate(r.heart_rate)) out.push(`Heart Rate = ${r.heart_rate} bpm`);
  if (THRESHOLDS.spo2(r.spo2)) out.push(`SpO₂ = ${r.spo2}%`);
  if (THRESHOLDS.systolic_bp(r.systolic_bp)) out.push(`Systolic BP = ${r.systolic_bp} mmHg`);
  if (THRESHOLDS.diastolic_bp(r.diastolic_bp)) out.push(`Diastolic BP = ${r.diastolic_bp} mmHg`);
  if (THRESHOLDS.mean_bp(r.mean_bp)) out.push(`MAP = ${r.mean_bp} mmHg`);
  return out;
}