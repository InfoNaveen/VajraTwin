"""Unit tests for the physics digital-twin surrogate."""

from __future__ import annotations

import math

from app.physics.engine import PhysicsEngine


def _cruise():
    return {
        "rpm": 5000,
        "map_kpa": 105,
        "oat_c": 15,
        "egt_avg_c": 700,
        "cht_avg_c": 110,
        "oil_temp_c": 90,
        "oil_pressure_psi": 65,
        "vibration_rms_g": 1.4,
        "dt_s": 1.0,
    }


def test_volumetric_efficiency_in_range():
    eng = PhysicsEngine()
    ve = eng.volumetric_efficiency(5000, 105_000)
    assert 0.55 <= ve <= 0.95


def test_volumetric_efficiency_zero_rpm():
    eng = PhysicsEngine()
    assert eng.volumetric_efficiency(0, 101_325) == 0.0


def test_mass_airflow_positive_under_load():
    eng = PhysicsEngine()
    t_in = eng.inlet_temperature_k(15, 105_000)
    ve = eng.volumetric_efficiency(5000, 105_000)
    m = eng.mass_airflow_kg_s(105_000, 5000, t_in, ve)
    assert m > 0


def test_inlet_temperature_rises_with_boost():
    eng = PhysicsEngine()
    t_amb = eng.inlet_temperature_k(15, 101_325)
    t_boost = eng.inlet_temperature_k(15, 140_000)
    assert t_boost > t_amb


def test_expected_parameters_present():
    eng = PhysicsEngine()
    exp = eng.calculate_expected_parameters(_cruise())
    for k in (
        "expected_egt_c",
        "expected_cht_c",
        "expected_oil_temp_c",
        "expected_oil_pressure_psi",
        "expected_vibration_rms_g",
    ):
        assert k in exp
        assert math.isfinite(exp[k])


def test_residuals_near_zero_when_actual_matches_expected():
    eng = PhysicsEngine()
    # first frame seeds thermal state from actuals -> residual ~0 for EGT/CHT
    exp = eng.calculate_expected_parameters(_cruise())
    res = eng.calculate_residuals(_cruise(), exp)
    assert abs(res["delta_egt_c"]) < 1.0
    assert abs(res["delta_cht_c"]) < 1.0


def test_residual_positive_when_egt_elevated():
    eng = PhysicsEngine()
    exp = eng.calculate_expected_parameters(_cruise())
    hot = _cruise()
    hot["egt_avg_c"] = exp["expected_egt_c"] + 80
    res = eng.calculate_residuals(hot, exp)
    assert res["delta_egt_c"] > 50


def test_bad_telemetry_does_not_crash():
    eng = PhysicsEngine()
    bad = {"rpm": float("nan"), "map_kpa": float("inf"), "egt_avg_c": None, "dt_s": 1.0}
    out = eng.analyse(bad)  # must not raise
    assert "residuals" in out and "expected" in out


def test_zero_rpm_clamped():
    eng = PhysicsEngine()
    state = eng.calculate_engine_state({"rpm": 0, "map_kpa": 50, "oat_c": 15})
    assert state["mass_airflow_kg_s"] == 0.0
    assert state["load_factor"] == 0.0


def test_health_features_shape():
    eng = PhysicsEngine()
    st = eng.calculate_engine_state(_cruise())
    feats = eng.calculate_health_features(_cruise(), st)
    assert {"delta_egt_c", "delta_cht_c", "load_factor"} <= set(feats)
