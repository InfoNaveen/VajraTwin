"""
database/mongo.py
=================
MongoDB abstraction with automatic in-memory demo-mode fallback.

Collections:
    telemetry           raw + analysed telemetry frames
    health_states       per-frame health snapshots
    fault_events        discrete fault onsets
    missions            mission-reliability analyses
    maintenance_events  advisory transitions / maintenance records

Behaviour:
    - On connect(), attempt a MongoDB ping within MONGODB_TIMEOUT_MS.
    - If it fails for ANY reason, switch to the in-memory MemoryStore and set
      demo_mode = True. The application keeps running.
    - `status()` reports which backend is active so the UI can show DEMO MODE.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging_config import get_logger
from app.database.memory_store import MemoryStore

logger = get_logger("vajra.db")

COLLECTIONS = [
    "telemetry",
    "health_states",
    "fault_events",
    "missions",
    "maintenance_events",
]


class Database:
    def __init__(self) -> None:
        self._client = None
        self._db = None
        self._memory: Optional[MemoryStore] = None
        self.demo_mode: bool = False
        self.backend: str = "uninitialised"

    # ── lifecycle ──────────────────────────────────────────────────────────────
    async def connect(self) -> None:
        """Try MongoDB; fall back to in-memory demo mode on any failure."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient

            self._client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            )
            # force a round-trip to verify connectivity
            await self._client.admin.command("ping")
            self._db = self._client[settings.MONGODB_DB]
            await self._ensure_indexes()
            self.demo_mode = False
            self.backend = "mongodb"
            logger.info("Connected to MongoDB at %s (db=%s)", settings.MONGODB_URI, settings.MONGODB_DB)
        except Exception as exc:  # noqa: BLE001 — any failure => demo mode
            logger.warning(
                "MongoDB unavailable (%s). Falling back to IN-MEMORY DEMO MODE.", exc
            )
            self._client = None
            self._db = None
            self._memory = MemoryStore()
            self.demo_mode = True
            self.backend = "in_memory_demo"

    async def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            logger.info("MongoDB connection closed")

    async def _ensure_indexes(self) -> None:
        if self._db is None:
            return
        await self._db.telemetry.create_index([("engine_id", 1), ("sim_time_s", -1)])
        await self._db.health_states.create_index([("engine_id", 1), ("sim_time_s", -1)])
        await self._db.fault_events.create_index([("engine_id", 1), ("sim_time_s", -1)])
        await self._db.missions.create_index([("mission_id", 1)])
        await self._db.maintenance_events.create_index([("engine_id", 1), ("sim_time_s", -1)])

    # ── generic ops (route to Mongo or memory) ─────────────────────────────────
    async def insert(self, collection: str, doc: Dict[str, Any]) -> str:
        if self.demo_mode:
            return await self._memory.collection(collection).insert_one(doc)
        result = await self._db[collection].insert_one(dict(doc))
        return str(result.inserted_id)

    async def recent(
        self, collection: str, query: Optional[Dict[str, Any]] = None,
        limit: int = 100, sort_key: str = "sim_time_s",
    ) -> List[Dict[str, Any]]:
        if self.demo_mode:
            return await self._memory.collection(collection).find_recent(query, limit, sort_key)
        cursor = self._db[collection].find(query or {}, {"_id": 0}).sort(sort_key, -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return list(reversed(docs))

    async def latest(
        self, collection: str, query: Optional[Dict[str, Any]] = None, sort_key: str = "sim_time_s",
    ) -> Optional[Dict[str, Any]]:
        if self.demo_mode:
            return await self._memory.collection(collection).find_latest(query, sort_key)
        return await self._db[collection].find_one(query or {}, {"_id": 0}, sort=[(sort_key, -1)])

    async def count(self, collection: str, query: Optional[Dict[str, Any]] = None) -> int:
        if self.demo_mode:
            return await self._memory.collection(collection).count(query)
        return await self._db[collection].count_documents(query or {})

    # ── status for the UI ──────────────────────────────────────────────────────
    def status(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "demo_mode": self.demo_mode,
            "uri": settings.MONGODB_URI if not self.demo_mode else None,
            "database": settings.MONGODB_DB if not self.demo_mode else "in_memory",
            "collections": COLLECTIONS,
        }


# ── singleton ──────────────────────────────────────────────────────────────────
_DB: Optional[Database] = None


def get_database() -> Database:
    global _DB
    if _DB is None:
        _DB = Database()
    return _DB
