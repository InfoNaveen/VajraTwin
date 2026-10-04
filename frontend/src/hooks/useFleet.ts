// ---------------------------------------------------------------------------
// hooks/useFleet.ts — polls the fleet summary while the Fleet view is active.
// ---------------------------------------------------------------------------
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../services/api";
import type { FleetSummary } from "../types";

const POLL_MS = 2500;

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
      if (timer.current) clearInterval(timer.current);
      return;
    }
    refresh();
    timer.current = setInterval(refresh, POLL_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [active, refresh]);

  return { summary, loading, error, refresh, resetAll };
}
