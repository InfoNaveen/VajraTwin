"""
main.py
=======
VajraTwin FastAPI application entry point.

- Lifespan: connect DB (falls back to demo mode automatically), disconnect.
- CORS: configured from settings (local-first).
- Global exception handler: structured JSON errors, never leaks stack traces.
- /health: service + DB status.

Run:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.database.mongo import get_database
from app.api import api_router

configure_logging()
logger = get_logger("vajra.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = get_database()
    await db.connect()
    if db.demo_mode:
        logger.info("Backend running in DEMO MODE (in-memory persistence).")
    yield
    await db.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health():
    db = get_database()
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "database": db.status(),
        "ai_provider": "external_llm" if settings.llm_enabled else "deterministic",
        "physics_engine": "Rotax 914 F/UL algebraic surrogate",
        "data_label": "SYNTHETIC",
    }


@app.get("/", tags=["health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak a stack trace; return a structured error."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
            "path": request.url.path,
        },
    )
