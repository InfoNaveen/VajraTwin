// ---------------------------------------------------------------------------
// hooks/useFleet.ts
// ---------------------------------------------------------------------------
// Drives Fleet Operations progression while the Fleet view is active.
//
// The fleet is advanced by the backend's fleet-owned tick endpoint
// (POST /api/fleet/tick), which steps ALL six EngineService instances through
// their real pipeline and returns the aggregated summary. Polling a read-only
// GET would NOT advance the engines, so this hook ticks rather than merely
// reads.
//
// Ownership model (prevents double-ticking a single engine):
//   - Fleet view active  → this hook ticks the whole fleet.
//   - Engine view active → App sets `active=false` here, so the fleet loop
//     stops; the Engine Dashboard's useVajraTwin owns that engine's ticking.
//   Never are both loops advancing the same engine simultaneously.
//
// On deactivation the interval is cleared and no background ticking leaks.
// ---------------------------------------------------------------------------

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type { FleetSummary } from "../types";

const TICK_MS = 2000;
const TICK_DT = 1.5;

export interface FleetState {
  summary: FleetSummary | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  resetAll: () => Promise<void>;
}

export function useFleet(active: boolean): FleetState {
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const inFlight = useRef(false);

  // One fleet tick: advance all engines + get aggregated summary.
  const tick = useCallback(async () => {
    if (inFlight.current) return; // never overlap requests
    inFlight.current = true;
    try {
      const s = await api.fleetTick(TICK_DT);
      setSummary(s);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Fleet unavailable");
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  // Read-only refresh (used after an explicit control action).
  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const s = await api.fleetSummary();
      setSummary(s);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Fleet unavailable");
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  }, []);

  const resetAll = useCallback(async () => {
    setLoading(true);
    try {
      const s = await api.fleetResetAll();
      setSummary(s);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Fleet reset failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!active) {
      // Leaving the fleet view: stop ticking, clean up the interval.
      if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
      return;
    }
    // Entering the fleet view: tick immediately, then on an interval.
    tick();
    timer.current = setInterval(tick, TICK_MS);
    return () => {
      if (timer.current) {
        clearInterval(timer.current);
        timer.current = null;
      }
    };
  }, [active, tick]);

  return { summary, loading, error, refresh, resetAll };
}
