"""Unit tests for anomaly, fault diagnosis, degradation, RUL and mission."""

from __future__ import annotations

from app.ml.anomaly import AnomalyDetector
from app.ml.fault_diagnosis import diagnose_fault
from app.ml.degradation import DegradationTracker
from app.ml.rul import RULEstimator
from app.ml.mission import assess_mission_reliability
from app.ml.advisory import decide_advisory
from app.ml.ai_provider import DeterministicExplanationProvider


def _zero_residuals():
    return {
        "delta_egt_c": 2.0,
        "delta_cht_c": 1.0,
        "delta_oil_temp_c": 0.5,
        "delta_oil_pressure_psi": -0.5,
        "delta_vibration_rms_g": 0.02,
    }


def _cht_fault():
    return {
        "delta_egt_c": 10.0,
        "delta_cht_c": 40.0,
        "delta_oil_temp_c": 2.0,
        "delta_oil_pressure_psi": -2.0,
        "delta_vibration_rms_g": 0.1,
    }


# ── anomaly ──────────────────────────────────────────────────────────────────
def test_anomaly_low_when_nominal():
    det = AnomalyDetector()
    out = det.score(_zero_residuals())
    assert out["anomaly_score"] < 40
    assert out["anomaly_status"] in ("NOMINAL", "WATCH")


def test_anomaly_has_contributing_features():
    det = AnomalyDetector()
    out = det.score(_cht_fault())
    assert len(out["contributing_features"]) == 5
    assert all("contribution" in c for c in out["contributing_features"])


# ── fault diagnosis (deterministic) ──────────────────────────────────────────
def test_fault_normal_when_within_scatter():
    f = diagnose_fault(_zero_residuals(), {"load_factor": 0.7, "map_kpa": 100})
    assert f["fault_class"] == "NORMAL"


def test_fault_cht_overheat():
    f = diagnose_fault(_cht_fault(), {"load_factor": 0.7, "map_kpa": 100})
    assert f["fault_class"] in ("CHT_OVERHEAT", "MULTI_PARAMETER_FAULT")
    assert f["severity"] > 0.5
    assert len(f["evidence"]) >= 1


def test_fault_oil_pressure_low():
    res = _zero_residuals()
    res["delta_oil_pressure_psi"] = -25.0
    f = diagnose_fault(res, {"load_factor": 0.7, "map_kpa": 100})
    assert f["fault_class"] in ("OIL_PRESSURE_LOW", "MULTI_PARAMETER_FAULT")


def test_fault_sensor_anomaly_egt_only():
    res = _zero_residuals()
    res["delta_egt_c"] = 70.0  # EGT alone, nothing else
    f = diagnose_fault(res, {"load_factor": 0.7, "map_kpa": 100})
    assert f["fault_class"] in ("SENSOR_ANOMALY", "EGT_ANOMALY")


# ── degradation ──────────────────────────────────────────────────────────────
def test_health_high_when_healthy():
    d = DegradationTracker()
    out = d.update(anomaly_score=10, fault_severity=0.05, residuals=_zero_residuals(), timestamp=1.0)
    assert out["health_index"] > 80


def test_health_decreases_under_fault():
    d = DegradationTracker()
    d.update(5, 0.0, _zero_residuals(), 1.0)
    healthy = d.current_health
    for t in range(2, 20):
        out = d.update(70, 0.9, _cht_fault(), float(t))
    assert out["health_index"] < healthy


# ── RUL ──────────────────────────────────────────────────────────────────────
def test_rul_insufficient_history():
    r = RULEstimator()
    out = r.update(1.0, 95.0)
    assert out["status"] == "INSUFFICIENT_HISTORY"
    assert out["rul_hours"] is None


def test_rul_stable_when_no_decay():
    r = RULEstimator()
    for t in range(1, 20):
        out = r.update(float(t), 90.0)  # flat health
    assert out["status"] in ("STABLE_NO_DECAY", "OK")
    if out["status"] == "STABLE_NO_DECAY":
        assert out["rul_hours"] is None


def test_rul_estimates_hours_when_degrading():
    r = RULEstimator()
    h = 95.0
    for t in range(1, 30):
        h -= 1.5  # steady decline
        out = r.update(float(t), max(h, 5.0))
    assert out["status"] == "OK"
    assert out["rul_hours"] is not None and out["rul_hours"] >= 0
    assert out["confidence_interval"] is not None
    # honesty: methodology mentions trend-based / synthetic
    assert "trend" in out["methodology"].lower()


# ── mission ──────────────────────────────────────────────────────────────────
def test_mission_healthy_high_probability():
    m = assess_mission_reliability(90, 20.0, 4.0, 0.6, 0.8, 3000, "STANDARD")
    assert m["completion_probability_pct"] > 60
    assert m["risk_level"] in ("LOW", "MODERATE")


def test_mission_degraded_low_probability():
    m = assess_mission_reliability(35, 1.0, 6.0, 0.9, 1.1, 6000, "HARSH")
    assert m["completion_probability_pct"] < 50
    assert m["risk_level"] in ("ELEVATED", "HIGH")
    assert m["limiting_factor"]


# ── advisory (deterministic) ─────────────────────────────────────────────────
def test_advisory_go_when_normal():
    fault = diagnose_fault(_zero_residuals(), {"load_factor": 0.7, "map_kpa": 100})
    anomaly = AnomalyDetector().score(_zero_residuals())
    adv = decide_advisory(fault, anomaly, 90.0, _zero_residuals())
    assert adv["state"] == "GO"
    assert adv["advisory_source"] == "deterministic_rule_engine"


def test_advisory_maintenance_on_critical():
    res = _zero_residuals()
    res["delta_oil_pressure_psi"] = -25.0
    fault = diagnose_fault(res, {"load_factor": 0.7, "map_kpa": 100})
    anomaly = AnomalyDetector().score(res)
    adv = decide_advisory(fault, anomaly, 40.0, res)
    assert adv["state"] in ("MAINTENANCE REQUIRED", "GO WITH DERATE")


# ── AI provider ──────────────────────────────────────────────────────────────
def test_deterministic_explainer_references_evidence():
    prov = DeterministicExplanationProvider()
    fault = diagnose_fault(_cht_fault(), {"load_factor": 0.9, "map_kpa": 110})
    anomaly = AnomalyDetector().score(_cht_fault())
    adv = decide_advisory(fault, anomaly, 55.0, _cht_fault())
    out = prov.explain({
        "fault": fault, "advisory": adv, "residuals": _cht_fault(),
        "anomaly": anomaly, "twin_state": {"load_factor": 0.9},
    })
    assert out["explanation_source"] == "deterministic"
    assert len(out["explanation"]) > 20
