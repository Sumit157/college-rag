"""MongoDB connection management."""

from __future__ import annotations

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import get_settings


class Mongo:
    """Thin wrapper around a synchronous MongoClient.

    Kept intentionally small so repositories can be added per phase without
    changing how the application opens and closes the connection.
    """

    def __init__(self, uri: str, database: str, timeout_ms: int = 5000) -> None:
        self._client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        self._db = self._client[database]

    @property
    def client(self) -> MongoClient:
        return self._client

    @property
    def db(self):
        return self._db

    def ping(self) -> bool:
        """Return True when the server answers a ping."""
        try:
            self._client.admin.command("ping")
            return True
        except PyMongoError:
            return False

    def close(self) -> None:
        self._client.close()


_mongo: Mongo | None = None


def init_mongo() -> Mongo:
    """Create the application-wide Mongo connection."""
    global _mongo
    if _mongo is None:
        settings = get_settings()
        _mongo = Mongo(
            uri=settings.mongodb_uri,
            database=settings.mongodb_database,
            timeout_ms=settings.mongodb_timeout_ms,
        )
    return _mongo


def get_mongo() -> Mongo:
    """Return the current connection, initialising it if needed."""
    if _mongo is None:
        return init_mongo()
    return _mongo


def close_mongo() -> None:
    global _mongo
    if _mongo is not None:
        _mongo.close()
        _mongo = None
