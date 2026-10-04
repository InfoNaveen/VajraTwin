"""
ml/fault_diagnosis.py
=====================
DETERMINISTIC fault classification from physics residuals + sensor
relationships. No ML model decides the fault state — this is pure engineering
logic so it is reproducible, explainable and safe.

Fault classes
-------------
    NORMAL
    EGT_ANOMALY
    CHT_OVERHEAT
    OIL_PRESSURE_LOW
    VIBRATION_ANOMALY
    BOOST_TURBO_ANOMALY
    SENSOR_ANOMALY
    MULTI_PARAMETER_FAULT

Each result carries the evidence (which residuals crossed which thresholds),
so the UI and the AI explainer can cite concrete numbers.
"""

from __future__ import annotations

from typing import Dict, List

# Residual thresholds (engineering limits, °C / psi / g).
# WARN = investigate; CRIT = clear fault signature.
TH = {
    "egt_warn": 60.0, "egt_crit": 90.0,
    "cht_warn": 20.0, "cht_crit": 32.0,
    "oil_temp_warn": 10.0, "oil_temp_crit": 18.0,
    "oil_press_warn": 14.0, "oil_press_crit": 22.0,  # magnitude of drop
    "vib_warn": 0.9, "vib_crit": 1.8,
    "map_warn": 10.0, "map_crit": 18.0,
}

FAULT_LABELS = {
    "NORMAL": "Normal",
    "EGT_ANOMALY": "EGT Anomaly",
    "CHT_OVERHEAT": "CHT Overheat",
    "OIL_PRESSURE_LOW": "Oil Pressure Low",
    "VIBRATION_ANOMALY": "Vibration Anomaly",
    "BOOST_TURBO_ANOMALY": "Boost / Turbo Anomaly",
    "SENSOR_ANOMALY": "Sensor Anomaly",
    "MULTI_PARAMETER_FAULT": "Multi-Parameter Fault",
}


def diagnose_fault(residuals: Dict[str, float], twin_state: Dict[str, float] | None = None) -> Dict[str, object]:
    """
    Classify the fault from physics residuals.

    Parameters
    ----------
    residuals : dict with delta_* keys from PhysicsEngine.calculate_residuals
    twin_state: optional engine state (load_factor, map_kpa) for boost logic

    Returns
    -------
    dict: fault_class, fault_label, severity (0..1), evidence[], active_channels[]
    """
    twin_state = twin_state or {}

    d_egt = float(residuals.get("delta_egt_c", 0.0))
    d_cht = float(residuals.get("delta_cht_c", 0.0))
    d_oilt = float(residuals.get("delta_oil_temp_c", 0.0))
    d_oilp = float(residuals.get("delta_oil_pressure_psi", 0.0))
    d_vib = float(residuals.get("delta_vibration_rms_g", 0.0))

    evidence: List[Dict[str, object]] = []
    active: List[str] = []

    def flag(channel: str, value: float, warn: float, crit: float, direction: str) -> str:
        """Return '', 'WARN' or 'CRIT' and record evidence."""
        mag = abs(value)
        level = ""
        if mag >= crit:
            level = "CRIT"
        elif mag >= warn:
            level = "WARN"
        if level:
            active.append(channel)
            evidence.append({
                "channel": channel,
                "value": round(value, 2),
                "threshold": crit if level == "CRIT" else warn,
                "level": level,
                "direction": direction,
            })
        return level

    # Direction matters for some channels (oil pressure LOW is the fault).
    egt_level = flag("EGT", d_egt, TH["egt_warn"], TH["egt_crit"], "high" if d_egt > 0 else "low")
    cht_level = flag("CHT", d_cht, TH["cht_warn"], TH["cht_crit"], "high" if d_cht > 0 else "low")
    oilt_level = flag("OIL_TEMP", d_oilt, TH["oil_temp_warn"], TH["oil_temp_crit"], "high" if d_oilt > 0 else "low")
    oilp_level = flag("OIL_PRESS", d_oilp, TH["oil_press_warn"], TH["oil_press_crit"], "low" if d_oilp < 0 else "high")
    vib_level = flag("VIBRATION", d_vib, TH["vib_warn"], TH["vib_crit"], "high" if d_vib > 0 else "low")

    # MAP deviation from state (boost) — compare actual vs expected cruise map.
    map_kpa = float(twin_state.get("map_kpa", 0.0))
    load = float(twin_state.get("load_factor", 0.0))

    # Count critical channels for multi-fault logic
    crit_channels = [c for c, lv in [
        ("EGT", egt_level), ("CHT", cht_level), ("OIL_TEMP", oilt_level),
        ("OIL_PRESS", oilp_level), ("VIBRATION", vib_level)
    ] if lv == "CRIT"]
    warn_or_crit = [c for c, lv in [
        ("EGT", egt_level), ("CHT", cht_level), ("OIL_TEMP", oilt_level),
        ("OIL_PRESS", oilp_level), ("VIBRATION", vib_level)
    ] if lv]

    # ── classification (priority order) ──────────────────────────────────────

    # Multi-parameter: 2+ critical channels across different subsystems
    if len(crit_channels) >= 2:
        fault = "MULTI_PARAMETER_FAULT"

    # Oil pressure low is safety-critical, check early
    elif oilp_level == "CRIT" and d_oilp < 0:
        fault = "OIL_PRESSURE_LOW"

    # Vibration anomaly (misfire/imbalance): big vib, often EGT drop
    elif vib_level == "CRIT":
        fault = "VIBRATION_ANOMALY"

    # Boost/turbo: EGT+CHT up together AND high MAP/load (over-boost signature)
    elif egt_level and cht_level and d_egt > 0 and d_cht > 0 and (map_kpa >= 108.0 or load >= 1.25):
        fault = "BOOST_TURBO_ANOMALY"

    # CHT overheat: CHT critical (cooling failure)
    elif cht_level == "CRIT" and d_cht > 0:
        fault = "CHT_OVERHEAT"

    # Sensor anomaly: EGT deviates alone with NO corroborating channel
    elif egt_level and not cht_level and not oilt_level and not oilp_level and not vib_level:
        fault = "SENSOR_ANOMALY"

    # EGT anomaly: EGT critical with some corroboration (real thermal event)
    elif egt_level == "CRIT":
        fault = "EGT_ANOMALY"

    # Any single warn-level deviation
    elif warn_or_crit:
        # map the dominant channel to its fault type
        dominant = max(
            [("EGT", abs(d_egt) / TH["egt_crit"]),
             ("CHT", abs(d_cht) / TH["cht_crit"]),
             ("OIL_PRESS", abs(d_oilp) / TH["oil_press_crit"]),
             ("VIBRATION", abs(d_vib) / TH["vib_crit"])],
            key=lambda t: t[1],
        )[0]
        fault = {
            "EGT": "EGT_ANOMALY",
            "CHT": "CHT_OVERHEAT",
            "OIL_PRESS": "OIL_PRESSURE_LOW",
            "VIBRATION": "VIBRATION_ANOMALY",
        }[dominant]

    else:
        fault = "NORMAL"

    # ── severity (0..1): worst normalised residual ───────────────────────────
    sev_components = [
        abs(d_egt) / TH["egt_crit"],
        abs(d_cht) / TH["cht_crit"],
        abs(d_oilt) / TH["oil_temp_crit"],
        abs(d_oilp) / TH["oil_press_crit"],
        abs(d_vib) / TH["vib_crit"],
    ]
    severity = round(min(1.0, max(sev_components) if fault != "NORMAL" else min(0.15, max(sev_components))), 3)

    return {
        "fault_class": fault,
        "fault_label": FAULT_LABELS[fault],
        "severity": severity,
        "evidence": evidence,
        "active_channels": active,
    }
