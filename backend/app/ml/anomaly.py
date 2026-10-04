"""
ml/anomaly.py
=============
Lightweight, reliable anomaly detection on physics residuals.

Method: rolling z-score on the residual vector (per channel) combined into a
single normalised anomaly score. This is deliberately simple and transparent —
it needs no training data, runs in microseconds, and its contributing-feature
breakdown is directly explainable (which the demo needs).

An optional Isolation Forest can be layered on later, but the statistical
detector is the reliable default for a live demo.

Output
------
    anomaly_score    : 0..100 (UI-friendly)
    anomaly_status   : NOMINAL | WATCH | ANOMALY
    contributing     : [{channel, z, contribution}]  sorted by contribution
"""

from __future__ import annotations

import math
from collections import deque
from typing import Deque, Dict, List

# Residual channels monitored for anomalies
_CHANNELS = [
    "delta_egt_c",
    "delta_cht_c",
    "delta_oil_temp_c",
    "delta_oil_pressure_psi",
    "delta_vibration_rms_g",
]

# Expected "healthy" standard deviation per channel (engineering priors).
# Used so the z-score is meaningful from the first frame, before enough
# history has accumulated. Units match each residual.
_PRIOR_STD = {
    "delta_egt_c": 30.0,
    "delta_cht_c": 10.0,
    "delta_oil_temp_c": 6.0,
    "delta_oil_pressure_psi": 11.0,
    "delta_vibration_rms_g": 0.25,
}

# Human-readable channel labels for the UI
CHANNEL_LABELS = {
    "delta_egt_c": "EGT residual",
    "delta_cht_c": "CHT residual",
    "delta_oil_temp_c": "Oil-temp residual",
    "delta_oil_pressure_psi": "Oil-pressure residual",
    "delta_vibration_rms_g": "Vibration residual",
}


class AnomalyDetector:
    """Rolling z-score anomaly detector over physics residuals."""

    def __init__(self, window: int = 20) -> None:
        self.window = window
        self._hist: Dict[str, Deque[float]] = {c: deque(maxlen=window) for c in _CHANNELS}

    def reset(self) -> None:
        for c in _CHANNELS:
            self._hist[c].clear()

    def _channel_z(self, channel: str, value: float) -> float:
        hist = self._hist[channel]
        hist.append(value)
        n = len(hist)
        if n < 3:
            # not enough history — use engineering prior std, zero mean
            std = _PRIOR_STD[channel]
            return abs(value) / std if std > 0 else 0.0
        mean = sum(hist) / n
        var = sum((x - mean) ** 2 for x in hist) / max(1, n - 1)
        std = math.sqrt(var)
        # blend sample std with prior so a quiet channel doesn't make tiny
        # deviations look huge
        eff_std = max(std, _PRIOR_STD[channel] * 0.5)
        return abs(value - mean) / eff_std if eff_std > 0 else 0.0

    def score(self, residuals: Dict[str, float]) -> Dict[str, object]:
        """
        Compute anomaly score from a residual dict.

        Returns a dict: anomaly_score (0..100), anomaly_status, contributing.
        """
        per_channel: List[Dict[str, float]] = []
        z_values: List[float] = []

        for c in _CHANNELS:
            val = float(residuals.get(c, 0.0))
            z = self._channel_z(c, val)
            z_values.append(z)
            per_channel.append({"channel": c, "label": CHANNEL_LABELS[c], "z": round(z, 3), "value": round(val, 3)})

        # Combined score: RMS of z-scores (penalises multi-channel faults),
        # mapped through a saturating function to 0..100.
        rms_z = math.sqrt(sum(z * z for z in z_values) / len(z_values))
        # z=0 -> 0, z=3 -> ~79, z>=5 -> ~95+, saturates at 100
        anomaly_score = round(100.0 * (1.0 - math.exp(-rms_z / 2.2)), 1)

        if anomaly_score >= 55.0:
            status = "ANOMALY"
        elif anomaly_score >= 30.0:
            status = "WATCH"
        else:
            status = "NOMINAL"

        # contribution = share of total z² (how much each channel drove it)
        total_z2 = sum(z * z for z in z_values) or 1.0
        for pc, z in zip(per_channel, z_values):
            pc["contribution"] = round(100.0 * (z * z) / total_z2, 1)

        contributing = sorted(per_channel, key=lambda d: d["contribution"], reverse=True)

        return {
            "anomaly_score": anomaly_score,
            "anomaly_status": status,
            "rms_z": round(rms_z, 3),
            "contributing_features": contributing,
        }
