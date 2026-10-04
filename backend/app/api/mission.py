"""api/mission.py — mission reliability analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.mission import MissionRequest
from app.services.engine_service import get_engine_service
from app.database.mongo import get_database

router = APIRouter()


@router.post("/analyze")
async def analyze_mission(req: MissionRequest):
    svc = get_engine_service(req.engine_id)
    return await svc.analyse_mission(req.model_dump())


@router.get("/{mission_id}")
async def get_mission(mission_id: str):
    db = get_database()
    doc = await db.latest("missions", {"mission_id": mission_id}, sort_key="mission_id")
    if not doc:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")
    return doc
