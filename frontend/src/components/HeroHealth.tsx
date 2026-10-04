import AdvisoryBadge from "./AdvisoryBadge";
import type { AdvisoryBlock, DegradationBlock, FaultBlock, RulBlock } from "../types";

interface Props {
  degradation: DegradationBlock | null;
  advisory: AdvisoryBlock | null;
  fault: FaultBlock | null;
  rul: RulBlock | null;
}

function healthRing(h: number): string {
  if (h > 70) return "#22c55e";
  if (h > 50) return "#eab308";
  if (h > 30) return "#f97316";
  return "#ef4444";
}

export default function HeroHealth({ degradation, advisory, fault, rul }: Props) {
  const health = degradation?.health_index ?? null;
  const ringColor = health !== null ? healthRing(health) : "#374151";
  const circumference = 2 * Math.PI * 52;
  const dash = health !== null ? (health / 100) * circumference : 0;

  const rulLabel =
    rul?.status === "OK" && rul.rul_hours != null
      ? rul.rul_hours >= 1
        ? `${rul.rul_hours.toFixed(1)} h`
        : `${(rul.rul_hours * 60).toFixed(0)} min`
      : rul?.status === "STABLE_NO_DECAY"
        ? "stable"
        : "—";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-5 flex flex-col lg:flex-row items-center gap-6">
      {/* Health ring */}
      <div className="relative shrink-0">
        <svg width="128" height="128" className="-rotate-90">
          <circle cx="64" cy="64" r="52" fill="none" stroke="#1f2937" strokeWidth="10" />
          <circle
            cx="64"
            cy="64"
            r="52"
            fill="none"
            stroke={ringColor}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            style={{ transition: "stroke-dasharray 0.7s ease, stroke 0.7s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-3xl font-bold" style={{ color: ringColor }}>
            {health !== null ? health.toFixed(0) : "--"}
          </span>
          <span className="font-mono text-[10px] text-gcs-sub uppercase tracking-wider">Health</span>
        </div>
      </div>

      {/* State summary */}
      <div className="flex-1 flex flex-col gap-3 w-full">
        <div className="flex flex-wrap items-center gap-3">
          <AdvisoryBadge advisory={advisory?.state ?? "PENDING"} pulse />
          <div className="flex flex-col">
            <span className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider">
              Engine State
            </span>
            <span className="font-mono text-sm font-bold text-gcs-text">
              {fault?.fault_label ?? "—"}
            </span>
          </div>
        </div>

        <p className="text-xs font-mono text-gcs-sub leading-relaxed">
          {advisory?.root_cause ?? "Awaiting telemetry…"}
        </p>

        <div className="grid grid-cols-3 gap-3 pt-1">
          <div>
            <p className="text-[10px] font-mono text-gcs-sub uppercase">Trend</p>
            <p className="font-mono text-sm font-bold text-gcs-text">
              {degradation?.health_trend ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-gcs-sub uppercase">Est. RUL</p>
            <p className="font-mono text-sm font-bold text-gcs-text">{rulLabel}</p>
          </div>
          <div>
            <p className="text-[10px] font-mono text-gcs-sub uppercase">Advisory</p>
            <p className="font-mono text-sm font-bold text-gcs-text">
              {advisory?.severity ?? "—"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
