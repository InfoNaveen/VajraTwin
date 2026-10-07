"""api/fleet.py — thin fleet-operations routes over FleetService."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.simulation import ScenarioRequest
from app.services.fleet_service import get_fleet_service

router = APIRouter()


@router.get("/summary")
async def fleet_summary():
    """Aggregated fleet state: counts, fleet health, highest risk, priority."""
    return await get_fleet_service().summary()


@router.get("/aircraft")
async def fleet_aircraft():
    """Flat list of per-aircraft engine-level state."""
    return await get_fleet_service().list_aircraft()


@router.post("/tick")
async def fleet_tick(dt: float = 1.5):
    """
    Advance ALL six fleet engines by one frame through the real engine
    pipeline, then return the aggregated fleet summary. This is how Fleet
    Operations progresses — GET endpoints remain read-only.
    """
    return await get_fleet_service().tick_all(dt_s=dt)


@router.get("/{uav_id}")
async def fleet_aircraft_detail(uav_id: str):
    detail = await get_fleet_service().aircraft_detail(uav_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"UAV '{uav_id}' not found")
    return detail


@router.post("/{uav_id}/scenario")
async def fleet_set_scenario(uav_id: str, req: ScenarioRequest):
    try:
        return await get_fleet_service().set_scenario(uav_id, req.scenario, req.severity)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"UAV '{uav_id}' not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{uav_id}/reset")
async def fleet_reset_aircraft(uav_id: str):
    try:
        return await get_fleet_service().reset_aircraft(uav_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"UAV '{uav_id}' not found")


@router.post("/reset")
async def fleet_reset_all():
    await get_fleet_service().reset_fleet()
    return await get_fleet_service().summary()
