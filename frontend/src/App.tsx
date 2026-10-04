// ---------------------------------------------------------------------------
// VajraTwin GCS — application shell / view router.
//   FLEET  → select UAV → ENGINE DIGITAL TWIN (drill-down)
// The single-engine dashboard (Phase 6) is preserved intact as EngineDashboard.
// ---------------------------------------------------------------------------
import { useCallback, useEffect, useRef, useState } from "react";

import TopBar from "./components/TopBar";
import FleetOverview from "./components/FleetOverview";
import EngineDashboard from "./components/EngineDashboard";
import { useFleet } from "./hooks/useFleet";
import { api } from "./services/api";
import type { ConnectionStatus, HealthResponse } from "./types";

type View = { kind: "fleet" } | { kind: "engine"; engineId: string };

const HEALTH_MS = 5000;

export default function App() {
  const [view, setView] = useState<View>({ kind: "fleet" });

  // Shared backend health/connection for the TopBar (single probe for the shell).
  const [connection, setConnection] = useState<ConnectionStatus>("connecting");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const healthTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const probe = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setConnection("online");
    } catch {
      setConnection("offline");
    }
  }, []);

  useEffect(() => {
    probe();
    healthTimer.current = setInterval(probe, HEALTH_MS);
    return () => {
      if (healthTimer.current) clearInterval(healthTimer.current);
    };
  }, [probe]);

  const demoMode = health?.database.demo_mode ?? false;
  const fleet = useFleet(view.kind === "fleet");

  const topEngineId = view.kind === "engine" ? view.engineId : "FLEET";

  return (
    <div className="min-h-screen flex flex-col bg-gcs-bg">
      <TopBar
        connection={connection}
        demoMode={demoMode}
        engineId={topEngineId}
        sim={null}
      />

      <main className="flex-1 px-6 py-5 max-w-[1600px] w-full mx-auto">
        {view.kind === "fleet" ? (
          <FleetOverview
            summary={fleet.summary}
            loading={fleet.loading}
            error={fleet.error}
            demoMode={demoMode}
            onSelect={(uavId) => setView({ kind: "engine", engineId: uavId })}
            onResetAll={fleet.resetAll}
          />
        ) : (
          <EngineDashboard
            engineId={view.engineId}
            connection={connection}
            health={health}
            onBack={() => setView({ kind: "fleet" })}
          />
        )}
      </main>

      <footer className="px-6 py-2 border-t border-gcs-border bg-gcs-surface flex items-center justify-between flex-wrap gap-2">
        <span className="text-[10px] font-mono text-gcs-muted">
          VAJRATWIN · SIH 2026 (PS26054) · FLEET → UAV → ENGINE DIGITAL TWIN
        </span>
        <span className="text-[10px] font-mono text-gcs-muted">
          FastAPI · MongoDB · Physics Surrogate · Deterministic Diagnostics
        </span>
      </footer>
    </div>
  );
}
