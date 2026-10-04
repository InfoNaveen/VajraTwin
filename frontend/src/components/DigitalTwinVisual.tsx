// ---------------------------------------------------------------------------
// DigitalTwinVisual — lightweight 2D engineering-style twin.
// Shows REAL engine ↔ VIRTUAL engine with expected-vs-actual for each channel.
// No 3D engine; pure SVG + data. Communicates the twin concept at a glance.
// ---------------------------------------------------------------------------

import type { ExpectedBlock, ResidualsBlock, TelemetryEcho } from "../types";

interface Props {
  telemetry: TelemetryEcho | null;
  expected: ExpectedBlock | null;
  residuals: ResidualsBlock | null;
}

interface ChannelRow {
  label: string;
  unit: string;
  actual: number | null | undefined;
  expected: number | undefined;
  delta: number | undefined;
  warn: number;
  precision: number;
}

function deltaTone(delta: number | undefined, warn: number): string {
  if (delta === undefined) return "text-gcs-sub";
  const a = Math.abs(delta);
  if (a >= warn) return "text-adv-maint";
  if (a >= warn * 0.6) return "text-adv-derate";
  return "text-adv-go";
}

export default function DigitalTwinVisual({ telemetry, expected, residuals }: Props) {
  const rows: ChannelRow[] = [
    {
      label: "EGT",
      unit: "°C",
      actual: telemetry?.egt_avg_c,
      expected: expected?.egt_c,
      delta: residuals?.delta_egt_c,
      warn: 60,
      precision: 0,
    },
    {
      label: "CHT",
      unit: "°C",
      actual: telemetry?.cht_avg_c,
      expected: expected?.cht_c,
      delta: residuals?.delta_cht_c,
      warn: 20,
      precision: 0,
    },
    {
      label: "Oil Temp",
      unit: "°C",
      actual: telemetry?.oil_temp_c,
      expected: expected?.oil_temp_c,
      delta: residuals?.delta_oil_temp_c,
      warn: 10,
      precision: 0,
    },
    {
      label: "Oil Press",
      unit: "psi",
      actual: telemetry?.oil_pressure_psi,
      expected: expected?.oil_pressure_psi,
      delta: residuals?.delta_oil_pressure_psi,
      warn: 14,
      precision: 1,
    },
    {
      label: "Vibration",
      unit: "g",
      actual: telemetry?.vibration_rms_g,
      expected: expected?.vibration_rms_g,
      delta: residuals?.delta_vibration_rms_g,
      warn: 0.9,
      precision: 2,
    },
  ];

  const EngineGlyph = ({ label, tone }: { label: string; tone: string }) => (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-16 h-16 rounded-lg border-2 ${tone} flex items-center justify-center bg-gcs-bg`}
      >
        {/* simple 4-cylinder flat-four glyph */}
        <svg width="40" height="40" viewBox="0 0 40 40">
          <rect x="6" y="16" width="28" height="8" rx="2" fill="currentColor" opacity="0.5" />
          <rect x="9" y="8" width="5" height="9" rx="1" fill="currentColor" />
          <rect x="16" y="8" width="5" height="9" rx="1" fill="currentColor" />
          <rect x="23" y="8" width="5" height="9" rx="1" fill="currentColor" />
          <rect x="12" y="23" width="16" height="7" rx="2" fill="currentColor" opacity="0.7" />
        </svg>
      </div>
      <span className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider">{label}</span>
    </div>
  );

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
        Digital Twin — Expected vs Actual
      </span>

      {/* twin diagram */}
      <div className="flex items-center justify-center gap-4">
        <EngineGlyph label="Real Engine" tone="border-gcs-accent/60 text-gcs-accent" />
        <div className="flex flex-col items-center text-gcs-sub">
          <span className="text-[9px] font-mono">telemetry →</span>
          <span className="text-[9px] font-mono">← residuals</span>
        </div>
        <EngineGlyph label="Virtual Twin" tone="border-adv-go/50 text-adv-go" />
      </div>

      {/* channel comparison table */}
      <div className="flex flex-col gap-1">
        <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-2 text-[9px] font-mono text-gcs-muted uppercase tracking-wider pb-1 border-b border-gcs-border/50">
          <span>Channel</span>
          <span className="text-right">Actual</span>
          <span className="text-right">Expected</span>
          <span className="text-right">Δ</span>
        </div>
        {rows.map((r) => (
          <div
            key={r.label}
            className="grid grid-cols-[1.2fr_1fr_1fr_1fr] gap-2 text-xs font-mono py-1 border-b border-gcs-border/30 last:border-0"
          >
            <span className="text-gcs-sub">{r.label}</span>
            <span className="text-right text-gcs-text">
              {r.actual != null ? r.actual.toFixed(r.precision) : "—"}
            </span>
            <span className="text-right text-gcs-sub">
              {r.expected != null ? r.expected.toFixed(r.precision) : "—"}
            </span>
            <span className={`text-right font-semibold ${deltaTone(r.delta, r.warn)}`}>
              {r.delta != null ? `${r.delta > 0 ? "+" : ""}${r.delta.toFixed(r.precision)}` : "—"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
