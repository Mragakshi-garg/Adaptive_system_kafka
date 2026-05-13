import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Reading, THRESHOLDS, getTriggers } from "@/lib/icu-data";
import { VitalCard } from "./VitalCard";
import { cn } from "@/lib/utils";

type Props = {
  patientId: number;
  readings: Reading[];
  acknowledged: boolean;
  onAcknowledge: () => void;
};

export function PatientDetail({ patientId, readings, acknowledged, onAcknowledge }: Props) {
  const latest = readings[readings.length - 1];
  const last20 = useMemo(() => readings.slice(-20), [readings]);

  const chartData = last20.map((r) => ({
    time: new Date(r.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }),
    HR: r.heart_rate,
    SpO2: r.spo2,
    Sys: r.systolic_bp,
    Dia: r.diastolic_bp,
    MAP: r.mean_bp,
  }));

  if (!latest) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Waiting for data…
      </div>
    );
  }

  const inWarning = latest.warning === 1;
  const triggers = getTriggers(latest);

  return (
    <main className="flex-1 overflow-y-auto bg-background">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Patient #{patientId.toString().padStart(3, "0")}
            </h1>
            <p className="text-sm text-muted-foreground">
              Last update: {new Date(latest.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </header>

        {inWarning && (
          <div
            className={cn(
              "rounded-lg border p-4 flex items-center justify-between gap-4 transition-colors",
              acknowledged
                ? "bg-muted border-border text-muted-foreground"
                : "bg-destructive border-destructive text-destructive-foreground animate-pulse"
            )}
          >
            <div>
              <div className="font-semibold">
                {acknowledged ? "Alarm acknowledged" : "⚠ ALERT — Patient needs attention"}
              </div>
              {triggers.length > 0 && (
                <div className="text-sm mt-1 opacity-90">
                  Triggered by: {triggers.join(", ")}
                </div>
              )}
            </div>
            {!acknowledged && (
              <button
                onClick={onAcknowledge}
                className="shrink-0 rounded-md bg-background text-foreground px-4 py-2 text-sm font-medium hover:bg-background/90"
              >
                Acknowledge / Dismiss
              </button>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <VitalCard
            label="HR"
            value={latest.heart_rate}
            unit="bpm"
            warning={THRESHOLDS.heart_rate(latest.heart_rate)}
          />
          <VitalCard
            label="SpO₂"
            value={latest.spo2}
            unit="%"
            warning={THRESHOLDS.spo2(latest.spo2)}
          />
          <VitalCard
            label="Sys BP"
            value={latest.systolic_bp}
            unit="mmHg"
            warning={THRESHOLDS.systolic_bp(latest.systolic_bp)}
          />
          <VitalCard
            label="Dia BP"
            value={latest.diastolic_bp}
            unit="mmHg"
            warning={THRESHOLDS.diastolic_bp(latest.diastolic_bp)}
          />
          <VitalCard
            label="MAP"
            value={latest.mean_bp}
            unit="mmHg"
            warning={THRESHOLDS.mean_bp(latest.mean_bp)}
          />
        </div>

        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground mb-3">
            Vitals — last {last20.length} readings
          </h2>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="currentColor" opacity={0.6} />
                <YAxis tick={{ fontSize: 11 }} stroke="currentColor" opacity={0.6} />
                <Tooltip
                  contentStyle={{
                    background: "var(--popover)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="HR" stroke="#ef4444" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="SpO2" stroke="#3b82f6" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="Sys" stroke="#10b981" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="Dia" stroke="#f59e0b" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="MAP" stroke="#8b5cf6" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </main>
  );
}