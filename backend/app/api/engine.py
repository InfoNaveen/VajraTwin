"""api/engine.py — per-engine health / diagnostics / degradation / RUL."""

from __future__ import annotations

from fastapi import APIRouter

from app.services.engine_service import get_engine_service

router = APIRouter()


def _last_or_empty(engine_id: str):
    svc = get_engine_service(engine_id)
    return svc, svc.last_analysis()


@router.get("/{engine_id}/health")
async def engine_health(engine_id: str):
    svc, a = _last_or_empty(engine_id)
    if not a:
        return {"engine_id": engine_id, "status": "no_data",
                "health_index": svc.degradation.current_health}
    return {
        "engine_id": engine_id,
        "health_index": a["degradation"]["health_index"],
        "health_trend": a["degradation"]["health_trend"],
        "advisory": a["advisory"],
        "fault_class": a["fault"]["fault_class"],
        "anomaly_status": a["anomaly"]["anomaly_status"],
        "sim_time_s": a["sim_time_s"],
    }


@router.get("/{engine_id}/diagnostics")
async def engine_diagnostics(engine_id: str):
    svc, a = _last_or_empty(engine_id)
    if not a:
        return {"engine_id": engine_id, "status": "no_data"}
    return {
        "engine_id": engine_id,
        "anomaly": a["anomaly"],
        "fault": a["fault"],
        "residuals": a["residuals"],
        "expected": a["expected"],
        "explanation": a["explanation"],
    }


@router.get("/{engine_id}/degradation")
async def engine_degradation(engine_id: str):
    svc, a = _last_or_empty(engine_id)
    if not a:
        return {"engine_id": engine_id, "status": "no_data", "history": svc.health_history()}
    return {
        "engine_id": engine_id,
        "degradation": a["degradation"],
        "history": svc.health_history(),
    }


@router.get("/{engine_id}/rul")
async def engine_rul(engine_id: str):
    svc, a = _last_or_empty(engine_id)
    rul = a["rul"] if a else svc.rul.estimate()
    return {"engine_id": engine_id, "rul": rul}
