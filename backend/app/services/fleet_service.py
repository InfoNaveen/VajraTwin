"""
services/fleet_service.py
=========================
Demonstrator-grade Fleet Operations layer.

This is a THIN ORCHESTRATION layer over the existing EngineService. It does NOT
contain any new physics/ML/analytics — each UAV is backed by one real
EngineService instance (keyed by engine_id), so fleet state is always exactly
the aggregate of real engine-level analysis.

Hierarchy:
    Fleet -> FleetAircraft -> EngineService (physics + ML + RUL + advisory)

DATA HONESTY: the fleet is a SYNTHETIC DEMONSTRATOR. All aircraft telemetry and
states come from the simulated engine pipeline. No real UAV/DRDO data.

Deterministic initial state
---------------------------
Six UAVs. Two (UAV-003, UAV-005) are pre-armed with a mild fault scenario and
warmed up so the fleet opens with a realistic "attention" distribution. All
states are produced by the real diagnostic pipeline — nothing is hardcoded as a
fake health percentage.

Status mapping (reuses existing advisory states, no new state machine)
----------------------------------------------------------------------
    GO                      -> HEALTHY
    GO WITH MONITORING      -> ATTENTION
    GO WITH DERATE          -> ATTENTION
    MAINTENANCE REQUIRED    -> CRITICAL
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.logging_config import get_logger
from app.services.engine_service import EngineService, get_engine_service

logger = get_logger("vajra.fleet")

# ── Advisory -> fleet status mapping ─────────────────────────────────────────
ADVISORY_TO_STATUS = {
    "GO": "HEALTHY",
    "GO WITH MONITORING": "ATTENTION",
    "GO WITH DERATE": "ATTENTION",
    "MAINTENANCE REQUIRED": "CRITICAL",
}
STATUS_ORDER = {"CRITICAL": 0, "ATTENTION": 1, "HEALTHY": 2}

# ── Deterministic demo fleet definition ──────────────────────────────────────
# (uav_id, callsign, initial_scenario, warmup_ticks)
# HEALTHY aircraft warm up healthy; ATTENTION aircraft pre-arm a mild fault.
FLEET_DEFINITION: List[tuple[str, str, str, float, int]] = [
    # uav_id,  callsign,     scenario,            severity, warmup
    ("UAV-001", "Garuda-1", "HEALTHY", 0.0, 12),
    ("UAV-002", "Garuda-2", "HEALTHY", 0.0, 12),
    ("UAV-003", "Garuda-3", "HIGH_EGT", 0.45, 14),
    ("UAV-004", "Garuda-4", "HEALTHY", 0.0, 12),
    ("UAV-005", "Garuda-5", "LOW_OIL_PRESSURE", 0.40, 14),
    ("UAV-006", "Garuda-6", "HEALTHY", 0.0, 12),
]


@dataclass
class FleetAircraft:
    uav_id: str
    callsign: str
    engine_id: str
    initial_scenario: str
    initial_severity: float
    warmup_ticks: int

    @property
    def service(self) -> EngineService:
        # Always resolves to the single shared EngineService for this engine.
        return get_engine_service(self.engine_id)


class FleetService:
    """Owns the demonstrator fleet and aggregates engine-level state."""

    def __init__(self) -> None:
        self.aircraft: Dict[str, FleetAircraft] = {}
        self._initialised = False
        # Serialises all fleet mutations (init, tick, scenario, reset) so a
        # tick can never interleave with a reset and corrupt engine state, and
        # overlapping frontend requests can never double-advance an engine.
        self._lock = asyncio.Lock()

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def ensure_initialised(self) -> None:
        if self._initialised:
            return
        async with self._lock:
            # re-check inside the lock (another request may have initialised)
            if self._initialised:
                return
            await self._build_fleet()
            self._initialised = True

    async def _build_fleet(self) -> None:
        self.aircraft.clear()
        for uav_id, callsign, scenario, severity, warmup in FLEET_DEFINITION:
            engine_id = uav_id  # 1:1 UAV<->engine for the demo
            ac = FleetAircraft(uav_id, callsign, engine_id, scenario, severity, warmup)
            self.aircraft[uav_id] = ac
            await self._prime_aircraft(ac)
        logger.info("Fleet initialised with %d aircraft", len(self.aircraft))

    async def _prime_aircraft(self, ac: FleetAircraft) -> None:
        """
        Produce a deterministic initial engine state via the REAL pipeline:
        start the sim, optionally arm a mild fault, warm up a few ticks.
        Fully async-native — safe to call from async request handlers.
        """
        svc = ac.service
        svc.reset()
        svc.simulator.start()
        if ac.initial_scenario != "HEALTHY":
            svc.simulator.set_scenario(ac.initial_scenario)
            svc.simulator.set_fault_severity(ac.initial_severity)
        for _ in range(ac.warmup_ticks):
            await svc.simulate_tick(real_dt_s=1.5, persist=False)

    # ── per-aircraft aggregation ───────────────────────────────────────────────
    def _aircraft_state(self, ac: FleetAircraft) -> Dict[str, Any]:
        svc = ac.service
        a = svc.last_analysis()
        sim = svc.simulator.state

        if not a:
            return {
                "uav_id": ac.uav_id,
                "callsign": ac.callsign,
                "engine_id": ac.engine_id,
                "status": "HEALTHY",
                "health_index": round(svc.degradation.current_health, 1),
                "fault_class": "NORMAL",
                "fault_label": "Normal",
                "fault_severity": 0.0,
                "anomaly_score": 0.0,
                "rul_hours": None,
                "rul_status": "INSUFFICIENT_HISTORY",
                "advisory_state": "GO",
                "mission_risk": None,
                "current_scenario": sim.scenario,
                "mission_phase": sim.mission_phase,
                "last_update_s": sim.sim_time_s,
                "data_label": "SYNTHETIC",
            }

        advisory_state = a["advisory"]["state"]
        return {
            "uav_id": ac.uav_id,
            "callsign": ac.callsign,
            "engine_id": ac.engine_id,
            "status": ADVISORY_TO_STATUS.get(advisory_state, "ATTENTION"),
            "health_index": a["degradation"]["health_index"],
            "fault_class": a["fault"]["fault_class"],
            "fault_label": a["fault"]["fault_label"],
            "fault_severity": a["fault"]["severity"],
            "anomaly_score": a["anomaly"]["anomaly_score"],
            "rul_hours": a["rul"].get("rul_hours"),
            "rul_status": a["rul"].get("status"),
            "advisory_state": advisory_state,
            "mission_risk": None,  # computed lazily in summary if needed
            "current_scenario": sim.scenario,
            "mission_phase": a["telemetry"].get("mission_phase") or sim.mission_phase,
            "last_update_s": a["sim_time_s"],
            "data_label": a.get("data_label", "SYNTHETIC"),
        }

    async def list_aircraft(self) -> List[Dict[str, Any]]:
        await self.ensure_initialised()
        return [self._aircraft_state(ac) for ac in self.aircraft.values()]

    async def aircraft_detail(self, uav_id: str) -> Optional[Dict[str, Any]]:
        await self.ensure_initialised()
        ac = self.aircraft.get(uav_id)
        if not ac:
            return None
        state = self._aircraft_state(ac)
        state["analysis"] = ac.service.last_analysis()
        state["simulation"] = ac.service.simulation_status()
        return state

    # ── maintenance priority (transparent, reason visible) ──────────────────────
    def _priority_key(self, s: Dict[str, Any]) -> tuple:
        # Lower tuple sorts first (higher priority).
        status_rank = STATUS_ORDER.get(s["status"], 1)
        # within status, worse health first, then lower RUL, then higher severity
        rul = s["rul_hours"] if s["rul_hours"] is not None else 9999.0
        return (status_rank, s["health_index"], rul, -s["fault_severity"])

    def maintenance_priority(self, states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = sorted(states, key=self._priority_key)
        out = []
        for i, s in enumerate(ranked, start=1):
            if s["status"] == "HEALTHY" and s["fault_class"] == "NORMAL":
                continue  # only list aircraft that actually need attention
            reason_bits = [s["fault_label"]]
            if s["rul_hours"] is not None:
                reason_bits.append(f"RUL {s['rul_hours']:.1f} h")
            reason_bits.append(s["advisory_state"])
            out.append({
                "rank": len(out) + 1,
                "uav_id": s["uav_id"],
                "callsign": s["callsign"],
                "status": s["status"],
                "fault_class": s["fault_class"],
                "health_index": s["health_index"],
                "rul_hours": s["rul_hours"],
                "advisory_state": s["advisory_state"],
                "reason": " · ".join(reason_bits),
            })
        return out

    # ── fleet-owned progression ──────────────────────────────────────────────
    async def tick_all(self, dt_s: float = 1.5) -> Dict[str, Any]:
        """
        Advance EVERY fleet engine by one frame through the real
        EngineService.simulate_tick() pipeline, then return the aggregated
        fleet summary.

        This is the ONLY way the fleet progresses. It mutates state, so it is
        exposed via POST (never via a GET). The lock guarantees that fleet
        ticks never overlap each other or interleave with scenario/reset.
        """
        await self.ensure_initialised()
        async with self._lock:
            for ac in self.aircraft.values():
                svc = ac.service
                if svc.simulator.state.running and not svc.simulator.state.paused:
                    await svc.simulate_tick(real_dt_s=dt_s, persist=False)
        # summary() takes the lock itself for the read-aggregate; call outside
        return await self.summary()

    # ── fleet summary ───────────────────────────────────────────────────────────
    async def summary(self) -> Dict[str, Any]:
        await self.ensure_initialised()
        states = await self.list_aircraft()

        healthy = sum(1 for s in states if s["status"] == "HEALTHY")
        attention = sum(1 for s in states if s["status"] == "ATTENTION")
        critical = sum(1 for s in states if s["status"] == "CRITICAL")

        # Fleet health = simple mean of engine health indices (documented).
        healths = [s["health_index"] for s in states]
        fleet_health = round(sum(healths) / len(healths), 1) if healths else 0.0

        # Highest-risk aircraft = top of maintenance priority (worst engine state).
        priority = self.maintenance_priority(states)
        highest_risk = priority[0] if priority else None

        # Fault distribution across the fleet
        fault_dist: Dict[str, int] = {}
        for s in states:
            fc = s["fault_class"]
            fault_dist[fc] = fault_dist.get(fc, 0) + 1

        return {
            "fleet_name": "VajraTwin Demonstrator Fleet",
            "data_label": "SYNTHETIC",
            "total_aircraft": len(states),
            "status_counts": {"healthy": healthy, "attention": attention, "critical": critical},
            "fleet_health": fleet_health,
            "fleet_health_method": "Unweighted mean of per-engine health indices (0..100).",
            "highest_risk": highest_risk,
            "maintenance_priority": priority,
            "fault_distribution": fault_dist,
            "aircraft": states,
            "generated_at": time.time(),
        }

    # ── control passthrough (reuses EngineService / simulator) ──────────────────
    async def set_scenario(self, uav_id: str, scenario: str, severity: Optional[float]) -> Dict[str, Any]:
        await self.ensure_initialised()
        if uav_id not in self.aircraft:
            raise KeyError(uav_id)
        async with self._lock:
            ac = self.aircraft[uav_id]
            svc = ac.service
            if not svc.simulator.state.running:
                svc.simulator.start()
            svc.simulator.set_scenario(scenario)
            if severity is not None:
                svc.simulator.set_fault_severity(severity)
            return svc.simulation_status()

    async def reset_aircraft(self, uav_id: str) -> Dict[str, Any]:
        """Reset a single aircraft back to its deterministic initial state."""
        await self.ensure_initialised()
        if uav_id not in self.aircraft:
            raise KeyError(uav_id)
        async with self._lock:
            ac = self.aircraft[uav_id]
            await self._prime_aircraft(ac)
            return self._aircraft_state(ac)

    async def reset_fleet(self) -> None:
        """Rebuild the entire deterministic demo fleet."""
        async with self._lock:
            self._initialised = False
            await self._build_fleet()
            self._initialised = True


# ── singleton ─────────────────────────────────────────────────────────────────
_FLEET: Optional[FleetService] = None


def get_fleet_service() -> FleetService:
    global _FLEET
    if _FLEET is None:
        _FLEET = FleetService()
    return _FLEET
