import { Timer, Info } from "lucide-react";
import type { RulBlock } from "../types";

interface Props {
  rul: RulBlock | null;
  isLoading: boolean;
}

function fmtHours(h: number | null): string {
  if (h === null || h === undefined) return "—";
  if (h >= 1) return `${h.toFixed(1)} h`;
  return `${(h * 60).toFixed(0)} min`;
}

export default function RulPanel({ rul, isLoading }: Props) {
  const status = rul?.status ?? "INSUFFICIENT_HISTORY";
  const hours = rul?.rul_hours ?? null;
  const ci = rul?.confidence_interval ?? null;

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Timer className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Trend-based RUL Estimate
        </span>
        {isLoading && (
          <span className="ml-auto text-[10px] font-mono text-gcs-muted animate-pulse">
            estimating…
          </span>
        )}
      </div>

      {status === "OK" ? (
        <>
          <div className="flex items-end gap-2">
            <span className="font-mono tabular-nums text-4xl font-bold leading-none text-gcs-text">
              {fmtHours(hours)}
            </span>
            <span className="text-gcs-sub font-mono text-xs mb-1">est. remaining</span>
          </div>
          {ci && (
            <div className="flex items-center gap-3 text-xs font-mono">
              <span className="text-adv-derate">P5 {fmtHours(ci[0])}</span>
              <span className="text-gcs-muted">—</span>
              <span className="text-adv-go">P95 {fmtHours(ci[1])}</span>
            </div>
          )}
        </>
      ) : (
        <div className="flex flex-col gap-1 py-2">
          <span className="font-mono text-sm text-gcs-sub">
            {status === "STABLE_NO_DECAY" ? "No measurable degradation trend" : "Insufficient degradation history"}
          </span>
          <span className="font-mono text-[10px] text-gcs-muted">
            {rul?.message ?? "RUL becomes available once a degradation trend is observed."}
          </span>
        </div>
      )}

      {/* Honest methodology note */}
      <div className="flex items-start gap-1.5 bg-gcs-bg border border-gcs-border rounded-lg p-2.5">
        <Info className="w-3.5 h-3.5 text-gcs-sub shrink-0 mt-0.5" />
        <p className="text-[10px] font-mono text-gcs-sub leading-relaxed">
          Trend-based estimator on synthetic degradation data. Demonstrator estimate — not a
          certified flight-safety or real-world engine-life prediction.
        </p>
      </div>
    </div>
  );
}
