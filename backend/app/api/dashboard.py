"""api/dashboard.py — single aggregated summary for the GCS first screen."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.engine_service import get_engine_service
from app.database.mongo import get_database

router = APIRouter()


@router.get("/summary")
async def dashboard_summary(engine_id: str = Query(default="rotax-914-uav-01")):
    svc = get_engine_service(engine_id)
    a = svc.last_analysis()
    db = get_database()

    summary = {
        "engine_id": engine_id,
        "db_status": db.status(),
        "simulation": svc.simulation_status(),
        "health_history": svc.health_history(),
    }
    if a:
        summary.update({
            "has_data": True,
            "data_label": a["data_label"],
            "sim_time_s": a["sim_time_s"],
            "telemetry": a["telemetry"],
            "twin_state": a["twin_state"],
            "expected": a["expected"],
            "residuals": a["residuals"],
            "anomaly": a["anomaly"],
            "fault": a["fault"],
            "degradation": a["degradation"],
            "rul": a["rul"],
            "advisory": a["advisory"],
            "explanation": a["explanation"],
        })
    else:
        summary["has_data"] = False
    return summary
