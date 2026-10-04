"""api/telemetry.py — telemetry ingestion + history (thin routes)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas.telemetry import TelemetryIn
from app.services.engine_service import get_engine_service
from app.database.mongo import get_database

router = APIRouter()


@router.post("/telemetry")
async def ingest_telemetry(frame: TelemetryIn):
    """Ingest one telemetry frame and return the full closed-loop analysis."""
    svc = get_engine_service(frame.engine_id)
    analysis = await svc.analyse_frame(frame.to_physics_dict(), persist=True)
    return analysis


@router.get("/telemetry/latest")
async def latest_telemetry(engine_id: str = Query(default="rotax-914-uav-01")):
    db = get_database()
    doc = await db.latest("telemetry", {"engine_id": engine_id})
    return doc or {"message": "no telemetry yet", "engine_id": engine_id}


@router.get("/telemetry/history")
async def telemetry_history(
    engine_id: str = Query(default="rotax-914-uav-01"),
    limit: int = Query(default=120, ge=1, le=1000),
):
    db = get_database()
    return await db.recent("telemetry", {"engine_id": engine_id}, limit=limit)
