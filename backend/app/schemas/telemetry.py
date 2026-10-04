"""
schemas/telemetry.py
====================
Pydantic models for telemetry ingestion and the analysis response.

Validation is defensive: optional fields, NaN/inf rejected, impossible values
clamped by validators so malformed telemetry can never crash the backend.
"""

from __future__ import annotations

import math
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _finite(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


class TelemetryIn(BaseModel):
    """Incoming engine telemetry frame. All sensor fields optional."""

    engine_id: str = Field(default="rotax-914-uav-01")
    timestamp: Optional[float] = None
    sim_time_s: Optional[float] = None

    rpm: float = Field(default=0.0, ge=0, le=8000)
    map_kpa: Optional[float] = Field(default=None, ge=0, le=250)
    oat_c: float = Field(default=15.0, ge=-80, le=80)
    egt_avg_c: Optional[float] = Field(default=None)
    cht_avg_c: Optional[float] = Field(default=None)
    oil_temp_c: Optional[float] = Field(default=None)
    oil_pressure_psi: Optional[float] = Field(default=None)
    fuel_flow_lph: Optional[float] = Field(default=None)
    vibration_rms_g: Optional[float] = Field(default=None)
    throttle_pct: Optional[float] = Field(default=None, ge=0, le=120)
    altitude_m: Optional[float] = Field(default=None)
    mission_phase: Optional[str] = None
    dt_s: float = Field(default=1.0, gt=0, le=30)

    @field_validator(
        "egt_avg_c", "cht_avg_c", "oil_temp_c", "oil_pressure_psi",
        "fuel_flow_lph", "vibration_rms_g", "map_kpa", "altitude_m",
        mode="before",
    )
    @classmethod
    def _reject_nonfinite(cls, v):  # noqa: N805
        return _finite(v)

    def to_physics_dict(self) -> dict:
        """Flatten into the dict shape the physics engine consumes."""
        d = self.model_dump(exclude_none=True)
        return d


class ResidualBlock(BaseModel):
    delta_egt_c: float
    delta_cht_c: float
    delta_oil_temp_c: float
    delta_oil_pressure_psi: float
    delta_vibration_rms_g: float


class ExpectedBlock(BaseModel):
    egt_c: float
    cht_c: float
    oil_temp_c: float
    oil_pressure_psi: float
    vibration_rms_g: float


class AnalysisResponse(BaseModel):
    """Full closed-loop analysis for one telemetry frame."""

    engine_id: str
    sim_time_s: float
    tick: int = 0
    data_label: str = "SYNTHETIC"

    telemetry: dict
    twin_state: dict
    expected: ExpectedBlock
    residuals: ResidualBlock

    anomaly: dict
    fault: dict
    degradation: dict
    rul: dict
    advisory: dict
    explanation: dict
