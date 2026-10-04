import { useState } from "react";
import { Rocket, Loader2, AlertTriangle } from "lucide-react";
import { api, ApiError } from "../services/api";
import type { MissionRequest, MissionResult } from "../types";

interface Props {
  engineId: string;
}

const ENVIRONMENTS = ["STANDARD", "HOT", "HIGH_ALTITUDE", "HARSH"];

const RISK_COLORS: Record<string, string> = {
  LOW: "text-adv-go border-adv-go/40 bg-adv-go/10",
  MODERATE: "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10",
  ELEVATED: "text-adv-derate border-adv-derate/40 bg-adv-derate/10",
  HIGH: "text-adv-maint border-adv-maint/50 bg-adv-maint/10",
};

export default function MissionSimulator({ engineId }: Props) {
  const [req, setReq] = useState<MissionRequest>({
    mission_duration_hours: 4,
    cruise_load: 0.65,
    max_load: 0.9,
    altitude_m: 4500,
    environment: "STANDARD",
  });
  const [result, setResult] = useState<MissionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.analyzeMission({ ...req, engine_id: engineId });
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Mission analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const upd = (k: keyof MissionRequest, v: number | string) =>
    setReq((p) => ({ ...p, [k]: v }));

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Rocket className="w-4 h-4 text-gcs-accent" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Mission Reliability Simulator
        </span>
      </div>

      {/* inputs */}
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono text-gcs-sub uppercase">Duration (h)</span>
          <input
            type="number"
            min={0.5}
            max={48}
            step={0.5}
            value={req.mission_duration_hours}
            onChange={(e) => upd("mission_duration_hours", Number(e.target.value))}
            className="bg-gcs-bg border border-gcs-border rounded-lg px-2 py-1.5 font-mono text-sm text-gcs-text outline-none focus:border-gcs-accent/50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono text-gcs-sub uppercase">Altitude (m)</span>
          <input
            type="number"
            min={0}
            max={15000}
            step={100}
            value={req.altitude_m}
            onChange={(e) => upd("altitude_m", Number(e.target.value))}
            className="bg-gcs-bg border border-gcs-border rounded-lg px-2 py-1.5 font-mono text-sm text-gcs-text outline-none focus:border-gcs-accent/50"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono text-gcs-sub uppercase">Cruise Load</span>
          <input
            type="range"
            min={0.3}
            max={1.1}
            step={0.05}
            value={req.cruise_load}
            onChange={(e) => upd("cruise_load", Number(e.target.value))}
            className="accent-gcs-accent"
          />
          <span className="text-[10px] font-mono text-gcs-text">{(req.cruise_load * 100).toFixed(0)}%</span>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] font-mono text-gcs-sub uppercase">Max Load</span>
          <input
            type="range"
            min={0.3}
            max={1.2}
            step={0.05}
            value={req.max_load}
            onChange={(e) => upd("max_load", Number(e.target.value))}
            className="accent-gcs-accent"
          />
          <span className="text-[10px] font-mono text-gcs-text">{(req.max_load * 100).toFixed(0)}%</span>
        </label>
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-[10px] font-mono text-gcs-sub uppercase">Environment</span>
        <div className="flex gap-1.5 flex-wrap">
          {ENVIRONMENTS.map((env) => (
            <button
              key={env}
              onClick={() => upd("environment", env)}
              className={[
                "px-2.5 py-1 rounded font-mono text-[10px] font-semibold border transition",
                req.environment === env
                  ? "border-gcs-accent/50 bg-gcs-accent/10 text-gcs-accent"
                  : "border-gcs-border text-gcs-sub hover:text-gcs-text",
              ].join(" ")}
            >
              {env}
            </button>
          ))}
        </div>
      </label>

      <button
        onClick={run}
        disabled={loading}
        className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-gcs-accent/50 bg-gcs-accent/10 text-gcs-accent font-mono text-xs font-semibold hover:bg-gcs-accent/20 transition disabled:opacity-40"
      >
        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Rocket className="w-3.5 h-3.5" />}
        ANALYZE MISSION
      </button>

      {error && (
        <div className="flex items-center gap-2 text-xs font-mono text-adv-maint">
          <AlertTriangle className="w-3.5 h-3.5" /> {error}
        </div>
      )}

      {/* result */}
      {result && (
        <div className="flex flex-col gap-3 animate-fade-in border-t border-gcs-border pt-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gcs-sub">Completion Probability</span>
            <span className="font-mono text-2xl font-bold text-gcs-text">
              {result.completion_probability_pct.toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-lg border font-mono text-xs font-bold ${
                RISK_COLORS[result.risk_level] ?? RISK_COLORS.HIGH
              }`}
            >
              RISK: {result.risk_level}
            </span>
            <span className="text-xs font-mono text-gcs-sub">
              Limiting: <span className="text-gcs-text">{result.limiting_factor}</span>
            </span>
          </div>
          <p className="text-xs font-mono text-gcs-text">{result.recommendation}</p>
          <p className="text-[10px] font-mono text-gcs-muted">
            Health used {result.health_index_used.toFixed(0)} ·{" "}
            RUL used {result.rul_hours_used != null ? `${result.rul_hours_used} h` : "n/a"} ·{" "}
            {result.methodology}
          </p>
        </div>
      )}
    </div>
  );
}
