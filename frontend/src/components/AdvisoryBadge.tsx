import { AlertTriangle, CheckCircle, Info, Wrench, Loader2 } from "lucide-react";
import type { AdvisoryState } from "../types";

interface Props {
  advisory: AdvisoryState | "PENDING";
  pulse?: boolean;
  size?: "sm" | "lg";
}

const CFG: Record<
  string,
  { bg: string; border: string; text: string; glow: string; icon: React.ReactNode; label: string }
> = {
  GO: {
    bg: "bg-adv-go/10",
    border: "border-adv-go/50",
    text: "text-adv-go",
    glow: "shadow-[0_0_16px_rgba(34,197,94,0.25)]",
    icon: <CheckCircle className="w-5 h-5" />,
    label: "GO",
  },
  "GO WITH MONITORING": {
    bg: "bg-adv-monitor/10",
    border: "border-adv-monitor/50",
    text: "text-adv-monitor",
    glow: "shadow-[0_0_16px_rgba(234,179,8,0.25)]",
    icon: <Info className="w-5 h-5" />,
    label: "GO WITH MONITORING",
  },
  "GO WITH DERATE": {
    bg: "bg-adv-derate/10",
    border: "border-adv-derate/50",
    text: "text-adv-derate",
    glow: "shadow-[0_0_16px_rgba(249,115,22,0.25)]",
    icon: <AlertTriangle className="w-5 h-5" />,
    label: "GO WITH DERATE",
  },
  "MAINTENANCE REQUIRED": {
    bg: "bg-adv-maint/10",
    border: "border-adv-maint/60",
    text: "text-adv-maint",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.4)]",
    icon: <Wrench className="w-5 h-5" />,
    label: "MAINTENANCE REQUIRED",
  },
  PENDING: {
    bg: "bg-gcs-muted/10",
    border: "border-gcs-muted/30",
    text: "text-gcs-sub",
    glow: "",
    icon: <Loader2 className="w-5 h-5 animate-spin" />,
    label: "AWAITING DATA",
  },
};

export default function AdvisoryBadge({ advisory, pulse = false, size = "lg" }: Props) {
  const c = CFG[advisory] ?? CFG["PENDING"];
  const pad = size === "lg" ? "px-5 py-3 text-sm" : "px-3 py-1.5 text-xs";
  return (
    <div
      className={[
        "flex items-center gap-3 rounded-xl border transition-all duration-500",
        pad,
        c.bg,
        c.border,
        c.text,
        c.glow,
        pulse && advisory === "MAINTENANCE REQUIRED" ? "animate-pulse" : "",
      ].join(" ")}
    >
      {c.icon}
      <span className="font-mono font-bold tracking-widest uppercase">{c.label}</span>
    </div>
  );
}
