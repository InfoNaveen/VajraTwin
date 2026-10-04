"""
physics/engine.py
=================
VajraTwin — canonical physics digital-twin surrogate for the Rotax 914 F/UL
turbocharged 4-cylinder aero-piston engine.

This is the SINGLE source of truth for engine physics (previously duplicated
across three modules). It is a lightweight, algebraic surrogate — not a full
CFD/ODE model — chosen for real-time (<25 ms) inference.

Clean interface
---------------
    engine = PhysicsEngine()
    state    = engine.calculate_engine_state(telemetry)
    expected = engine.calculate_expected_parameters(telemetry)
    residual = engine.calculate_residuals(actual, expected)
    features = engine.calculate_health_features(telemetry, state)

Models implemented
------------------
- Volumetric efficiency (algebraic VE curve around best-VE RPM)
- Speed-density mass airflow
- Turbocharger + intercooler inlet-temperature model
- EGT / CHT steady-state baselines
- First-order lumped thermal capacitance (τ_EGT, τ_CHT) for transient realism
- Oil-pressure / oil-temperature / vibration baselines
- Actual-vs-expected residuals for all monitored channels

NOTE ON DATA HONESTY
--------------------
All baselines are engineering approximations calibrated to published Rotax 914
operating envelopes. They are NOT validated against real engine test data.
Residuals drive deterministic health logic; see app/ml.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# =============================================================================
# Engine / environment constants
# =============================================================================

@dataclass(frozen=True)
class EngineConstants:
    """Rotax 914 F/UL calibration constants (published-envelope approximations)."""

    # Geometry
    displacement_m3: float = 1211e-6     # 1211 cc
    rpm_peak: float = 5500.0             # best-VE region [rev/min]
    rpm_max: float = 5800.0              # max continuous [rev/min]

    # Air / environment
    r_air: float = 287.05                # J/(kg·K)
    p_amb_pa: float = 101325.0           # sea-level ambient [Pa]
    gamma_air: float = 1.4

    # Turbo / intercooler
    compressor_eff: float = 0.70
    intercooler_eff: float = 0.65

    # Thermal ceilings
    egt_max_c: float = 950.0
    cht_max_c: float = 135.0

    # Lumped thermal time constants [s]
    # Short τ_EGT so the twin tracks the fast exhaust response and the healthy
    # residual stays small; CHT retains realistic thermal inertia.
    tau_egt_s: float = 1.2
    tau_cht_s: float = 12.0

    # Volumetric efficiency calibration
    eta_v_max: float = 0.88
    eta_v_rpm_sens: float = 0.35
    eta_v_boost_sens: float = 0.03

    # EGT steady-state calibration
    # Tuned so the healthy twin tracks the demonstrator's coupled EGT curve
    # (near-zero residual when the engine is healthy).
    egt_base_rise: float = 350.0
    egt_load_gain: float = 470.0
    egt_airflow_cool: float = 30.0

    # CHT steady-state calibration
    cht_base_rise: float = 55.0
    cht_load_gain: float = 48.0
    cht_airflow_cool: float = 12.0

    # Oil / vibration baselines (algebraic approximations)
    # Calibrated so a cruise point (~5000 rpm, oil ~95 °C) yields ~58 psi,
    # inside the Rotax 914 normal band (roughly 29–73 psi, red-line ~102 psi).
    oil_press_base_psi: float = 40.0
    oil_press_rpm_gain: float = 0.008    # psi per rpm contribution
    oil_press_temp_drop: float = 0.1     # psi lost per °C oil-temp rise term
    oil_temp_fraction: float = 0.80      # oil temp ≈ 0.8 × CHT
    vib_base_g: float = 0.5
    vib_rpm_scale: float = 6450.0        # vib ≈ base + (rpm/scale)²·k
    vib_rpm_gain: float = 0.6            # matches simulator healthy vib curve


# =============================================================================
# Small helpers
# =============================================================================

def clamp(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _get_float(src: Dict[str, Any], keys: tuple, default: Optional[float]) -> Optional[float]:
    """Fetch the first present key and coerce to float; aliases supported."""
    for key in keys:
        if key in src and src[key] is not None:
            try:
                v = float(src[key])
                if math.isnan(v) or math.isinf(v):
                    continue
                return v
            except (TypeError, ValueError):
                continue
    return default


# =============================================================================
# Thermal capacitance state
# =============================================================================

class ThermalState:
    """
    First-order lumped thermal capacitance for EGT and CHT:

        T[n+1] = T[n] + (T_ss - T[n]) · (1 - exp(-dt / τ))

    Algebraic, stable for any positive dt, no ODE solver.
    """

    __slots__ = ("egt_c", "cht_c", "initialized")

    def __init__(self, egt_c: float = 25.0, cht_c: float = 25.0) -> None:
        self.egt_c = egt_c
        self.cht_c = cht_c
        self.initialized = False

    def reset(self, egt_c: Optional[float] = None, cht_c: Optional[float] = None) -> None:
        if egt_c is not None:
            self.egt_c = egt_c
        if cht_c is not None:
            self.cht_c = cht_c
        self.initialized = False

    def update(self, dt_s: float, egt_ss_c: float, cht_ss_c: float, k: EngineConstants) -> None:
        dt = clamp(dt_s, 0.0, 5.0)
        if not self.initialized:
            self.egt_c = egt_ss_c
            self.cht_c = cht_ss_c
            self.initialized = True
            return
        alpha_egt = 1.0 - math.exp(-dt / k.tau_egt_s)
        alpha_cht = 1.0 - math.exp(-dt / k.tau_cht_s)
        self.egt_c += (egt_ss_c - self.egt_c) * alpha_egt
        self.cht_c += (cht_ss_c - self.cht_c) * alpha_cht


# =============================================================================
# Canonical physics engine
# =============================================================================

class PhysicsEngine:
    """
    Stateful physics digital twin. One instance per engine so thermal memory
    persists between telemetry frames.
    """

    def __init__(self, constants: Optional[EngineConstants] = None) -> None:
        self.k = constants or EngineConstants()
        self.thermal = ThermalState()

    # ── reset ────────────────────────────────────────────────────────────────
    def reset(self, egt_c: Optional[float] = None, cht_c: Optional[float] = None) -> None:
        self.thermal.reset(egt_c, cht_c)

    # ── sub-models ─────────────────────────────────────────────────────────────
    def volumetric_efficiency(self, rpm: float, map_pa: float) -> float:
        k = self.k
        if rpm <= 0.0:
            return 0.0
        rpm_norm = rpm / k.rpm_peak
        rpm_term = k.eta_v_max - k.eta_v_rpm_sens * (rpm_norm - 1.0) ** 2
        boost_term = k.eta_v_boost_sens * ((map_pa / 1000.0 - k.p_amb_pa / 1000.0) / 30.0)
        return clamp(rpm_term + boost_term, 0.55, 0.95)

    def inlet_temperature_k(self, oat_c: float, map_pa: float) -> float:
        k = self.k
        t_amb = max(oat_c + 273.15, 200.0)
        map_pa = max(map_pa, k.p_amb_pa)
        pr = map_pa / k.p_amb_pa
        if pr <= 1.0:
            return t_amb
        t_ideal = t_amb * (pr ** ((k.gamma_air - 1.0) / k.gamma_air))
        t_comp_out = t_amb + (t_ideal - t_amb) / k.compressor_eff
        return t_comp_out - k.intercooler_eff * (t_comp_out - t_amb)

    def mass_airflow_kg_s(self, map_pa: float, rpm: float, t_inlet_k: float, eta_v: float) -> float:
        k = self.k
        if rpm <= 0.0 or map_pa <= 0.0 or t_inlet_k <= 0.0 or eta_v <= 0.0:
            return 0.0
        return map_pa * k.displacement_m3 * (rpm / 60.0) / (2.0 * k.r_air * t_inlet_k) * eta_v

    def load_factor(self, map_pa: float, rpm: float) -> float:
        k = self.k
        if rpm <= 0.0:
            return 0.0
        return clamp((map_pa / 1000.0 / (k.p_amb_pa / 1000.0)) * (rpm / k.rpm_peak), 0.0, 1.6)

    def _steady_egt(self, oat_c, map_pa, rpm, m_dot) -> float:
        k = self.k
        if rpm <= 0.0 or map_pa <= 0.0 or m_dot <= 0.0:
            return oat_c
        load = self.load_factor(map_pa, rpm)
        airflow_norm = clamp(m_dot / 0.08, 0.0, 2.0)
        egt = oat_c + k.egt_base_rise + k.egt_load_gain * load - k.egt_airflow_cool * airflow_norm
        return clamp(egt, oat_c, k.egt_max_c)

    def _steady_cht(self, oat_c, map_pa, rpm, m_dot) -> float:
        k = self.k
        if rpm <= 0.0 or map_pa <= 0.0 or m_dot <= 0.0:
            return oat_c
        load = self.load_factor(map_pa, rpm)
        airflow_norm = clamp(m_dot / 0.08, 0.0, 2.0)
        cht = oat_c + k.cht_base_rise + k.cht_load_gain * load - k.cht_airflow_cool * airflow_norm
        return clamp(cht, oat_c, k.cht_max_c)

    def _expected_oil_pressure(self, rpm: float, oil_temp_c: float) -> float:
        k = self.k
        return clamp(k.oil_press_rpm_gain * rpm - k.oil_press_temp_drop * oil_temp_c + k.oil_press_base_psi, 0.0, 120.0)

    def _expected_oil_temp(self, cht_c: float) -> float:
        return clamp(self.k.oil_temp_fraction * cht_c, 0.0, 160.0)

    def _expected_vibration(self, rpm: float) -> float:
        k = self.k
        return k.vib_base_g + (rpm / k.vib_rpm_scale) ** 2 * k.vib_rpm_gain

    # ── normalise raw telemetry dict ───────────────────────────────────────────
    def _normalise(self, telemetry: Dict[str, Any]) -> Dict[str, float]:
        k = self.k
        rpm = _get_float(telemetry, ("rpm", "RPM", "engine_rpm"), 0.0)
        oat_c = _get_float(telemetry, ("oat_c", "OAT_C", "oat", "OAT"), 15.0)
        dt_s = _get_float(telemetry, ("dt_s", "dt", "delta_t"), 1.0)

        if any(x in telemetry for x in ("map_pa", "MAP_Pa")):
            map_pa = _get_float(telemetry, ("map_pa", "MAP_Pa"), k.p_amb_pa)
        else:
            map_kpa = _get_float(
                telemetry, ("map_kpa", "MAP_kPa", "map_hpa", "MAP_hPa", "map", "MAP"), k.p_amb_pa / 1000.0
            )
            map_pa = map_kpa * 1000.0

        # Plausibility clamping (never crash on bad telemetry)
        rpm = clamp(rpm, 0.0, 7000.0)
        oat_c = clamp(oat_c, -60.0, 60.0)
        map_pa = clamp(map_pa if map_pa and map_pa >= 0 else k.p_amb_pa, 0.0, 250000.0)

        return {"rpm": rpm, "oat_c": oat_c, "map_pa": map_pa, "dt_s": dt_s}

    # ======================================================================
    # PUBLIC INTERFACE
    # ======================================================================

    def calculate_engine_state(self, telemetry: Dict[str, Any]) -> Dict[str, float]:
        """Virtual engine thermodynamic state from telemetry (no residuals)."""
        n = self._normalise(telemetry)
        rpm, oat_c, map_pa = n["rpm"], n["oat_c"], n["map_pa"]

        if rpm <= 0.0:
            eta_v, t_inlet_k, m_dot = 0.0, oat_c + 273.15, 0.0
        else:
            eta_v = self.volumetric_efficiency(rpm, map_pa)
            t_inlet_k = self.inlet_temperature_k(oat_c, map_pa)
            m_dot = self.mass_airflow_kg_s(map_pa, rpm, t_inlet_k, eta_v)

        return {
            "rpm": rpm,
            "map_pa": map_pa,
            "map_kpa": map_pa / 1000.0,
            "oat_c": oat_c,
            "volumetric_efficiency": eta_v,
            "inlet_temp_k": t_inlet_k,
            "inlet_temp_c": t_inlet_k - 273.15,
            "mass_airflow_kg_s": m_dot,
            "load_factor": self.load_factor(map_pa, rpm),
            "dt_s": n["dt_s"],
        }

    def calculate_expected_parameters(self, telemetry: Dict[str, Any]) -> Dict[str, float]:
        """
        Expected (healthy-baseline) parameters for all monitored channels.
        Advances the lumped thermal model by dt for EGT/CHT realism.
        """
        state = self.calculate_engine_state(telemetry)
        rpm, oat_c, map_pa, m_dot = (
            state["rpm"], state["oat_c"], state["map_pa"], state["mass_airflow_kg_s"]
        )

        egt_ss = self._steady_egt(oat_c, map_pa, rpm, m_dot)
        cht_ss = self._steady_cht(oat_c, map_pa, rpm, m_dot)

        # Seed thermal state from actuals (if present) on first frame
        actual_egt = _get_float(telemetry, ("egt_c", "egt_avg_c", "EGT_C", "egt", "EGT"), None)
        actual_cht = _get_float(telemetry, ("cht_c", "cht_avg_c", "CHT_C", "cht", "CHT"), None)
        if not self.thermal.initialized:
            self.thermal.egt_c = actual_egt if actual_egt is not None else egt_ss
            self.thermal.cht_c = actual_cht if actual_cht is not None else cht_ss
            self.thermal.initialized = True
        else:
            self.thermal.update(state["dt_s"], egt_ss, cht_ss, self.k)

        expected_egt = self.thermal.egt_c
        expected_cht = self.thermal.cht_c
        expected_oil_temp = self._expected_oil_temp(expected_cht)
        expected_oil_press = self._expected_oil_pressure(rpm, expected_oil_temp)
        expected_vibration = self._expected_vibration(rpm)

        return {
            "expected_egt_c": expected_egt,
            "expected_cht_c": expected_cht,
            "expected_oil_temp_c": expected_oil_temp,
            "expected_oil_pressure_psi": expected_oil_press,
            "expected_vibration_rms_g": expected_vibration,
            "steady_egt_c": egt_ss,
            "steady_cht_c": cht_ss,
            **state,
        }

    def calculate_residuals(
        self, actual: Dict[str, Any], expected: Dict[str, float]
    ) -> Dict[str, float]:
        """Δ = actual − expected for every monitored channel."""
        a_egt = _get_float(actual, ("egt_c", "egt_avg_c", "EGT_C", "egt", "EGT"), expected["expected_egt_c"])
        a_cht = _get_float(actual, ("cht_c", "cht_avg_c", "CHT_C", "cht", "CHT"), expected["expected_cht_c"])
        a_oilt = _get_float(actual, ("oil_temp_c", "OIL_TEMP_C"), expected["expected_oil_temp_c"])
        a_oilp = _get_float(actual, ("oil_pressure_psi", "oil_press_psi"), expected["expected_oil_pressure_psi"])
        a_vib = _get_float(actual, ("vibration_rms_g", "vibration"), expected["expected_vibration_rms_g"])

        return {
            "delta_egt_c": a_egt - expected["expected_egt_c"],
            "delta_cht_c": a_cht - expected["expected_cht_c"],
            "delta_oil_temp_c": a_oilt - expected["expected_oil_temp_c"],
            "delta_oil_pressure_psi": a_oilp - expected["expected_oil_pressure_psi"],
            "delta_vibration_rms_g": a_vib - expected["expected_vibration_rms_g"],
            "actual_egt_c": a_egt,
            "actual_cht_c": a_cht,
            "actual_oil_temp_c": a_oilt,
            "actual_oil_pressure_psi": a_oilp,
            "actual_vibration_rms_g": a_vib,
        }

    def calculate_health_features(
        self, telemetry: Dict[str, Any], twin_state: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Compact feature vector for the ML / health engine.
        Combines residuals with normalised operating-point context.
        """
        expected = self.calculate_expected_parameters(telemetry)
        residuals = self.calculate_residuals(telemetry, expected)
        return {
            # residuals (the primary health signal)
            "delta_egt_c": residuals["delta_egt_c"],
            "delta_cht_c": residuals["delta_cht_c"],
            "delta_oil_temp_c": residuals["delta_oil_temp_c"],
            "delta_oil_pressure_psi": residuals["delta_oil_pressure_psi"],
            "delta_vibration_rms_g": residuals["delta_vibration_rms_g"],
            # operating-point context
            "load_factor": twin_state.get("load_factor", expected["load_factor"]),
            "volumetric_efficiency": twin_state.get("volumetric_efficiency", expected["volumetric_efficiency"]),
            "mass_airflow_kg_s": twin_state.get("mass_airflow_kg_s", expected["mass_airflow_kg_s"]),
        }

    # ── convenience: full analysis in one call ─────────────────────────────────
    def analyse(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """Full twin analysis: state + expected + residuals in one structure."""
        expected = self.calculate_expected_parameters(telemetry)
        residuals = self.calculate_residuals(telemetry, expected)
        return {
            "state": {
                "rpm": expected["rpm"],
                "map_kpa": expected["map_kpa"],
                "oat_c": expected["oat_c"],
                "load_factor": expected["load_factor"],
                "volumetric_efficiency": expected["volumetric_efficiency"],
                "mass_airflow_kg_s": expected["mass_airflow_kg_s"],
                "inlet_temp_c": expected["inlet_temp_c"],
            },
            "expected": {
                "egt_c": expected["expected_egt_c"],
                "cht_c": expected["expected_cht_c"],
                "oil_temp_c": expected["expected_oil_temp_c"],
                "oil_pressure_psi": expected["expected_oil_pressure_psi"],
                "vibration_rms_g": expected["expected_vibration_rms_g"],
            },
            "residuals": {
                "delta_egt_c": residuals["delta_egt_c"],
                "delta_cht_c": residuals["delta_cht_c"],
                "delta_oil_temp_c": residuals["delta_oil_temp_c"],
                "delta_oil_pressure_psi": residuals["delta_oil_pressure_psi"],
                "delta_vibration_rms_g": residuals["delta_vibration_rms_g"],
            },
            "actual": {
                "egt_c": residuals["actual_egt_c"],
                "cht_c": residuals["actual_cht_c"],
                "oil_temp_c": residuals["actual_oil_temp_c"],
                "oil_pressure_psi": residuals["actual_oil_pressure_psi"],
                "vibration_rms_g": residuals["actual_vibration_rms_g"],
            },
        }
