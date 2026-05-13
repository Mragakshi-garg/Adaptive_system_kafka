import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: number | string;
  unit: string;
  warning: boolean;
};

export function VitalCard({ label, value, unit, warning }: Props) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        warning
          ? "bg-destructive/10 border-destructive/40 text-destructive"
          : "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400"
      )}
    >
      <div className="text-xs font-medium uppercase tracking-wide opacity-80">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className="text-4xl font-bold tabular-nums">{value}</span>
        <span className="text-sm opacity-70">{unit}</span>
      </div>
    </div>
  );
}