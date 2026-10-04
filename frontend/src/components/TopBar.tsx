import { Activity, Cpu, Database, Wifi, WifiOff, Loader2, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import type { ConnectionStatus, SimulationStatus } from "../types";

interface Props {
  connection: ConnectionStatus;
  demoMode: boolean;
  engineId: string;
  sim: SimulationStatus | null;
}

function ConnPill({ connection }: { connection: ConnectionStatus }) {
  const map = {
    online: { icon: <Wifi className="w-3.5 h-3.5" />, label: "BACKEND ONLINE", cls: "text-adv-go" },
    offline: { icon: <WifiOff className="w-3.5 h-3.5" />, label: "BACKEND OFFLINE", cls: "text-adv-maint" },
    connecting: {
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
      label: "CONNECTING…",
      cls: "text-gcs-sub",
    },
  }[connection];
  return (
    <span className={`flex items-center gap-1.5 font-mono text-xs font-semibold ${map.cls}`}>
      {map.icon}
      {map.label}
    </span>
  );
}

export default function TopBar({ connection, demoMode, engineId, sim }: Props) {
  const [clock, setClock] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const simState = sim
    ? sim.paused
      ? "PAUSED"
      : sim.running
        ? "RUNNING"
        : "STOPPED"
    : "—";

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gcs-surface border-b border-gcs-border flex-wrap gap-y-2">
      {/* Left — brand + engine */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-9 h-9 bg-gcs-accent/10 border border-gcs-accent/30 rounded-lg flex items-center justify-center">
            <Activity className="w-5 h-5 text-gcs-accent" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-widest text-gcs-text leading-none">
              VAJRATWIN
            </div>
            <div className="text-[10px] text-gcs-sub font-mono leading-none mt-0.5">
              UAV ENGINE DIGITAL TWIN · GCS
            </div>
          </div>
        </div>

        <div className="h-7 w-px bg-gcs-border" />

        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-gcs-sub" />
          <span className="font-mono text-xs text-gcs-sub">ENGINE</span>
          <span className="font-mono text-xs text-gcs-accent font-semibold">{engineId}</span>
        </div>
      </div>

      {/* Right — status cluster */}
      <div className="flex items-center gap-3 flex-wrap">
        <ConnPill connection={connection} />

        <div className="h-5 w-px bg-gcs-border" />

        {/* DB / demo mode */}
        <span
          className={[
            "flex items-center gap-1.5 font-mono text-xs font-semibold px-2 py-0.5 rounded border",
            demoMode
              ? "text-adv-monitor border-adv-monitor/40 bg-adv-monitor/10"
              : "text-adv-go border-adv-go/30 bg-adv-go/10",
          ].join(" ")}
          title={
            demoMode
              ? "MongoDB unavailable — using in-memory persistence (intentional demonstrator mode)"
              : "Connected to MongoDB"
          }
        >
          <Database className="w-3.5 h-3.5" />
          {demoMode ? "DEMO MODE" : "MONGODB"}
        </span>

        <div className="h-5 w-px bg-gcs-border" />

        {/* Sim state */}
        <span
          className={[
            "font-mono text-xs font-semibold",
            simState === "RUNNING"
              ? "text-adv-go"
              : simState === "PAUSED"
                ? "text-adv-monitor"
                : "text-gcs-sub",
          ].join(" ")}
        >
          SIM: {simState}
        </span>

        <div className="h-5 w-px bg-gcs-border" />

        <span className="flex items-center gap-1.5 font-mono text-xs text-gcs-sub">
          <Clock className="w-3.5 h-3.5" />
          {clock.toLocaleTimeString()}
        </span>
      </div>
    </header>
  );
}
