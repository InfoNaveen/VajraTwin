"""
conftest.py
===========
Pytest fixtures for the VajraTwin backend test suite.

Forces DEMO MODE (no MongoDB) by pointing MONGODB_URI at an unreachable host
with a short timeout, so the suite runs fully offline and also exercises the
in-memory fallback. A FastAPI TestClient drives the real app through its
lifespan (startup/shutdown) so the DB connect/fallback path is tested too.
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure the backend package is importable (tests live in backend/tests).
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Force demo-mode fallback before any app import.
os.environ.setdefault("MONGODB_URI", "mongodb://127.0.0.1:59999")
os.environ.setdefault("MONGODB_TIMEOUT_MS", "600")
os.environ.setdefault("LOG_LEVEL", "WARNING")


@pytest.fixture(scope="session")
def client():
    """A TestClient that runs the app lifespan (DB connect → demo fallback)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c
