"""
VajraTwin health & analytics engine.

All safety-critical decisions (fault class, advisory state) are DETERMINISTIC.
The AI provider only generates human-readable explanations; it never decides
the health state.
"""

from app.ml.anomaly import AnomalyDetector
from app.ml.fault_diagnosis import diagnose_fault
from app.ml.degradation import DegradationTracker
from app.ml.rul import RULEstimator
from app.ml.mission import assess_mission_reliability
from app.ml.advisory import decide_advisory
from app.ml.ai_provider import get_ai_provider

__all__ = [
    "AnomalyDetector",
    "diagnose_fault",
    "DegradationTracker",
    "RULEstimator",
    "assess_mission_reliability",
    "decide_advisory",
    "get_ai_provider",
]
