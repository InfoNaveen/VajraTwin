import { BrainCircuit, ShieldAlert, Activity } from "lucide-react";
import type { AnomalyBlock, FaultBlock, ExplanationBlock } from "../types";

interface Props {
  anomaly: AnomalyBlock | null;
  fault: FaultBlock | null;
  explanation: ExplanationBlock | null;
  isLoading: boolean;
}

const FAULT_COLORS: Record<string, string> = {
  NORMAL: "text-adv-go border-adv-go/40 bg-adv-go/10",
  EGT_ANOMALY: "text-adv-derate border-adv-derate/40 bg-adv-derate/10",
  CHT_OVERHEAT: "text-adv-maint border-adv-maint/50 bg-adv-maint/10",
  OIL_PRESSURE_LOW: "text-adv-maint border-adv-maint/50 bg-adv-maint/10",
  VIBRATION_ANOMALY: "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10",
  BOOST_TURBO_ANOMALY: "text-adv-derate border-adv-derate/40 bg-adv-derate/10",
  SENSOR_ANOMALY: "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10",
  MULTI_PARAMETER_FAULT: "text-adv-maint border-adv-maint/60 bg-adv-maint/10",
};

function AnomalyMeter({ score, status }: { score: number; status: string }) {
  const cls =
    status === "ANOMALY"
      ? "bg-adv-maint/10 border-adv-maint/50 text-adv-maint"
      : status === "WATCH"
        ? "bg-adv-monitor/10 border-adv-monitor/40 text-adv-monitor"
        : "bg-adv-go/10 border-adv-go/40 text-adv-go";
  const pct = Math.max(0, Math.min(100, score));
  return (
    <div className={`rounded-lg border p-3 ${cls}`}>
      <div className="flex items-center justify-between text-xs font-mono font-semibold">
        <span className="flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5" />
          ANOMALY {status}
        </span>
        <span>{score.toFixed(0)}/100</span>
      </div>
      <div className="w-full bg-gcs-border/60 rounded-full h-1.5 mt-2 overflow-hidden">
        <div
          className="h-1.5 rounded-full bg-current transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function DiagnosticsPanel({ anomaly, fault, explanation, isLoading }: Props) {
  const faultClass = fault?.fault_class ?? "NORMAL";
  const faultColor = FAULT_COLORS[faultClass] ?? FAULT_COLORS.NORMAL;
  const top = anomaly?.contributing_features?.slice(0, 3) ?? [];

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <BrainCircuit className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Diagnostics
        </span>
        {isLoading && (
          <span className="ml-auto text-[10px] font-mono text-gcs-muted animate-pulse">
            analysing…
          </span>
        )}
      </div>

      {anomaly ? (
        <AnomalyMeter score={anomaly.anomaly_score} status={anomaly.anomaly_status} />
      ) : (
        <div className="rounded-lg border border-gcs-border p-3 text-xs font-mono text-gcs-sub">
          No anomaly data yet.
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-gcs-sub">Fault Class</span>
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold ${faultColor}`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          {fault?.fault_label ?? "Normal"}
        </div>
      </div>

      {/* Contributing features */}
      <div>
        <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1.5">
          Contributing Parameters
        </p>
        <div className="flex flex-col gap-1">
          {top.length > 0 ? (
            top.map((c) => (
              <div key={c.channel} className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-gcs-sub w-28 shrink-0">{c.label}</span>
                <div className="flex-1 bg-gcs-border/50 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-1.5 rounded-full bg-gcs-accent transition-all duration-500"
                    style={{ width: `${Math.min(100, c.contribution)}%` }}
                  />
                </div>
                <span className="text-[10px] font-mono text-gcs-text w-10 text-right">
                  {c.contribution.toFixed(0)}%
                </span>
              </div>
            ))
          ) : (
            <span className="text-[10px] font-mono text-gcs-muted">—</span>
          )}
        </div>
      </div>

      {/* XAI explanation */}
      <div className="bg-gcs-bg rounded-lg border border-gcs-border p-3 min-h-[64px]">
        <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1">
          Root-Cause Explanation
          {explanation?.explanation_source && (
            <span className="ml-2 text-gcs-muted normal-case">
              ({explanation.explanation_source})
            </span>
          )}
        </p>
        <p className="text-xs leading-relaxed text-gcs-text font-sans animate-fade-in">
          {explanation?.explanation ?? "Awaiting diagnostics…"}
        </p>
      </div>
    </div>
  );
}
