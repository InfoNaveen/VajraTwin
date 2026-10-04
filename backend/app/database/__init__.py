"""MongoDB persistence layer with automatic in-memory demo-mode fallback."""

from app.database.mongo import Database, get_database

__all__ = ["Database", "get_database"]
