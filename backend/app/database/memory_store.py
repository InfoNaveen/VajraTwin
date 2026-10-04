"""
database/memory_store.py
========================
In-memory fallback store used when MongoDB is unavailable (DEMO MODE).

Implements the small subset of the collection API the app actually uses:
insert_one, find (sorted, limited), find_one (latest), count. This keeps the
service layer identical whether we're on real Mongo or the fallback.

Everything here is ephemeral — it lives only for the process lifetime.
"""

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import Any, Dict, List, Optional

_counter = itertools.count(1)


class MemoryCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self._docs: List[Dict[str, Any]] = []

    async def insert_one(self, doc: Dict[str, Any]) -> str:
        doc = dict(doc)
        doc.setdefault("_id", next(_counter))
        self._docs.append(doc)
        return str(doc["_id"])

    async def find_recent(
        self, query: Optional[Dict[str, Any]] = None, limit: int = 100, sort_key: str = "sim_time_s"
    ) -> List[Dict[str, Any]]:
        docs = self._match(query)
        docs = sorted(docs, key=lambda d: d.get(sort_key, 0), reverse=True)[:limit]
        # return in chronological order for charts
        return list(reversed([self._clean(d) for d in docs]))

    async def find_latest(self, query: Optional[Dict[str, Any]] = None, sort_key: str = "sim_time_s") -> Optional[Dict[str, Any]]:
        docs = self._match(query)
        if not docs:
            return None
        latest = max(docs, key=lambda d: d.get(sort_key, 0))
        return self._clean(latest)

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        return len(self._match(query))

    def _match(self, query: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not query:
            return list(self._docs)
        return [d for d in self._docs if all(d.get(k) == v for k, v in query.items())]

    @staticmethod
    def _clean(doc: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(doc)
        d.pop("_id", None)
        return d


class MemoryStore:
    """A tiny Mongo-like database backed by dicts."""

    def __init__(self) -> None:
        self._collections: Dict[str, MemoryCollection] = defaultdict(
            lambda: MemoryCollection("unnamed")
        )

    def collection(self, name: str) -> MemoryCollection:
        if name not in self._collections:
            self._collections[name] = MemoryCollection(name)
        return self._collections[name]
