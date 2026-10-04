"""
ml/advisory.py
==============
DETERMINISTIC maintenance advisory decision engine.

Four states:
    GO
    GO WITH MONITORING
    GO WITH DERATE
    MAINTENANCE REQUIRED

The decision is made ONLY from deterministic engineering inputs (fault class,
fault severity, residuals, anomaly, health). The AI explainer may describe
*why*, but it can NEVER change this state.

Returns a structured advisory:
    { state, severity, root_cause, evidence, recommended_action, advisory_source }
"""

from __future__ import annotations

from typing import Dict, List

# Oil-pressure loss and multi-parameter faults are the most safety-critical.
_CRITICAL_FAULTS = {"OIL_PRESSURE_LOW", "MULTI_PARAMETER_FAULT", "CHT_OVERHEAT"}


def decide_advisory(
    fault: Dict[str, object],
    anomaly: Dict[str, object],
    health_index: float,
    residuals: Dict[str, float],
) -> Dict[str, object]:
    fault_class = str(fault.get("fault_class", "NORMAL"))
    severity = float(fault.get("severity", 0.0))
    anomaly_status = str(anomaly.get("anomaly_status", "NOMINAL"))
    anomaly_score = float(anomaly.get("anomaly_score", 0.0))
    evidence = list(fault.get("evidence", []))

    d_oilp = float(residuals.get("delta_oil_pressure_psi", 0.0))
    d_cht = float(residuals.get("delta_cht_c", 0.0))

    # ── deterministic decision tree ──────────────────────────────────────────

    # 1. Critical safety faults -> MAINTENANCE REQUIRED
    if fault_class == "OIL_PRESSURE_LOW" and d_oilp < -16.0:
        state = "MAINTENANCE REQUIRED"
        action = "Land as soon as practical. Inspect oil system before next flight."
    elif fault_class == "MULTI_PARAMETER_FAULT":
        state = "MAINTENANCE REQUIRED"
        action = "Abort/return. Multiple subsystems out of tolerance — ground the engine."
    elif fault_class == "CHT_OVERHEAT" and d_cht > 28.0:
        state = "MAINTENANCE REQUIRED"
        action = "Reduce power immediately and land. Inspect cooling system."
    elif health_index < 35.0:
        state = "MAINTENANCE REQUIRED"
        action = "Engine health critically low. Ground for inspection."

    # 2. Significant single fault -> GO WITH DERATE
    elif fault_class in {"BOOST_TURBO_ANOMALY", "VIBRATION_ANOMALY", "EGT_ANOMALY"} and severity >= 0.7:
        state = "GO WITH DERATE"
        action = "Reduce power/boost. Continue only at reduced load and monitor closely."
    elif health_index < 55.0:
        state = "GO WITH DERATE"
        action = "Operate at reduced power. Plan maintenance at next opportunity."

    # 3. Minor anomaly -> GO WITH MONITORING
    elif anomaly_status in {"WATCH", "ANOMALY"} or fault_class != "NORMAL":
        state = "GO WITH MONITORING"
        action = "Continue mission. Monitor the flagged parameter(s) closely."

    # 4. Nominal
    else:
        state = "GO"
        action = "All parameters nominal. Continue normal operation."

    # severity label for UI
    if state == "MAINTENANCE REQUIRED":
        sev_label = "CRITICAL"
    elif state == "GO WITH DERATE":
        sev_label = "HIGH"
    elif state == "GO WITH MONITORING":
        sev_label = "MODERATE"
    else:
        sev_label = "NOMINAL"

    # root cause (deterministic, cites fault + top evidence)
    if evidence:
        top = evidence[0]
        root = (
            f"{fault.get('fault_label', fault_class)}: {top['channel']} residual "
            f"{top['value']:+} ({top['level']}, {top['direction']})."
        )
    elif fault_class == "NORMAL":
        root = "No fault signature detected; residuals within normal scatter."
    else:
        root = str(fault.get("fault_label", fault_class))

    return {
        "state": state,
        "severity": sev_label,
        "root_cause": root,
        "evidence": evidence,
        "recommended_action": action,
        "advisory_source": "deterministic_rule_engine",
    }
