import { Reading } from "@/lib/icu-data";
import { cn } from "@/lib/utils";

type Props = {
  patients: { id: number; latest: Reading | null }[];
  selectedId: number;
  onSelect: (id: number) => void;
};

export function PatientList({ patients, selectedId, onSelect }: Props) {
  const sorted = [...patients].sort((a, b) => {
    const aw = a.latest?.warning ?? 0;
    const bw = b.latest?.warning ?? 0;
    if (aw !== bw) return bw - aw;
    return a.id - b.id;
  });

  return (
    <aside className="w-72 shrink-0 border-r border-border bg-card flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-sm font-semibold text-foreground">ICU Patients</h2>
        <p className="text-xs text-muted-foreground">{patients.length} monitored</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {sorted.map((p) => {
          const warn = p.latest?.warning === 1;
          const selected = p.id === selectedId;
          return (
            <button
              key={p.id}
              onClick={() => onSelect(p.id)}
              className={cn(
                "w-full flex items-center justify-between gap-2 px-4 py-3 text-left border-b border-border/60 transition-colors",
                selected ? "bg-accent" : "hover:bg-accent/50"
              )}
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium text-foreground">
                  Patient #{p.id.toString().padStart(3, "0")}
                </span>
                {p.latest && (
                  <span className="text-xs text-muted-foreground">
                    HR {p.latest.heart_rate} · SpO₂ {p.latest.spo2}%
                  </span>
                )}
              </div>
              {warn ? (
  <span className="inline-flex items-center gap-1 rounded-full bg-destructive px-2 py-0.5 text-xs font-medium text-destructive-foreground animate-pulse">
    ⚠ {p.latest?.risk_score
        ? `Risk ${Math.round(p.latest.risk_score * 100)}%`
        : 'Warning'}
  </span>
) : (
  <span className="inline-flex items-center rounded-full bg-emerald-500/15 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400">
    {p.latest?.risk_score
        ? `${Math.round((1 - p.latest.risk_score) * 100)}% safe`
        : 'Normal'}
  </span>
)}
            </button>
          );
        })}
      </div>
    </aside>
  );
}