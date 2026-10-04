"""API routers — thin HTTP layer over the service orchestration."""

from fastapi import APIRouter

from app.api import telemetry, engine, mission, simulation, dashboard, fleet

api_router = APIRouter()
api_router.include_router(telemetry.router, prefix="/api", tags=["telemetry"])
api_router.include_router(engine.router, prefix="/api/engine", tags=["engine"])
api_router.include_router(mission.router, prefix="/api/mission", tags=["mission"])
api_router.include_router(simulation.router, prefix="/api/simulation", tags=["simulation"])
api_router.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
api_router.include_router(fleet.router, prefix="/api/fleet", tags=["fleet"])

__all__ = ["api_router"]
