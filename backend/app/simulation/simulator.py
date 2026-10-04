"""
simulation/simulator.py
=======================
Physically-coupled synthetic telemetry simulator for the VajraTwin demo.

Design principles
-----------------
1. Parameters are NOT independent random values. A single latent "load demand"
   drives RPM, MAP, fuel flow, EGT, CHT, oil temp and vibration together, so
   the stream is physically plausible.
2. A smooth random walk on load demand (plus a slow mission-phase profile)
   produces realistic drift; small Gaussian jitter simulates sensor noise.
3. Faults are applied on top of the healthy baseline via scenario mutations,
   producing recognizable signatures (see scenarios/definitions.py).

Controls: start / stop / pause / reset / set_scenario / set_speed /
set_fault_severity.

DATA HONESTY: all output is SYNTHETIC TELEMETRY.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from app.simulation.scenarios import SCENARIO_DEFS
from app.core.logging_config import get_logger

logger = get_logger("vajra.simulator")

SCENARIOS = list(SCENARIO_DEFS.keys())

# Mission phases cycle to give the demo visual variety and realistic load.
MISSION_PHASES = ["TAXI", "TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT"]

# Phase → target load demand (0..1.2) the engine is commanded to produce.
PHASE_LOAD = {
    "TAXI": 0.18,
    "TAKEOFF": 1.05,
    "CLIMB": 0.92,
    "CRUISE": 0.68,
    "LOITER": 0.55,
    "DESCENT": 0.35,
}


@dataclass
class SimulatorState:
    running: bool = False
    paused: bool = False
    scenario: str = "HEALTHY"
    fault_severity: float = 0.0        # 0..1
    speed: float = 1.0                 # simulation speed multiplier
    tick: int = 0
    sim_time_s: float = 0.0
    mission_phase: str = "CRUISE"
    engine_id: str = "rotax-914-uav-01"

    def public(self) -> Dict[str, Any]:
        d = asdict(self)
        d["available_scenarios"] = [
            {"key": k, "label": v.label, "description": v.description}
            for k, v in SCENARIO_DEFS.items()
        ]
        return d


class TelemetrySimulator:
    """
    Stateful simulator. One instance per demo session.
    Call `tick()` to advance one frame and return a telemetry dict.
    """

    def __init__(self, engine_id: str = "rotax-914-uav-01", seed: Optional[int] = 42) -> None:
        self._rng = random.Random(seed)
        self.state = SimulatorState(engine_id=engine_id)
        # latent dynamic variables
        self._load = 0.65           # smoothed load demand
        self._phase_idx = 3         # start in CRUISE
        self._phase_timer = 0.0
        # progressive-degradation accumulator (for DEGRADING scenario)
        self._degradation = 0.0

    # ── controls ───────────────────────────────────────────────────────────────
    def start(self) -> None:
        self.state.running = True
        self.state.paused = False
        logger.info("Simulator START (scenario=%s)", self.state.scenario)

    def stop(self) -> None:
        self.state.running = False
        self.state.paused = False
        logger.info("Simulator STOP")

    def pause(self) -> None:
        if self.state.running:
            self.state.paused = True
            logger.info("Simulator PAUSE")

    def resume(self) -> None:
        if self.state.running:
            self.state.paused = False
            logger.info("Simulator RESUME")

    def reset(self) -> None:
        eid = self.state.engine_id
        self.state = SimulatorState(engine_id=eid)
        self._load = 0.65
        self._phase_idx = 3
        self._phase_timer = 0.0
        self._degradation = 0.0
        self._rng = random.Random(42)
        logger.info("Simulator RESET")

    def set_scenario(self, scenario: str) -> None:
        scenario = scenario.upper()
        if scenario not in SCENARIO_DEFS:
            raise ValueError(f"Unknown scenario '{scenario}'. Valid: {SCENARIOS}")
        self.state.scenario = scenario
        if scenario == "HEALTHY":
            self.state.fault_severity = 0.0
        elif self.state.fault_severity == 0.0:
            # auto-arm a sensible severity when selecting a fault
            self.state.fault_severity = 0.8
        self._degradation = 0.0
        logger.info("Simulator scenario=%s severity=%.2f", scenario, self.state.fault_severity)

    def set_fault_severity(self, severity: float) -> None:
        self.state.fault_severity = max(0.0, min(1.0, float(severity)))

    def set_speed(self, speed: float) -> None:
        self.state.speed = max(0.25, min(10.0, float(speed)))

    # ── baseline physics-coupled frame ─────────────────────────────────────────
    def _advance_mission(self, dt: float) -> None:
        self._phase_timer += dt
        # change phase roughly every 20 sim-seconds for demo variety
        if self._phase_timer >= 20.0:
            self._phase_timer = 0.0
            self._phase_idx = (self._phase_idx + 1) % len(MISSION_PHASES)
        self.state.mission_phase = MISSION_PHASES[self._phase_idx]

    def _healthy_frame(self, dt: float) -> Dict[str, float]:
        # Smoothly chase the phase's target load with a little random walk.
        target = PHASE_LOAD[self.state.mission_phase]
        self._load += (target - self._load) * min(1.0, dt * 0.15)
        self._load += self._rng.uniform(-0.01, 0.01)
        load = max(0.1, min(1.15, self._load))

        # Derive coupled parameters from load (single latent driver).
        rpm = 1800.0 + load * 3700.0                     # idle→max
        map_kpa = 45.0 + load * 70.0                     # 45..115 kPa
        oat_c = 15.0 + 3.0 * math.sin(self.state.sim_time_s / 60.0)
        # altitude loosely tracks climb/descent phases
        altitude_m = {
            "TAXI": 0, "TAKEOFF": 50, "CLIMB": 1800,
            "CRUISE": 4500, "LOITER": 4200, "DESCENT": 1200,
        }[self.state.mission_phase]
        throttle_pct = 100.0 * min(1.0, load / 1.05)

        # Thermo/mechanical responses to load (healthy relationships).
        egt = 430.0 + load * 390.0                       # ~470..880 °C
        cht = 70.0 + load * 55.0                          # ~75..135 °C
        oil_temp = 50.0 + load * 55.0                     # ~55..110 °C
        oil_press = 72.0 - load * 10.0                    # drops slightly w/ heat/load
        fuel_flow = 4.0 + load * 20.0                     # L/h
        vibration = 0.5 + (rpm / 5000.0) ** 2 * 0.6       # grows with rpm

        # Sensor jitter
        jit = self._rng.gauss
        frame = {
            "rpm": rpm + jit(0, 15),
            "map_kpa": map_kpa + jit(0, 0.6),
            "oat_c": oat_c + jit(0, 0.2),
            "egt_avg_c": egt + jit(0, 2.5),
            "cht_avg_c": cht + jit(0, 1.2),
            "oil_temp_c": oil_temp + jit(0, 1.0),
            "oil_pressure_psi": oil_press + jit(0, 0.4),
            "fuel_flow_lph": fuel_flow + jit(0, 0.2),
            "vibration_rms_g": vibration + jit(0, 0.03),
            "throttle_pct": throttle_pct,
            "altitude_m": float(altitude_m),
        }
        return frame

    # ── main tick ────────────────────────────────────────────────────────────
    def tick(self, real_dt_s: float = 1.0) -> Dict[str, Any]:
        """
        Advance one simulation frame. `real_dt_s` is wall-clock dt; the sim
        advances by real_dt_s * speed.
        """
        dt = real_dt_s * self.state.speed
        self.state.tick += 1
        self.state.sim_time_s += dt
        sim_time_s = self.state.sim_time_s
        self._advance_mission(dt)

        frame = self._healthy_frame(dt)

        # Apply fault scenario mutation
        sdef = SCENARIO_DEFS[self.state.scenario]
        if self.state.scenario != "HEALTHY":
            if sdef.progressive:
                # ramp severity slowly over sim time (cap at configured severity)
                self._degradation = min(self.state.fault_severity, self._degradation + 0.01 * dt)
                sev = self._degradation
            else:
                sev = self.state.fault_severity
            sdef.mutate(frame, sev)

        # Final plausibility clamps (never emit impossible values)
        frame["rpm"] = max(0.0, min(6200.0, frame["rpm"]))
        frame["map_kpa"] = max(20.0, min(160.0, frame["map_kpa"]))
        frame["egt_avg_c"] = max(0.0, min(1100.0, frame["egt_avg_c"]))
        frame["cht_avg_c"] = max(0.0, min(200.0, frame["cht_avg_c"]))
        frame["oil_temp_c"] = max(0.0, min(180.0, frame["oil_temp_c"]))
        frame["oil_pressure_psi"] = max(0.0, min(120.0, frame["oil_pressure_psi"]))
        frame["fuel_flow_lph"] = max(0.0, frame["fuel_flow_lph"])
        frame["vibration_rms_g"] = max(0.0, frame["vibration_rms_g"])

        # Round for clean transport
        frame = {k: round(v, 3) for k, v in frame.items()}

        # Metadata
        frame["engine_id"] = self.state.engine_id
        frame["timestamp"] = time.time()
        frame["sim_time_s"] = round(sim_time_s, 3)   # monotonic sim clock
        frame["tick"] = self.state.tick
        frame["mission_phase"] = self.state.mission_phase
        frame["dt_s"] = round(dt, 3)
        frame["active_scenario"] = self.state.scenario
        frame["fault_severity"] = round(
            self._degradation if sdef.progressive else self.state.fault_severity, 3
        )
        frame["data_label"] = "SYNTHETIC"
        return frame
