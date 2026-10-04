"""schemas/simulation.py — simulator control request/response."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    scenario: str = Field(..., description="Scenario key, e.g. HIGH_CHT")
    severity: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SpeedRequest(BaseModel):
    speed: float = Field(..., ge=0.25, le=10.0)


class SimulationStatus(BaseModel):
    running: bool
    paused: bool
    scenario: str
    fault_severity: float
    speed: float
    tick: int
    sim_time_s: float
    mission_phase: str
    engine_id: str
    available_scenarios: list
