"""schemas/mission.py — mission planning request/response."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class MissionRequest(BaseModel):
    engine_id: str = Field(default="rotax-914-uav-01")
    mission_duration_hours: float = Field(default=4.0, gt=0, le=48)
    cruise_load: float = Field(default=0.65, ge=0.1, le=1.2)
    max_load: float = Field(default=0.9, ge=0.1, le=1.2)
    altitude_m: float = Field(default=4500.0, ge=0, le=15000)
    route_length_km: Optional[float] = Field(default=None, ge=0)
    environment: str = Field(default="STANDARD")  # STANDARD|HOT|HIGH_ALTITUDE|HARSH


class MissionResponse(BaseModel):
    mission_id: str
    engine_id: str
    completion_probability: float
    completion_probability_pct: float
    risk_level: str
    limiting_factor: str
    factors: dict
    recommendation: str
    methodology: str
    health_index_used: float
    rul_hours_used: Optional[float]
