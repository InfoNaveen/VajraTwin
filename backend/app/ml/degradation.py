"""
ml/degradation.py
=================
Degradation / health-index tracking.

health_index: 0..100
    100 = healthy baseline
      0 = severely degraded

The instantaneous health is derived DETERMINISTICALLY from current residuals,
anomaly score, fault severity and operating stress. It is then smoothed over
time (EWMA) so the displayed health is stable, not a per-frame flicker.

A short history is retained to compute health trend and degradation rate.

DATA HONESTY: health_index is a model-derived engineering indicator computed
from synthetic telemetry residuals — it is NOT a measured or certified metric.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional

# weights for the instantaneous penalty (sum ~ 1.0)
_W_ANOMALY = 0.45
_W_FAULT = 0.35
_W_THERMAL = 0.20


class DegradationTracker:
    def __init__(self, history: int = 240, ewma_alpha: float = 0.06) -> None:
        self.history = history
        self.alpha = ewma_alpha
        self._health: Optional[float] = None
        self._hist: Deque[Dict[str, float]] = deque(maxlen=history)

    def reset(self) -> None:
        self._health = None
        self._hist.clear()

    def update(
        self,
        anomaly_score: float,         # 0..100
        fault_severity: float,        # 0..1
        residuals: Dict[str, float],
        timestamp: float,
    ) -> Dict[str, object]:
        # thermal stress penalty from EGT/CHT residual magnitude
        egt = abs(float(residuals.get("delta_egt_c", 0.0)))
        cht = abs(float(residuals.get("delta_cht_c", 0.0)))
        thermal_penalty = min(1.0, (egt / 90.0) * 0.5 + (cht / 55.0) * 0.5)

        # instantaneous "unhealth" in 0..1
        unhealth = (
            _W_ANOMALY * (anomaly_score / 100.0)
            + _W_FAULT * fault_severity
            + _W_THERMAL * thermal_penalty
        )
        instant_health = max(0.0, min(100.0, 100.0 * (1.0 - unhealth)))

        # EWMA smoothing
        if self._health is None:
            self._health = instant_health
        else:
            self._health = (1 - self.alpha) * self._health + self.alpha * instant_health

        self._hist.append({"t": timestamp, "health": self._health})

        trend, rate = self._trend_and_rate()
        contributors = self._contributors(anomaly_score, fault_severity, thermal_penalty)

        return {
            "health_index": round(self._health, 1),
            "instant_health": round(instant_health, 1),
            "health_trend": trend,                        # IMPROVING | STABLE | DEGRADING
            "degradation_rate_per_min": round(rate, 3),   # health points lost / min
            "major_contributors": contributors,
            "history": [
                {"t": h["t"], "health": round(h["health"], 1)} for h in self._hist
            ],
        }

    def _trend_and_rate(self) -> tuple[str, float]:
        if len(self._hist) < 5:
            return "STABLE", 0.0
        recent = list(self._hist)[-min(30, len(self._hist)):]
        t0, h0 = recent[0]["t"], recent[0]["health"]
        t1, h1 = recent[-1]["t"], recent[-1]["health"]
        dt_min = max(1e-6, (t1 - t0) / 60.0)
        rate = (h0 - h1) / dt_min          # positive => losing health
        if rate > 0.5:
            return "DEGRADING", rate
        if rate < -0.5:
            return "IMPROVING", rate
        return "STABLE", rate

    def _contributors(self, anomaly: float, fault_sev: float, thermal: float) -> List[Dict[str, object]]:
        raw = [
            ("Anomaly score", _W_ANOMALY * (anomaly / 100.0)),
            ("Fault severity", _W_FAULT * fault_sev),
            ("Thermal stress", _W_THERMAL * thermal),
        ]
        total = sum(v for _, v in raw) or 1.0
        return [
            {"factor": name, "contribution_pct": round(100.0 * v / total, 1)}
            for name, v in sorted(raw, key=lambda t: t[1], reverse=True)
        ]

    @property
    def current_health(self) -> float:
        return self._health if self._health is not None else 100.0

    def health_history(self) -> List[Dict[str, float]]:
        return [{"t": h["t"], "health": round(h["health"], 1)} for h in self._hist]
