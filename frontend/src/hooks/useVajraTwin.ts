// ---------------------------------------------------------------------------
// hooks/useVajraTwin.ts
// ---------------------------------------------------------------------------
// The single orchestration hook for the GCS. Owns:
//   - backend health / connection state (DEMO MODE detection)
//   - simulation control (start/stop/pause/reset/scenario/speed)
//   - the polling loop that drives /api/simulation/tick while running
//   - a rolling chart buffer built from analysis frames
//
// Polling strategy (simple, not over-engineered):
//   - while running: tick + status every ~1.5 s
//   - health probe every ~5 s (keeps DEMO/online state fresh)
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type {
  Analysis,
  ChartPoint,
  ConnectionStatus,
  HealthResponse,
  SimulationStatus,
} from "../types";

const TICK_MS = 1500;
const HEALTH_MS = 5000;
const MAX_POINTS = 80;

function hms(simTime: number): string {
  const s = Math.floor(simTime % 60);
  const m = Math.floor(simTime / 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export interface VajraTwinState {
  connection: ConnectionStatus;
  health: HealthResponse | null;
  demoMode: boolean;
  sim: SimulationStatus | null;
  analysis: Analysis | null;
  chart: ChartPoint[];
  error: string | null;
  busy: boolean;
  // controls
  start: () => Promise<void>;
  stop: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  reset: () => Promise<void>;
  setScenario: (scenario: string, severity?: number | null) => Promise<void>;
  setSpeed: (speed: number) => Promise<void>;
}

export function useVajraTwin(engineId?: string): VajraTwinState {
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sim, setSim] = useState<SimulationStatus | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [chart, setChart] = useState<ChartPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const healthRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const inFlight = useRef(false);

  const demoMode = health?.database.demo_mode ?? false;

  // ── health probe ───────────────────────────────────────────────────────────
  const probeHealth = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setConnection("online");
    } catch {
      setConnection("offline");
    }
  }, []);

  // ── push an analysis frame into the chart buffer ───────────────────────────
  const pushChart = useCallback((a: Analysis) => {
    const point: ChartPoint = {
      tick: a.tick,
      time: hms(a.sim_time_s),
      delta_egt_c: a.residuals.delta_egt_c,
      delta_cht_c: a.residuals.delta_cht_c,
      delta_oil_temp_c: a.residuals.delta_oil_temp_c,
      delta_oil_pressure_psi: a.residuals.delta_oil_pressure_psi,
      delta_vibration_rms_g: a.residuals.delta_vibration_rms_g,
      health_index: a.degradation.health_index,
      anomaly_score: a.anomaly.anomaly_score,
    };
    setChart((prev) => {
      const next = [...prev, point];
      return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
    });
  }, []);

  // ── one simulation tick ─────────────────────────────────────────────────────
  const doTick = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const res = await api.simTick(engineId, 1.5);
      setSim(res.status);
      if (res.advanced && res.analysis) {
        setAnalysis(res.analysis);
        pushChart(res.analysis);
      }
      setConnection("online");
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) {
        setConnection("offline");
        setError("Backend unreachable");
      }
    } finally {
      inFlight.current = false;
    }
  }, [engineId, pushChart]);

  // ── control helpers ─────────────────────────────────────────────────────────
  const withBusy = useCallback(
    async (fn: () => Promise<SimulationStatus>) => {
      setBusy(true);
      try {
        const s = await fn();
        setSim(s);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Command failed");
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const start = useCallback(() => withBusy(() => api.simStart(engineId)), [engineId, withBusy]);
  const stop = useCallback(() => withBusy(() => api.simStop(engineId)), [engineId, withBusy]);
  const pause = useCallback(() => withBusy(() => api.simPause(engineId)), [engineId, withBusy]);
  const resume = useCallback(() => withBusy(() => api.simResume(engineId)), [engineId, withBusy]);
  const reset = useCallback(
    () =>
      withBusy(async () => {
        const s = await api.simReset(engineId);
        setAnalysis(null);
        setChart([]);
        return s;
      }),
    [engineId, withBusy],
  );
  const setScenario = useCallback(
    (scenario: string, severity: number | null = null) =>
      withBusy(() => api.simScenario(scenario, severity, engineId)),
    [engineId, withBusy],
  );
  const setSpeed = useCallback(
    (speed: number) => withBusy(() => api.simSpeed(speed, engineId)),
    [engineId, withBusy],
  );

  // ── lifecycle ────────────────────────────────────────────────────────────────
  useEffect(() => {
    probeHealth();
    // initial sim status
    api.simStatus(engineId).then(setSim).catch(() => undefined);

    healthRef.current = setInterval(probeHealth, HEALTH_MS);
    tickRef.current = setInterval(doTick, TICK_MS);

    return () => {
      if (healthRef.current) clearInterval(healthRef.current);
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [probeHealth, doTick, engineId]);

  return {
    connection,
    health,
    demoMode,
    sim,
    analysis,
    chart,
    error,
    busy,
    start,
    stop,
    pause,
    resume,
    reset,
    setScenario,
    setSpeed,
  };
}
