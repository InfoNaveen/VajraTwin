// ---------------------------------------------------------------------------
// SystemStatusPanel — the Digital Twin / System Status panel.
// Shows the live state of the whole closed loop: backend connection, DB mode,
// simulation state, engine sync, scenario, last telemetry update, data source.
// ---------------------------------------------------------------------------

import {
  Server,
  Database,
  Radio,
  GitCompareArrows,
  Gauge,
  FlaskConical,
} from "lucide-react";
import type {
  Analysis,
  ConnectionStatus,
  HealthResponse,
  SimulationStatus,
} from "../types";

interface Props {
  connection: ConnectionStatus;
  health: HealthResponse | null;
  sim: SimulationStatus | null;
  analysis: Analysis | null;
}

function Row({
  icon,
  label,
  value,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const toneCls = {
    default: "text-gcs-text",
    good: "text-adv-go",
    warn: "text-adv-monitor",
    bad: "text-adv-maint",
  }[tone];
  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-gcs-border/40 last:border-0">
      <div className="w-7 h-7 rounded-lg bg-gcs-bg border border-gcs-border flex items-center justify-center shrink-0 text-gcs-sub">
        {icon}
      </div>
      <span className="text-xs font-mono text-gcs-sub flex-1">{label}</span>
      <span className={`text-xs font-mono font-semibold ${toneCls} text-right truncate max-w-[55%]`}>
        {value}
      </span>
    </div>
  );
}

export default function SystemStatusPanel({ connection, health, sim, analysis }: Props) {
  const demoMode = health?.database.demo_mode ?? false;

  // "twin synchronisation" = how closely actual tracks the physics expected.
  // We derive a simple sync indicator from the EGT+CHT residual magnitude.
  let syncLabel = "—";
  let syncTone: "default" | "good" | "warn" | "bad" = "default";
  if (analysis) {
    const dE = Math.abs(analysis.residuals.delta_egt_c);
    const dC = Math.abs(analysis.residuals.delta_cht_c);
    const score = dE / 60 + dC / 20;
    if (score < 1) {
      syncLabel = "SYNCHRONISED";
      syncTone = "good";
    } else if (score < 2) {
      syncLabel = "DIVERGING";
      syncTone = "warn";
    } else {
      syncLabel = "DESYNCHRONISED";
      syncTone = "bad";
    }
  }

  const simState = sim
    ? sim.paused
      ? "PAUSED"
      : sim.running
        ? "RUNNING"
        : "STOPPED"
    : "—";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2 mb-1">
        <GitCompareArrows className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Digital Twin · System Status
        </span>
      </div>

      <Row
        icon={<Server className="w-3.5 h-3.5" />}
        label="Backend"
        value={connection === "online" ? "ONLINE" : connection === "offline" ? "OFFLINE" : "CONNECTING"}
        tone={connection === "online" ? "good" : connection === "offline" ? "bad" : "default"}
      />
      <Row
        icon={<Database className="w-3.5 h-3.5" />}
        label="Persistence"
        value={demoMode ? "DEMO MODE (in-memory)" : "MONGODB"}
        tone={demoMode ? "warn" : "good"}
      />
      <Row
        icon={<Radio className="w-3.5 h-3.5" />}
        label="Simulation"
        value={simState}
        tone={simState === "RUNNING" ? "good" : simState === "PAUSED" ? "warn" : "default"}
      />
      <Row
        icon={<GitCompareArrows className="w-3.5 h-3.5" />}
        label="Twin Sync"
        value={syncLabel}
        tone={syncTone}
      />
      <Row
        icon={<Gauge className="w-3.5 h-3.5" />}
        label="Scenario"
        value={sim?.scenario ?? "—"}
        tone={sim && sim.scenario !== "HEALTHY" ? "warn" : "good"}
      />
      <Row
        icon={<Radio className="w-3.5 h-3.5" />}
        label="Mission Phase"
        value={analysis?.telemetry.mission_phase ?? sim?.mission_phase ?? "—"}
      />
      <Row
        icon={<Gauge className="w-3.5 h-3.5" />}
        label="Last Update"
        value={analysis ? `t+${analysis.sim_time_s.toFixed(0)}s · tick ${analysis.tick}` : "—"}
      />
      <Row
        icon={<FlaskConical className="w-3.5 h-3.5" />}
        label="Data Source"
        value={analysis?.data_label ?? "SYNTHETIC"}
        tone="warn"
      />
      <Row
        icon={<Server className="w-3.5 h-3.5" />}
        label="Physics Engine"
        value="Rotax 914 surrogate"
      />
      <Row
        icon={<FlaskConical className="w-3.5 h-3.5" />}
        label="AI Provider"
        value={health?.ai_provider ?? "deterministic"}
      />
    </div>
  );
}
