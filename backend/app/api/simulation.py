"""api/simulation.py — simulator control + driven tick analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.simulation import ScenarioRequest, SpeedRequest
from app.services.engine_service import get_engine_service

router = APIRouter()


def _svc(engine_id: str):
    return get_engine_service(engine_id)


@router.post("/start")
async def sim_start(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.simulator.start()
    return svc.simulation_status()


@router.post("/stop")
async def sim_stop(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.simulator.stop()
    return svc.simulation_status()


@router.post("/pause")
async def sim_pause(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.simulator.pause()
    return svc.simulation_status()


@router.post("/resume")
async def sim_resume(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.simulator.resume()
    return svc.simulation_status()


@router.post("/reset")
async def sim_reset(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.reset()
    return svc.simulation_status()


@router.post("/scenario")
async def sim_scenario(req: ScenarioRequest, engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    try:
        svc.simulator.set_scenario(req.scenario)
        if req.severity is not None:
            svc.simulator.set_fault_severity(req.severity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return svc.simulation_status()


@router.post("/speed")
async def sim_speed(req: SpeedRequest, engine_id: str = Query(default="rotax-914-uav-01")):
    svc = _svc(engine_id)
    svc.simulator.set_speed(req.speed)
    return svc.simulation_status()


@router.get("/status")
async def sim_status(engine_id: str = Query(default="rotax-914-uav-01")):
    return _svc(engine_id).simulation_status()


@router.post("/tick")
async def sim_tick(
    engine_id: str = Query(default="rotax-914-uav-01"),
    dt: float = Query(default=1.0, ge=0.1, le=10.0),
):
    """
    Advance the simulator one frame and return the full analysis.
    The frontend polls this on an interval to drive the live dashboard.
    """
    svc = _svc(engine_id)
    if not svc.simulator.state.running or svc.simulator.state.paused:
        # Return the last analysis without advancing when stopped/paused.
        last = svc.last_analysis()
        status = svc.simulation_status()
        return {"advanced": False, "status": status, "analysis": last}
    analysis = await svc.simulate_tick(real_dt_s=dt, persist=True)
    return {"advanced": True, "status": svc.simulation_status(), "analysis": analysis}
