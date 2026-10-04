import { TrendingDown, TrendingUp, Minus, HeartPulse } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { DegradationBlock } from "../types";

interface Props {
  degradation: DegradationBlock | null;
  isLoading: boolean;
}

function healthColor(h: number): string {
  if (h > 70) return "text-adv-go";
  if (h > 50) return "text-adv-monitor";
  if (h > 30) return "text-adv-derate";
  return "text-adv-maint";
}
function healthBar(h: number): string {
  if (h > 70) return "bg-adv-go";
  if (h > 50) return "bg-adv-monitor";
  if (h > 30) return "bg-adv-derate";
  return "bg-adv-maint";
}

export default function DegradationPanel({ degradation, isLoading }: Props) {
  const health = degradation?.health_index ?? null;
  const trend = degradation?.health_trend ?? "STABLE";
  const rate = degradation?.degradation_rate_per_min ?? 0;
  const contributors = degradation?.major_contributors ?? [];
  const history = (degradation?.history ?? []).map((p, i) => ({
    i,
    health: p.health,
  }));

  const TrendIcon =
    trend === "DEGRADING" ? TrendingDown : trend === "IMPROVING" ? TrendingUp : Minus;
  const trendColor =
    trend === "DEGRADING"
      ? "text-adv-maint"
      : trend === "IMPROVING"
        ? "text-adv-go"
        : "text-gcs-sub";

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <HeartPulse className="w-4 h-4 text-adv-go" />
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          Degradation Tracking
        </span>
        {isLoading && (
          <span className="ml-auto text-[10px] font-mono text-gcs-muted animate-pulse">
            updating…
          </span>
        )}
      </div>

      {/* Health index */}
      <div className="flex flex-col gap-1.5">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-gcs-sub">Health Index</span>
          <span className={`font-bold text-lg ${health !== null ? healthColor(health) : "text-gcs-sub"}`}>
            {health !== null ? `${health.toFixed(1)}` : "---"}
            <span className="text-xs text-gcs-sub"> / 100</span>
          </span>
        </div>
        <div className="w-full bg-gcs-border rounded-full h-2.5 overflow-hidden">
          <div
            className={`${health !== null ? healthBar(health) : "bg-gcs-muted"} h-2.5 rounded-full transition-all duration-700`}
            style={{ width: `${Math.max(0, health ?? 0)}%` }}
          />
        </div>
      </div>

      {/* Trend + rate */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gcs-bg border border-gcs-border rounded-lg p-3">
          <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1">Trend</p>
          <p className={`flex items-center gap-1.5 font-mono text-sm font-bold ${trendColor}`}>
            <TrendIcon className="w-4 h-4" />
            {trend}
          </p>
        </div>
        <div className="bg-gcs-bg border border-gcs-border rounded-lg p-3">
          <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1">
            Degradation Rate
          </p>
          <p className="font-mono text-sm font-bold text-gcs-text">
            {rate.toFixed(2)} <span className="text-[10px] text-gcs-sub">pts/min</span>
          </p>
        </div>
      </div>

      {/* Health trend sparkline */}
      <div className="h-24">
        {history.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
              <defs>
                <linearGradient id="healthFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis dataKey="i" hide />
              <YAxis
                domain={[0, 100]}
                tick={{ fill: "#6b7280", fontSize: 9, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={false}
                width={32}
              />
              <Tooltip
                contentStyle={{
                  background: "#0a0e1a",
                  border: "1px solid #1f2937",
                  borderRadius: 8,
                  fontSize: 11,
                  fontFamily: "JetBrains Mono",
                }}
                formatter={(v: number) => [`${v.toFixed(1)}`, "health"]}
              />
              <Area
                type="monotone"
                dataKey="health"
                stroke="#22c55e"
                strokeWidth={1.8}
                fill="url(#healthFill)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gcs-sub text-xs font-mono">
            Health history builds as the simulation runs…
          </div>
        )}
      </div>

      {/* Contributors */}
      {contributors.length > 0 && (
        <div>
          <p className="text-[10px] font-mono text-gcs-sub uppercase tracking-wider mb-1">
            Major Contributors
          </p>
          <div className="flex flex-wrap gap-1.5">
            {contributors.map((c) => (
              <span
                key={c.factor}
                className="text-[10px] font-mono px-2 py-0.5 rounded border border-gcs-border bg-gcs-bg text-gcs-sub"
              >
                {c.factor} {c.contribution_pct.toFixed(0)}%
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
