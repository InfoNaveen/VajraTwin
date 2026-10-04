"""
services/engine_service.py
=========================
The closed-loop orchestration service. Owns one PhysicsEngine + ML stack +
simulator per engine, runs the full analysis pipeline for a telemetry frame,
and persists results.

Pipeline (per frame)
--------------------
    telemetry
      -> physics.calculate_expected_parameters
      -> physics.calculate_residuals
      -> anomaly.score
      -> diagnose_fault            (deterministic)
      -> degradation.update        (health index 0..100)
      -> rul.update                (trend-based RUL)
      -> decide_advisory           (deterministic GO/MONITOR/DERATE/MAINTAIN)
      -> ai.explain                (explanation only; never decides)
      -> persist telemetry + health + fault/maintenance events

This service is deliberately framework-agnostic: FastAPI routes call it, but it
has no FastAPI imports.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.physics.engine import PhysicsEngine
from app.simulation.simulator import TelemetrySimulator
from app.ml.anomaly import AnomalyDetector
from app.ml.fault_diagnosis import diagnose_fault
from app.ml.degradation import DegradationTracker
from app.ml.rul import RULEstimator
from app.ml.mission import assess_mission_reliability
from app.ml.advisory import decide_advisory
from app.ml.ai_provider import get_ai_provider
from app.database.mongo import get_database

logger = get_logger("vajra.service")


class EngineService:
    def __init__(self, engine_id: str) -> None:
        self.engine_id = engine_id
        self.physics = PhysicsEngine()
        self.anomaly = AnomalyDetector()
        self.degradation = DegradationTracker()
        self.rul = RULEstimator()
        self.simulator = TelemetrySimulator(engine_id=engine_id)
        self.ai = get_ai_provider()
        self.db = get_database()

        self._last_analysis: Optional[Dict[str, Any]] = None
        self._last_advisory_state: Optional[str] = None

    # ── full-reset (used by simulation reset) ──────────────────────────────────
    def reset(self) -> None:
        self.physics.reset()
        self.anomaly.reset()
        self.degradation.reset()
        self.rul.reset()
        self.simulator.reset()
        self._last_analysis = None
        self._last_advisory_state = None

    # ── core pipeline ──────────────────────────────────────────────────────────
    async def analyse_frame(self, telemetry: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
        sim_time = float(telemetry.get("sim_time_s") or telemetry.get("timestamp") or time.time())

        expected = self.physics.calculate_expected_parameters(telemetry)
        residuals = self.physics.calculate_residuals(telemetry, expected)
        twin_state = {
            "rpm": expected["rpm"],
            "map_kpa": expected["map_kpa"],
            "oat_c": expected["oat_c"],
            "load_factor": expected["load_factor"],
            "volumetric_efficiency": expected["volumetric_efficiency"],
            "mass_airflow_kg_s": expected["mass_airflow_kg_s"],
            "inlet_temp_c": expected["inlet_temp_c"],
        }

        anomaly = self.anomaly.score(residuals)
        fault = diagnose_fault(residuals, twin_state)
        degradation = self.degradation.update(
            anomaly["anomaly_score"], float(fault["severity"]), residuals, sim_time
        )
        rul = self.rul.update(sim_time, degradation["health_index"])
        advisory = decide_advisory(fault, anomaly, degradation["health_index"], residuals)
        explanation = self.ai.explain({
            "fault": fault, "advisory": advisory, "residuals": residuals,
            "anomaly": anomaly, "twin_state": twin_state,
        })

        analysis: Dict[str, Any] = {
            "engine_id": self.engine_id,
            "sim_time_s": round(sim_time, 3),
            "tick": int(telemetry.get("tick", 0)),
            "data_label": telemetry.get("data_label", "SYNTHETIC"),
            "telemetry": {
                "rpm": telemetry.get("rpm"),
                "map_kpa": telemetry.get("map_kpa"),
                "oat_c": telemetry.get("oat_c"),
                "egt_avg_c": telemetry.get("egt_avg_c"),
                "cht_avg_c": telemetry.get("cht_avg_c"),
                "oil_temp_c": telemetry.get("oil_temp_c"),
                "oil_pressure_psi": telemetry.get("oil_pressure_psi"),
                "fuel_flow_lph": telemetry.get("fuel_flow_lph"),
                "vibration_rms_g": telemetry.get("vibration_rms_g"),
                "throttle_pct": telemetry.get("throttle_pct"),
                "altitude_m": telemetry.get("altitude_m"),
                "mission_phase": telemetry.get("mission_phase"),
            },
            "twin_state": {k: round(v, 4) if isinstance(v, float) else v for k, v in twin_state.items()},
            "expected": {
                "egt_c": round(expected["expected_egt_c"], 2),
                "cht_c": round(expected["expected_cht_c"], 2),
                "oil_temp_c": round(expected["expected_oil_temp_c"], 2),
                "oil_pressure_psi": round(expected["expected_oil_pressure_psi"], 2),
                "vibration_rms_g": round(expected["expected_vibration_rms_g"], 3),
            },
            "residuals": {k: round(v, 3) for k, v in residuals.items() if k.startswith("delta_")},
            "anomaly": anomaly,
            "fault": fault,
            "degradation": degradation,
            "rul": rul,
            "advisory": advisory,
            "explanation": explanation,
        }
        self._last_analysis = analysis

        if persist:
            await self._persist(analysis)

        return analysis

    async def _persist(self, analysis: Dict[str, Any]) -> None:
        try:
            await self.db.insert("telemetry", {
                "engine_id": self.engine_id,
                "sim_time_s": analysis["sim_time_s"],
                "tick": analysis["tick"],
                **analysis["telemetry"],
                **{f"res_{k}": v for k, v in analysis["residuals"].items()},
            })
            await self.db.insert("health_states", {
                "engine_id": self.engine_id,
                "sim_time_s": analysis["sim_time_s"],
                "health_index": analysis["degradation"]["health_index"],
                "anomaly_score": analysis["anomaly"]["anomaly_score"],
                "fault_class": analysis["fault"]["fault_class"],
                "advisory": analysis["advisory"]["state"],
            })
            # fault / maintenance events on advisory transition
            state = analysis["advisory"]["state"]
            if state != self._last_advisory_state:
                self._last_advisory_state = state
                if state != "GO":
                    await self.db.insert("maintenance_events", {
                        "engine_id": self.engine_id,
                        "sim_time_s": analysis["sim_time_s"],
                        "advisory": state,
                        "fault_class": analysis["fault"]["fault_class"],
                        "root_cause": analysis["advisory"]["root_cause"],
                    })
                if analysis["fault"]["fault_class"] != "NORMAL":
                    await self.db.insert("fault_events", {
                        "engine_id": self.engine_id,
                        "sim_time_s": analysis["sim_time_s"],
                        "fault_class": analysis["fault"]["fault_class"],
                        "severity": analysis["fault"]["severity"],
                    })
        except Exception as exc:  # noqa: BLE001 — persistence must never break analysis
            logger.warning("Persistence skipped (%s)", exc)

    # ── simulation driver ──────────────────────────────────────────────────────
    async def simulate_tick(self, real_dt_s: float = 1.0, persist: bool = True) -> Dict[str, Any]:
        frame = self.simulator.tick(real_dt_s)
        return await self.analyse_frame(frame, persist=persist)

    # ── mission analysis ───────────────────────────────────────────────────────
    async def analyse_mission(self, req: Dict[str, Any]) -> Dict[str, Any]:
        health = self.degradation.current_health
        rul_est = self.rul.estimate()
        rul_hours = rul_est.get("rul_hours")
        result = assess_mission_reliability(
            health_index=health,
            rul_hours=rul_hours,
            mission_duration_hours=float(req.get("mission_duration_hours", 4.0)),
            cruise_load=float(req.get("cruise_load", 0.65)),
            max_load=float(req.get("max_load", 0.9)),
            altitude_m=float(req.get("altitude_m", 4500.0)),
            environment=str(req.get("environment", "STANDARD")),
        )
        mission_id = f"m-{uuid.uuid4().hex[:8]}"
        doc = {
            "mission_id": mission_id,
            "engine_id": self.engine_id,
            "request": req,
            "health_index_used": round(health, 1),
            "rul_hours_used": rul_hours,
            **result,
        }
        try:
            await self.db.insert("missions", doc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Mission persistence skipped (%s)", exc)
        doc["mission_id"] = mission_id
        return doc

    # ── accessors ──────────────────────────────────────────────────────────────
    def last_analysis(self) -> Optional[Dict[str, Any]]:
        return self._last_analysis

    def health_history(self) -> List[Dict[str, float]]:
        return self.degradation.health_history()

    def simulation_status(self) -> Dict[str, Any]:
        return self.simulator.state.public()


# ── registry: one service per engine_id ──────────────────────────────────────
_SERVICES: Dict[str, EngineService] = {}


def get_engine_service(engine_id: Optional[str] = None) -> EngineService:
    eid = engine_id or settings.DEFAULT_ENGINE_ID
    if eid not in _SERVICES:
        _SERVICES[eid] = EngineService(eid)
    return _SERVICES[eid]
