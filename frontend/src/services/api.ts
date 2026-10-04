// ---------------------------------------------------------------------------
// services/api.ts — centralized API client for the VajraTwin FastAPI backend.
// All backend communication goes through this module. No scattered fetch().
// Base URL comes from VITE_API_BASE_URL (defaults to local dev).
// ---------------------------------------------------------------------------

import type {
  Analysis,
  DashboardSummary,
  FleetAircraftState,
  FleetSummary,
  HealthResponse,
  MissionRequest,
  MissionResult,
  SimTickResponse,
  SimulationStatus,
} from "../types";

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export const API_BASE_URL = BASE_URL;
export const DEFAULT_ENGINE_ID = "rotax-914-uav-01";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  timeoutMs = 8000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const j = await res.json();
        detail = (j && (j.detail || j.error)) || detail;
      } catch {
        /* non-JSON error body — keep default */
      }
      throw new ApiError(detail, res.status);
    }
    // some endpoints may return empty body
    const text = await res.text();
    return (text ? JSON.parse(text) : {}) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError("Request timed out", 0);
    }
    throw new ApiError(
      err instanceof Error ? err.message : "Network error — backend unreachable",
      0,
    );
  } finally {
    clearTimeout(timer);
  }
}

const eid = (engineId?: string) => encodeURIComponent(engineId ?? DEFAULT_ENGINE_ID);

// ── Health ─────────────────────────────────────────────────────────────────
export const api = {
  health: () => request<HealthResponse>("GET", "/health"),

  // ── Telemetry ──────────────────────────────────────────────────────────
  postTelemetry: (frame: Record<string, unknown>) =>
    request<Analysis>("POST", "/api/telemetry", frame),

  latestTelemetry: (engineId?: string) =>
    request<Record<string, unknown>>("GET", `/api/telemetry/latest?engine_id=${eid(engineId)}`),

  telemetryHistory: (engineId?: string, limit = 120) =>
    request<Record<string, unknown>[]>(
      "GET",
      `/api/telemetry/history?engine_id=${eid(engineId)}&limit=${limit}`,
    ),

  // ── Engine analytics ─────────────────────────────────────────────────────
  engineHealth: (engineId?: string) =>
    request<Record<string, unknown>>("GET", `/api/engine/${eid(engineId)}/health`),
  engineDiagnostics: (engineId?: string) =>
    request<Record<string, unknown>>("GET", `/api/engine/${eid(engineId)}/diagnostics`),
  engineDegradation: (engineId?: string) =>
    request<Record<string, unknown>>("GET", `/api/engine/${eid(engineId)}/degradation`),
  engineRul: (engineId?: string) =>
    request<Record<string, unknown>>("GET", `/api/engine/${eid(engineId)}/rul`),

  // ── Mission ──────────────────────────────────────────────────────────────
  analyzeMission: (req: MissionRequest) =>
    request<MissionResult>("POST", "/api/mission/analyze", req),
  getMission: (missionId: string) =>
    request<MissionResult>("GET", `/api/mission/${encodeURIComponent(missionId)}`),

  // ── Simulation control ─────────────────────────────────────────────────────
  simStart: (engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/start?engine_id=${eid(engineId)}`),
  simStop: (engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/stop?engine_id=${eid(engineId)}`),
  simPause: (engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/pause?engine_id=${eid(engineId)}`),
  simResume: (engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/resume?engine_id=${eid(engineId)}`),
  simReset: (engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/reset?engine_id=${eid(engineId)}`),
  simScenario: (scenario: string, severity: number | null, engineId?: string) =>
    request<SimulationStatus>(
      "POST",
      `/api/simulation/scenario?engine_id=${eid(engineId)}`,
      { scenario, severity },
    ),
  simSpeed: (speed: number, engineId?: string) =>
    request<SimulationStatus>("POST", `/api/simulation/speed?engine_id=${eid(engineId)}`, {
      speed,
    }),
  simStatus: (engineId?: string) =>
    request<SimulationStatus>("GET", `/api/simulation/status?engine_id=${eid(engineId)}`),
  simTick: (engineId?: string, dt = 1.0) =>
    request<SimTickResponse>(
      "POST",
      `/api/simulation/tick?engine_id=${eid(engineId)}&dt=${dt}`,
      undefined,
      6000,
    ),

  // ── Dashboard ──────────────────────────────────────────────────────────────
  dashboardSummary: (engineId?: string) =>
    request<DashboardSummary>("GET", `/api/dashboard/summary?engine_id=${eid(engineId)}`),

  // ── Fleet ──────────────────────────────────────────────────────────────────
  fleetSummary: () => request<FleetSummary>("GET", "/api/fleet/summary", undefined, 15000),
  fleetAircraft: () => request<FleetAircraftState[]>("GET", "/api/fleet/aircraft"),
  fleetDetail: (uavId: string) =>
    request<FleetAircraftState>("GET", `/api/fleet/${encodeURIComponent(uavId)}`),
  fleetScenario: (uavId: string, scenario: string, severity: number | null = null) =>
    request<SimulationStatus>("POST", `/api/fleet/${encodeURIComponent(uavId)}/scenario`, {
      scenario,
      severity,
    }),
  fleetResetAircraft: (uavId: string) =>
    request<FleetAircraftState>("POST", `/api/fleet/${encodeURIComponent(uavId)}/reset`),
  fleetResetAll: () => request<FleetSummary>("POST", "/api/fleet/reset", undefined, 15000),
};
