"""
simulation/scenarios/definitions.py
===================================
Declarative definitions of the 9 demonstrator scenarios.

Each scenario describes how a healthy baseline telemetry frame is MUTATED to
produce a recognizable fault signature. Mutations are applied as functions of
severity (0..1) so the simulator can ramp faults in gradually.

DATA HONESTY: every scenario here is SYNTHETIC. These are engineering fault
signatures, not recordings of real engine failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict


@dataclass(frozen=True)
class ScenarioDef:
    key: str
    label: str
    description: str
    # mutate(frame, severity) -> mutated frame (in place dict ok)
    mutate: Callable[[Dict[str, float], float], None]
    # whether this scenario ramps severity over time (degradation)
    progressive: bool = False


# --- individual mutation functions --------------------------------------------

def _healthy(frame: Dict[str, float], sev: float) -> None:
    # No fault signature. Healthy baseline only.
    return


def _high_egt(frame: Dict[str, float], sev: float) -> None:
    # Lean mixture / ignition retard signature: EGT climbs, slight CHT rise,
    # fuel flow drops (leaner), mild vibration.
    frame["egt_avg_c"] += 70.0 * sev
    frame["cht_avg_c"] += 10.0 * sev
    frame["fuel_flow_lph"] -= 1.5 * sev
    frame["vibration_rms_g"] += 0.3 * sev


def _high_cht(frame: Dict[str, float], sev: float) -> None:
    # Cooling degradation: CHT climbs strongly, oil temp follows,
    # oil pressure sags as oil thins with heat.
    frame["cht_avg_c"] += 35.0 * sev
    frame["oil_temp_c"] += 25.0 * sev
    frame["oil_pressure_psi"] -= 6.0 * sev


def _low_oil_pressure(frame: Dict[str, float], sev: float) -> None:
    # Oil leak / pump wear: pressure drops hard, temp rises, vibration grows.
    frame["oil_pressure_psi"] -= 28.0 * sev
    frame["oil_temp_c"] += 18.0 * sev
    frame["vibration_rms_g"] += 0.5 * sev


def _high_vibration(frame: Dict[str, float], sev: float) -> None:
    # Misfire / mechanical imbalance: vibration spikes, EGT drops on dead
    # cylinder, CHT dips slightly.
    frame["vibration_rms_g"] += 4.0 * sev
    frame["egt_avg_c"] -= 60.0 * sev
    frame["cht_avg_c"] -= 12.0 * sev


def _turbo_boost(frame: Dict[str, float], sev: float) -> None:
    # Turbo/boost anomaly (wastegate stuck closed / over-boost):
    # MAP climbs above commanded, EGT + CHT climb, fuel flow rises.
    frame["map_kpa"] += 22.0 * sev
    frame["egt_avg_c"] += 45.0 * sev
    frame["cht_avg_c"] += 18.0 * sev
    frame["fuel_flow_lph"] += 2.5 * sev


def _sensor_drift(frame: Dict[str, float], sev: float) -> None:
    # Sensor drift: a slow bias on EGT sensor with no corroborating change in
    # CHT/oil/vibration (physics residual will flag EGT alone -> SENSOR class).
    frame["egt_avg_c"] += 55.0 * sev


def _combined_fault(frame: Dict[str, float], sev: float) -> None:
    # Multi-parameter fault: cooling + oil + vibration simultaneously.
    frame["cht_avg_c"] += 30.0 * sev
    frame["oil_temp_c"] += 20.0 * sev
    frame["oil_pressure_psi"] -= 20.0 * sev
    frame["vibration_rms_g"] += 2.5 * sev
    frame["egt_avg_c"] += 25.0 * sev


def _degrading(frame: Dict[str, float], sev: float) -> None:
    # Progressive degradation: everything drifts slowly worse with severity,
    # which the simulator ramps over time.
    frame["cht_avg_c"] += 25.0 * sev
    frame["egt_avg_c"] += 30.0 * sev
    frame["oil_pressure_psi"] -= 15.0 * sev
    frame["oil_temp_c"] += 15.0 * sev
    frame["vibration_rms_g"] += 1.5 * sev


# --- scenario registry --------------------------------------------------------

SCENARIO_DEFS: Dict[str, ScenarioDef] = {
    "HEALTHY": ScenarioDef(
        "HEALTHY", "Healthy",
        "Nominal engine operation within all expected envelopes.",
        _healthy,
    ),
    "HIGH_EGT": ScenarioDef(
        "HIGH_EGT", "High EGT",
        "Lean mixture / ignition-retard signature: EGT above baseline.",
        _high_egt,
    ),
    "HIGH_CHT": ScenarioDef(
        "HIGH_CHT", "High CHT",
        "Cooling degradation: cylinder-head temperature above baseline.",
        _high_cht,
    ),
    "LOW_OIL_PRESSURE": ScenarioDef(
        "LOW_OIL_PRESSURE", "Low Oil Pressure",
        "Oil leak / pump wear: oil pressure drops, oil temp rises.",
        _low_oil_pressure,
    ),
    "HIGH_VIBRATION": ScenarioDef(
        "HIGH_VIBRATION", "High Vibration",
        "Misfire / mechanical imbalance: vibration spike, EGT drop.",
        _high_vibration,
    ),
    "TURBO_BOOST": ScenarioDef(
        "TURBO_BOOST", "Turbo / Boost Anomaly",
        "Wastegate / over-boost: MAP above commanded, thermal rise.",
        _turbo_boost,
    ),
    "SENSOR_DRIFT": ScenarioDef(
        "SENSOR_DRIFT", "Sensor Drift",
        "EGT sensor bias with no corroborating physical change.",
        _sensor_drift,
    ),
    "COMBINED_FAULT": ScenarioDef(
        "COMBINED_FAULT", "Combined Fault",
        "Multiple simultaneous anomalies (cooling + oil + vibration).",
        _combined_fault,
    ),
    "DEGRADING": ScenarioDef(
        "DEGRADING", "Degrading Engine",
        "Progressive multi-parameter degradation ramping over time.",
        _degrading,
        progressive=True,
    ),
}
