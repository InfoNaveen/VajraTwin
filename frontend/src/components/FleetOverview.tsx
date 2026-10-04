// ---------------------------------------------------------------------------
// FleetOverview — command-center fleet view. Aggregates engine-level state for
// all demonstrator UAVs and lets the operator drill into one aircraft's twin.
// ---------------------------------------------------------------------------
import {
  Plane,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Activity,
  ChevronRight,
  RotateCcw,
  Loader2,
  Wrench,
} from "lucide-react";
import type { FleetSummary, FleetAircraftState, FleetStatus } from "../types";

interface Props {
  summary: FleetSummary | null;
  loading: boolean;
  error: string | null;
  demoMode: boolean;
  onSelect: (uavId: string) => void;
  onResetAll: () => void;
}

const STATUS_CFG: Record<
  FleetStatus,
  { text: string; border: string; bg: string; icon: React.ReactNode }
> = {
  HEALTHY: {
    text: "text-adv-go",
    border: "border-adv-go/40",
    bg: "bg-adv-go/5",
    icon: <ShieldCheck className="w-4 h-4" />,
  },
  ATTENTION: {
    text: "text-adv-monitor",
    border: "border-adv-monitor/40",
    bg: "bg-adv-monitor/5",
    icon: <ShieldAlert className="w-4 h-4" />,
  },
  CRITICAL: {
    text: "text-adv-maint",
    border: "border-adv-maint/50",
    bg: "bg-adv-maint/5",
    icon: <ShieldX className="w-4 h-4" />,
  },
};

function rulLabel(h: number | null): string {
  if (h === null || h === undefined) return "—";
  return h >= 1 ? `${h.toFixed(1)} h` : `${(h * 60).toFixed(0)} min`;
}

function healthColor(h: number): string {
  if (h > 70) return "text-adv-go";
  if (h > 50) return "text-adv-monitor";
  if (h > 30) return "text-adv-derate";
  return "text-adv-maint";
}

function StatBlock({
  label,
  value,
  tone = "text-gcs-text",
}: {
  label: string;
  value: string;
  tone?: string;
}) {
  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-1">
      <span className="text-[10px] font-mono text-gcs-sub uppercase tracking-widest">{label}</span>
      <span className={`font-mono text-2xl font-bold ${tone}`}>{value}</span>
    </div>
  );
}

export default function FleetOverview({
  summary,
  loading,
  error,
  demoMode,
  onSelect,
  onResetAll,
}: Props) {
  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center h-96 text-gcs-sub font-mono text-sm gap-2">
        <Loader2 className="w-5 h-5 animate-spin" /> Initialising demonstrator fleet…
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="px-4 py-3 bg-adv-maint/10 border border-adv-maint/30 rounded-xl text-adv-maint text-sm font-mono">
          Fleet unavailable: {error}
        </div>
      </div>
    );
  }

  if (!summary) return null;

  const counts = summary.status_counts;
  const fleetTone = healthColor(summary.fleet_health);

  return (
    <div className="space-y-5">
      {/* Header strip */}
      <section className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-lg font-bold text-gcs-text tracking-wide flex items-center gap-2">
            <Plane className="w-5 h-5 text-gcs-accent" />
            Fleet Operations
          </h1>
          <p className="text-xs font-mono text-gcs-sub mt-0.5">
            {summary.fleet_name} · {summary.total_aircraft} aircraft · each backed by its own
            engine digital twin
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-1 rounded border border-adv-monitor/40 bg-adv-monitor/10 text-adv-monitor">
            SYNTHETIC · DEMONSTRATOR
          </span>
          <button
            onClick={onResetAll}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gcs-border bg-gcs-bg text-gcs-sub font-mono text-xs font-semibold hover:border-gcs-accent/40 hover:text-gcs-accent transition"
          >
            <RotateCcw className="w-3.5 h-3.5" /> RESET FLEET
          </button>
        </div>
      </section>

      {/* KPI row */}
      <section className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatBlock label="Aircraft" value={String(summary.total_aircraft)} />
        <StatBlock label="Healthy" value={String(counts.healthy)} tone="text-adv-go" />
        <StatBlock label="Attention" value={String(counts.attention)} tone="text-adv-monitor" />
        <StatBlock label="Critical" value={String(counts.critical)} tone="text-adv-maint" />
        <StatBlock label="Fleet Health" value={`${summary.fleet_health.toFixed(0)}%`} tone={fleetTone} />
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Aircraft list */}
        <section className="xl:col-span-2">
          <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub mb-3">
            Aircraft — select to inspect digital twin
          </p>
          <div className="flex flex-col gap-2">
            {summary.aircraft.map((ac: FleetAircraftState) => {
              const cfg = STATUS_CFG[ac.status];
              return (
                <button
                  key={ac.uav_id}
                  onClick={() => onSelect(ac.uav_id)}
                  className={`group flex items-center gap-4 px-4 py-3 rounded-xl border ${cfg.border} ${cfg.bg} hover:border-gcs-accent/50 transition text-left`}
                >
                  <span className={`${cfg.text} shrink-0`}>{cfg.icon}</span>
                  <div className="flex flex-col min-w-[120px]">
                    <span className="font-mono text-sm font-bold text-gcs-text">{ac.uav_id}</span>
                    <span className="font-mono text-[10px] text-gcs-sub">{ac.callsign}</span>
                  </div>
                  <div className="flex flex-col items-center w-16">
                    <span className={`font-mono text-lg font-bold ${healthColor(ac.health_index)}`}>
                      {ac.health_index.toFixed(0)}
                    </span>
                    <span className="font-mono text-[9px] text-gcs-sub uppercase">health</span>
                  </div>
                  <span
                    className={`font-mono text-xs font-bold ${cfg.text} w-20 text-center`}
                  >
                    {ac.status}
                  </span>
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="font-mono text-xs text-gcs-text truncate">{ac.fault_label}</span>
                    <span className="font-mono text-[10px] text-gcs-sub">
                      RUL {rulLabel(ac.rul_hours)} · {ac.advisory_state}
                    </span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gcs-sub group-hover:text-gcs-accent shrink-0" />
                </button>
              );
            })}
          </div>
          {demoMode && (
            <p className="text-[10px] font-mono text-gcs-muted mt-2">
              DEMO MODE — fleet state held in-memory (MongoDB not connected). Fully operational.
            </p>
          )}
        </section>

        {/* Side column: highest risk + maintenance priority + fault dist */}
        <section className="flex flex-col gap-4">
          {/* Highest risk */}
          <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-4 h-4 text-adv-maint" />
              <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
                Highest Risk
              </span>
            </div>
            {summary.highest_risk ? (
              <button
                onClick={() => onSelect(summary.highest_risk!.uav_id)}
                className="w-full text-left"
              >
                <p className="font-mono text-lg font-bold text-adv-maint">
                  {summary.highest_risk.uav_id}
                </p>
                <p className="font-mono text-xs text-gcs-sub mt-0.5">
                  {summary.highest_risk.reason}
                </p>
              </button>
            ) : (
              <p className="font-mono text-sm text-adv-go">All aircraft nominal</p>
            )}
          </div>

          {/* Maintenance priority */}
          <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Wrench className="w-4 h-4 text-gcs-accent" />
              <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
                Maintenance Priority
              </span>
            </div>
            {summary.maintenance_priority.length > 0 ? (
              <ol className="flex flex-col gap-2">
                {summary.maintenance_priority.map((p) => (
                  <li key={p.uav_id}>
                    <button
                      onClick={() => onSelect(p.uav_id)}
                      className="w-full flex items-start gap-2 text-left group"
                    >
                      <span className="font-mono text-xs font-bold text-gcs-sub w-4 shrink-0">
                        {p.rank}.
                      </span>
                      <div className="flex flex-col min-w-0">
                        <span
                          className={`font-mono text-xs font-bold group-hover:text-gcs-accent ${
                            STATUS_CFG[p.status].text
                          }`}
                        >
                          {p.uav_id}
                        </span>
                        <span className="font-mono text-[10px] text-gcs-sub truncate">
                          {p.reason}
                        </span>
                      </div>
                    </button>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="font-mono text-sm text-adv-go">No maintenance actions required</p>
            )}
          </div>

          {/* Fault distribution */}
          <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4">
            <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
              Fault Distribution
            </span>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {Object.entries(summary.fault_distribution).map(([k, v]) => (
                <span
                  key={k}
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                    k === "NORMAL"
                      ? "border-adv-go/40 text-adv-go bg-adv-go/10"
                      : "border-adv-derate/40 text-adv-derate bg-adv-derate/10"
                  }`}
                >
                  {k} × {v}
                </span>
              ))}
            </div>
            <p className="text-[9px] font-mono text-gcs-muted mt-2">
              {summary.fleet_health_method}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
