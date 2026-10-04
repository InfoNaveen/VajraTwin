import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { ChartPoint } from "../types";

interface Props {
  data: ChartPoint[];
  mode: "thermal" | "mechanical";
}

interface TipPayloadEntry {
  color: string;
  name: string;
  value: number;
}

function Tip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TipPayloadEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gcs-bg border border-gcs-border rounded-lg px-3 py-2 text-xs font-mono shadow-xl">
      <p className="text-gcs-sub mb-1">t+{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}:{" "}
          <b>
            {p.value > 0 ? "+" : ""}
            {p.value.toFixed(2)}
          </b>
        </p>
      ))}
    </div>
  );
}

const THERMAL = [
  { key: "delta_egt_c", name: "ΔEGT (°C)", color: "#fb923c", warn: 60 },
  { key: "delta_cht_c", name: "ΔCHT (°C)", color: "#38bdf8", warn: 20 },
];
const MECH = [
  { key: "delta_oil_temp_c", name: "ΔOil Temp (°C)", color: "#a78bfa", warn: 10 },
  { key: "delta_oil_pressure_psi", name: "ΔOil Press (psi)", color: "#34d399", warn: 14 },
  { key: "delta_vibration_rms_g", name: "ΔVib (g)", color: "#f472b6", warn: 0.9 },
];

export default function ResidualsChart({ data, mode }: Props) {
  const lines = mode === "thermal" ? THERMAL : MECH;
  const title = mode === "thermal" ? "Thermal Residuals" : "Mechanical Residuals";
  const subtitle =
    mode === "thermal"
      ? "Δ = Actual − Expected · dashed = warn band"
      : "Oil temp · oil pressure · vibration deviations";
  const isEmpty = data.length === 0;

  return (
    <div className="bg-gcs-surface border border-gcs-border rounded-xl p-4 flex flex-col gap-3">
      <div>
        <span className="text-xs font-mono font-semibold uppercase tracking-widest text-gcs-sub">
          {title}
        </span>
        <p className="text-gcs-sub text-[10px] mt-0.5 font-mono">{subtitle}</p>
      </div>

      <div className="h-48">
        {isEmpty ? (
          <div className="h-full flex items-center justify-center text-gcs-sub text-sm font-mono">
            Awaiting live residual stream…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <ReferenceLine y={0} stroke="#374151" strokeWidth={1} />
              {lines.flatMap((l) => [
                <ReferenceLine
                  key={`${l.key}+`}
                  y={l.warn}
                  stroke={l.color}
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  strokeOpacity={0.35}
                />,
                <ReferenceLine
                  key={`${l.key}-`}
                  y={-l.warn}
                  stroke={l.color}
                  strokeDasharray="4 4"
                  strokeWidth={1}
                  strokeOpacity={0.35}
                />,
              ])}
              <XAxis
                dataKey="time"
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={{ stroke: "#1f2937" }}
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${Number(v).toFixed(0)}`}
                domain={["auto", "auto"]}
              />
              <Tooltip content={<Tip />} />
              <Legend
                wrapperStyle={{ fontSize: "10px", fontFamily: "JetBrains Mono", paddingTop: "4px" }}
                formatter={(value) => <span style={{ color: "#9ca3af" }}>{value}</span>}
              />
              {lines.map((l) => (
                <Line
                  key={l.key}
                  type="monotone"
                  dataKey={l.key}
                  name={l.name}
                  stroke={l.color}
                  strokeWidth={1.8}
                  dot={false}
                  activeDot={{ r: 3 }}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
