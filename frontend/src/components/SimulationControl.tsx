import { Play, Pause, Square, RotateCcw, Zap, Gauge as SpeedIcon } from "lucide-react";
import type { SimulationStatus } from "../types";

interface Props {
  sim: SimulationStatus | null;
  busy: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  onScenario: (scenario: string) => void;
  onSpeed: (speed: number) => void;
}

const SPEEDS = [1, 2, 4];

export default function SimulationControl({
  sim,
  busy,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
  onScenario,
  onSpeed,
}: Props) {
  const running = sim?.running ?? false;
  const paused = sim?.paused ?? false;
  const scenarios = sim?.available_scenarios ?? [];
  const current = sim?.scenario ?? "HEALTHY";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Zap className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Simulation Control Center
        </span>
      </div>

      {/* Transport controls */}
      <div className="flex flex-wrap gap-2">
        {!running ? (
          <button
            onClick={onStart}
            disabled={busy}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-adv-go/50 bg-adv-go/10 text-adv-go font-mono text-xs font-semibold hover:bg-adv-go/20 transition disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5" /> START
          </button>
        ) : paused ? (
          <button
            onClick={onResume}
            disabled={busy}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-adv-go/50 bg-adv-go/10 text-adv-go font-mono text-xs font-semibold hover:bg-adv-go/20 transition disabled:opacity-40"
          >
            <Play className="w-3.5 h-3.5" /> RESUME
          </button>
        ) : (
          <button
            onClick={onPause}
            disabled={busy}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-adv-monitor/50 bg-adv-monitor/10 text-adv-monitor font-mono text-xs font-semibold hover:bg-adv-monitor/20 transition disabled:opacity-40"
          >
            <Pause className="w-3.5 h-3.5" /> PAUSE
          </button>
        )}

        <button
          onClick={onStop}
          disabled={busy || !running}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gcs-border bg-gcs-bg text-gcs-sub font-mono text-xs font-semibold hover:border-adv-maint/40 hover:text-adv-maint transition disabled:opacity-40"
        >
          <Square className="w-3.5 h-3.5" /> STOP
        </button>

        <button
          onClick={onReset}
          disabled={busy}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gcs-border bg-gcs-bg text-gcs-sub font-mono text-xs font-semibold hover:border-gcs-accent/40 hover:text-gcs-accent transition disabled:opacity-40"
        >
          <RotateCcw className="w-3.5 h-3.5" /> RESET
        </button>

        {/* speed */}
        <div className="flex items-center gap-1 ml-auto">
          <SpeedIcon className="w-3.5 h-3.5 text-gcs-sub" />
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => onSpeed(s)}
              disabled={busy}
              className={[
                "px-2 py-1 rounded font-mono text-[10px] font-semibold border transition",
                (sim?.speed ?? 1) === s
                  ? "border-gcs-accent/50 bg-gcs-accent/10 text-gcs-accent"
                  : "border-gcs-border text-gcs-sub hover:text-gcs-text",
              ].join(" ")}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Scenario selector */}
      <div>
        <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-2">
          Fault Scenario Injection
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {scenarios.map((sc) => {
            const active = sc.key === current;
            const isHealthy = sc.key === "HEALTHY";
            return (
              <button
                key={sc.key}
                onClick={() => onScenario(sc.key)}
                disabled={busy}
                title={sc.description}
                className={[
                  "px-2.5 py-2 rounded-lg border font-mono text-[10px] font-semibold text-left transition disabled:opacity-40",
                  active
                    ? isHealthy
                      ? "border-adv-go/50 bg-adv-go/10 text-adv-go"
                      : "border-adv-maint/50 bg-adv-maint/10 text-adv-maint"
                    : "border-gcs-border bg-gcs-bg text-gcs-sub hover:border-gcs-accent/40 hover:text-gcs-text",
                ].join(" ")}
              >
                {sc.label}
              </button>
            );
          })}
        </div>
      </div>

      <p className="text-[10px] font-mono text-gcs-muted">
        Select a fault while running to watch it propagate through residuals → anomaly → fault →
        health → RUL → advisory.
      </p>
    </div>
  );
}
