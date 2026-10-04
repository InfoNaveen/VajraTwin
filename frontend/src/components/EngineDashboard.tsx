// ---------------------------------------------------------------------------
// EngineDashboard — the Phase 6 single-engine Digital Twin dashboard, now
// parameterised by engineId so it works both standalone and as a fleet
// drill-down. Behaviour is unchanged from Phase 6.
// ---------------------------------------------------------------------------
import {
  Gauge,
  Wind,
  Thermometer,
  Droplet,
  Gauge as PressureIcon,
  Vibrate,
  Fuel,
  ArrowLeft,
} from "lucide-react";

import HeroHealth from "./HeroHealth";
import StatCard from "./StatCard";
import DigitalTwinVisual from "./DigitalTwinVisual";
import ResidualsChart from "./ResidualsChart";
import DiagnosticsPanel from "./DiagnosticsPanel";
import DegradationPanel from "./DegradationPanel";
import RulPanel from "./RulPanel";
import SystemStatusPanel from "./SystemStatusPanel";
import SimulationControl from "./SimulationControl";
import MissionSimulator from "./MissionSimulator";
import { useVajraTwin } from "../hooks/useVajraTwin";
import type { ConnectionStatus, HealthResponse } from "../types";

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub mb-3">
      {children}
    </p>
  );
}

interface Props {
  engineId: string;
  // shared connection/health from the app shell (avoids duplicate /health polls)
  connection: ConnectionStatus;
  health: HealthResponse | null;
  onBack?: () => void;
}

export default function EngineDashboard({ engineId, connection, health, onBack }: Props) {
  const vt = useVajraTwin(engineId);
  const a = vt.analysis;
  const t = a?.telemetry ?? null;
  const res = a?.residuals ?? null;
  const busyTick = vt.sim?.running === true && !vt.sim.paused;

  // merge app-shell connection with this hook's own view
  const conn = connection === "offline" ? "offline" : vt.connection;

  const egtAlert = res ? Math.abs(res.delta_egt_c) >= 60 : false;
  const chtAlert = res ? Math.abs(res.delta_cht_c) >= 20 : false;
  const oilTAlert = res ? Math.abs(res.delta_oil_temp_c) >= 10 : false;
  const oilPAlert = res ? Math.abs(res.delta_oil_pressure_psi) >= 14 : false;
  const vibAlert = res ? Math.abs(res.delta_vibration_rms_g) >= 0.9 : false;

  return (
    <div className="space-y-5">
      {/* offline banner */}
      {conn === "offline" && (
        <div className="flex items-center gap-3 px-4 py-3 bg-adv-maint/10 border border-adv-maint/30 rounded-xl text-adv-maint text-xs font-mono animate-fade-in">
          <span className="font-semibold shrink-0">BACKEND OFFLINE</span>
          <span className="truncate">
            Cannot reach the VajraTwin API (uvicorn app.main:app --port 8000).
          </span>
        </div>
      )}
      {vt.error && conn !== "offline" && (
        <div className="flex items-center gap-3 px-4 py-2.5 bg-adv-monitor/10 border border-adv-monitor/30 rounded-xl text-adv-monitor text-xs font-mono">
          <span className="font-semibold shrink-0">NOTICE</span>
          <span className="truncate">{vt.error}</span>
        </div>
      )}

      {/* Title + back */}
      <section className="flex items-start justify-between flex-wrap gap-2">
        <div className="flex items-start gap-3">
          {onBack && (
            <button
              onClick={onBack}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gcs-border bg-gcs-bg text-gcs-sub font-mono text-xs font-semibold hover:border-gcs-accent/40 hover:text-gcs-accent transition mt-0.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> FLEET
            </button>
          )}
          <div>
            <h1 className="text-lg font-bold text-gcs-text tracking-wide">
              {engineId}
              <span className="text-gcs-sub font-normal text-base">
                {" "}
                — Rotax 914 F/UL · Closed-Loop Digital Twin
              </span>
            </h1>
            <p className="text-xs font-mono text-gcs-sub mt-0.5">
              Physics surrogate · deterministic diagnostics · degradation · trend-based RUL ·
              mission reliability
            </p>
          </div>
        </div>
        <span className="text-[10px] font-mono px-2 py-1 rounded border border-adv-monitor/40 bg-adv-monitor/10 text-adv-monitor">
          SYNTHETIC TELEMETRY · DEMONSTRATOR
        </span>
      </section>

      <HeroHealth
        degradation={a?.degradation ?? null}
        advisory={a?.advisory ?? null}
        fault={a?.fault ?? null}
        rul={a?.rul ?? null}
      />

      <section>
        <SectionLabel>Live Sensor Telemetry</SectionLabel>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Engine Speed" value={t?.rpm} unit="RPM" icon={Gauge} color="text-tel-rpm" precision={0} />
          <StatCard label="MAP" value={t?.map_kpa} unit="kPa" icon={Wind} color="text-tel-map" precision={1} />
          <StatCard label="EGT" value={t?.egt_avg_c} unit="°C" icon={Thermometer} color="text-tel-egt" precision={0} isAlert={egtAlert} subLabel="Exp:" subValue={a?.expected.egt_c} />
          <StatCard label="CHT" value={t?.cht_avg_c} unit="°C" icon={Thermometer} color="text-tel-cht" precision={0} isAlert={chtAlert} subLabel="Exp:" subValue={a?.expected.cht_c} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3">
          <StatCard label="Oil Temp" value={t?.oil_temp_c} unit="°C" icon={Droplet} color="text-[#a78bfa]" precision={0} isAlert={oilTAlert} subLabel="Exp:" subValue={a?.expected.oil_temp_c} />
          <StatCard label="Oil Pressure" value={t?.oil_pressure_psi} unit="psi" icon={PressureIcon} color="text-[#34d399]" precision={1} isAlert={oilPAlert} subLabel="Exp:" subValue={a?.expected.oil_pressure_psi} />
          <StatCard label="Vibration" value={t?.vibration_rms_g} unit="g" icon={Vibrate} color="text-[#f472b6]" precision={2} isAlert={vibAlert} subLabel="Exp:" subValue={a?.expected.vibration_rms_g} />
          <StatCard label="Fuel Flow" value={t?.fuel_flow_lph} unit="L/h" icon={Fuel} color="text-[#93c5fd]" precision={1} />
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <DigitalTwinVisual telemetry={t} expected={a?.expected ?? null} residuals={res} />
        <div className="xl:col-span-2 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ResidualsChart data={vt.chart} mode="thermal" />
          <ResidualsChart data={vt.chart} mode="mechanical" />
        </div>
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <DiagnosticsPanel
          anomaly={a?.anomaly ?? null}
          fault={a?.fault ?? null}
          explanation={a?.explanation ?? null}
          isLoading={busyTick}
        />
        <DegradationPanel degradation={a?.degradation ?? null} isLoading={busyTick} />
        <RulPanel rul={a?.rul ?? null} isLoading={busyTick} />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <SimulationControl
          sim={vt.sim}
          busy={vt.busy}
          onStart={vt.start}
          onPause={vt.pause}
          onResume={vt.resume}
          onStop={vt.stop}
          onReset={vt.reset}
          onScenario={(s) => vt.setScenario(s)}
          onSpeed={vt.setSpeed}
        />
        <MissionSimulator engineId={engineId} />
        <SystemStatusPanel connection={conn} health={health} sim={vt.sim} analysis={a} />
      </section>

      <div className="h-4" />
    </div>
  );
}
