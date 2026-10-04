"""
ml/rul.py
=========
Trend-based Remaining Useful Life (RUL) estimator.

METHODOLOGY & HONESTY
---------------------
This is a TREND-BASED RUL ESTIMATOR operating on the synthetic digital-twin
health signal. It projects the observed health-degradation trend forward and
uses a Monte Carlo spread to express uncertainty.

It is NOT:
  - a certified engine-life prediction
  - validated against real run-to-failure data
  - a measured remaining-hours figure

If there is not enough degradation history, it returns
"Insufficient degradation history" rather than inventing a number.

Output
------
    rul_hours              : estimate (flight hours) OR None
    confidence_interval    : [p5_hours, p95_hours] OR None
    confidence_hours       : ± spread OR None
    degradation_trend      : health points lost per minute (observed)
    methodology            : human-readable method string
    status                 : OK | INSUFFICIENT_HISTORY | STABLE_NO_DECAY
"""

from __future__ import annotations

import random
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

_METHOD = "Trend-based degradation estimator (Monte Carlo spread on synthetic health signal)"

# failure threshold on the health index
_FAILURE_HEALTH = 20.0

# minimum history (samples) before we attempt a projection
_MIN_HISTORY = 10

# Demo time-base assumption (documented): the degradation trend observed over
# simulated seconds is projected onto an engine-life horizon. We treat the
# health signal as decaying over FLIGHT HOURS, where one simulated minute of
# observed decay maps to this many flight hours of real degradation. This keeps
# the RUL in a plausible flight-hour band for the demonstrator.
# THIS IS A SYNTHETIC SCALING, NOT A VALIDATED RATE.
_SIM_MIN_TO_FLIGHT_HOURS = 90.0


class RULEstimator:
    def __init__(self, history: int = 240, seed: int = 7) -> None:
        self._hist: Deque[Tuple[float, float]] = deque(maxlen=history)  # (t_seconds, health)
        self._rng = random.Random(seed)

    def reset(self) -> None:
        self._hist.clear()

    def update(self, timestamp: float, health_index: float) -> Dict[str, object]:
        self._hist.append((timestamp, health_index))
        return self.estimate()

    def _linear_decay_rate(self) -> Optional[float]:
        """Least-squares slope of health vs time (health points per second)."""
        n = len(self._hist)
        if n < _MIN_HISTORY:
            return None
        pts = list(self._hist)
        t0 = pts[0][0]
        xs = [(t - t0) for t, _ in pts]
        ys = [h for _, h in pts]
        mx = sum(xs) / n
        my = sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs)
        if denom <= 1e-9:
            return 0.0
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
        return slope  # health per second (negative => degrading)

    def estimate(self) -> Dict[str, object]:
        n = len(self._hist)
        if n < _MIN_HISTORY:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "rul_hours": None,
                "confidence_interval": None,
                "confidence_hours": None,
                "degradation_trend_per_min": 0.0,
                "methodology": _METHOD,
                "message": "Insufficient degradation history",
            }

        slope_per_s = self._linear_decay_rate() or 0.0
        decay_per_min = -slope_per_s * 60.0   # positive => losing health/min
        current_health = self._hist[-1][1]

        # Not degrading (flat or improving) -> no finite RUL
        if decay_per_min <= 0.02:
            return {
                "status": "STABLE_NO_DECAY",
                "rul_hours": None,
                "confidence_interval": None,
                "confidence_hours": None,
                "degradation_trend_per_min": round(decay_per_min, 4),
                "methodology": _METHOD,
                "message": "Health stable — no measurable degradation trend",
            }

        # Deterministic point estimate: sim-minutes until health hits failure
        # band, then mapped to flight-hours via the documented synthetic scale.
        margin = max(0.0, current_health - _FAILURE_HEALTH)
        point_sim_minutes = margin / decay_per_min
        point_hours = point_sim_minutes * _SIM_MIN_TO_FLIGHT_HOURS / 60.0

        # Monte Carlo spread: perturb the decay rate (±25%, lognormal-ish)
        samples: List[float] = []
        for _ in range(300):
            rate = decay_per_min * self._rng.uniform(0.75, 1.35)
            if rate <= 1e-6:
                continue
            samples.append((margin / rate) * _SIM_MIN_TO_FLIGHT_HOURS / 60.0)
        samples.sort()
        if samples:
            p5 = samples[int(0.05 * len(samples))]
            p95 = samples[int(0.95 * len(samples)) - 1]
        else:
            p5 = p95 = point_hours

        return {
            "status": "OK",
            "rul_hours": round(point_hours, 1),
            "confidence_interval": [round(p5, 1), round(p95, 1)],
            "confidence_hours": round((p95 - p5) / 2.0, 1),
            "degradation_trend_per_min": round(decay_per_min, 4),
            "methodology": _METHOD,
            "message": (
                "Estimated from observed degradation trend in the synthetic "
                "digital-twin environment; not a certified flight-safety prediction."
            ),
        }
