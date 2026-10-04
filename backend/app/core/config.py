"""
core/config.py
==============
Central application configuration, loaded from environment variables.
No cloud-specific config. Local-first.
"""

from __future__ import annotations

import os
from functools import lru_cache


class Settings:
    """Application settings sourced from environment variables with safe defaults."""

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "VajraTwin"
    APP_VERSION: str = "3.0.0"
    APP_DESCRIPTION: str = (
        "AI-Enabled Real-Time Digital Twin for Health Monitoring, Fault Prediction, "
        "Degradation Tracking, RUL Estimation and Mission Reliability Assessment of "
        "Aero-Piston Engines used in MALE UAVs (calibrated on Rotax 914 F/UL)."
    )

    # ── Server ───────────────────────────────────────────────────────────────
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Comma-separated list; default allows local Vite dev servers.
    CORS_ORIGINS: list[str] = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5174,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,"
        "http://192.168.56.1:5173",
    ).split(",")

    # ── Database (MongoDB) ───────────────────────────────────────────────────
    MONGODB_URI: str = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB: str = os.environ.get("MONGODB_DB", "vajratwin")
    # Connection timeout before falling back to in-memory demo mode (ms)
    MONGODB_TIMEOUT_MS: int = int(os.environ.get("MONGODB_TIMEOUT_MS", "1500"))

    # ── AI / XAI provider ────────────────────────────────────────────────────
    # If LLM_API_KEY is empty, the deterministic explanation provider is used.
    LLM_PROVIDER: str = os.environ.get("LLM_PROVIDER", "deterministic")
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "")
    LLM_API_BASE: str = os.environ.get("LLM_API_BASE", "")
    LLM_MODEL: str = os.environ.get("LLM_MODEL", "")

    # ── Engine identity ──────────────────────────────────────────────────────
    DEFAULT_ENGINE_ID: str = os.environ.get("DEFAULT_ENGINE_ID", "rotax-914-uav-01")

    @property
    def llm_enabled(self) -> bool:
        """True only if an external LLM is explicitly configured."""
        return bool(self.LLM_API_KEY) and self.LLM_PROVIDER.lower() != "deterministic"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
