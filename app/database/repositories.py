"""MongoDB repositories for documents and chunks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database


def to_object_id(value: str) -> ObjectId | None:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


class DocumentRepository:
    def __init__(self, db: Database) -> None:
        self._col = db["documents"]
        self._chunks = db["document_chunks"]

    def ensure_indexes(self) -> None:
        self._col.create_index([("file_hash", ASCENDING)])
        self._col.create_index([("subject", ASCENDING), ("semester", ASCENDING)])
        self._col.create_index([("status", ASCENDING)])
        self._col.create_index([("created_at", DESCENDING)])
        self._chunks.create_index([("document_id", ASCENDING)])
        self._chunks.create_index([("subject", ASCENDING), ("semester", ASCENDING)])

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        record = {
            **record,
            "created_at": record.get("created_at") or datetime.now(timezone.utc),
        }
        result = self._col.insert_one(record)
        record["_id"] = result.inserted_id
        return record

    def get(self, document_id: str) -> dict[str, Any] | None:
        oid = to_object_id(document_id)
        if oid is None:
            return None
        return self._col.find_one({"_id": oid})

    def get_by_hash(self, file_hash: str) -> dict[str, Any] | None:
        return self._col.find_one({"file_hash": file_hash})

    def list(
        self,
        subject: str | None = None,
        semester: int | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if subject:
            query["subject"] = subject
        if semester is not None:
            query["semester"] = semester
        return list(self._col.find(query).sort("created_at", DESCENDING))

    def mark_indexed(
        self,
        document_id: str,
        chunk_count: int,
        page_count: int | None,
    ) -> dict[str, Any] | None:
        oid = to_object_id(document_id)
        if oid is None:
            return None
        return self._col.find_one_and_update(
            {"_id": oid},
            {
                "$set": {
                    "status": "indexed",
                    "chunk_count": chunk_count,
                    "page_count": page_count,
                    "error": None,
                }
            },
            return_document=True,
        )

    def mark_failed(self, document_id: str, error: str) -> dict[str, Any] | None:
        oid = to_object_id(document_id)
        if oid is None:
            return None
        return self._col.find_one_and_update(
            {"_id": oid},
            {"$set": {"status": "failed", "error": error}},
            return_document=True,
        )

    def delete(self, document_id: str) -> bool:
        oid = to_object_id(document_id)
        if oid is None:
            return False
        self._chunks.delete_many({"document_id": document_id})
        result = self._col.delete_one({"_id": oid})
        return result.deleted_count > 0

    def stats(self) -> dict[str, int]:
        documents = self._col.count_documents({})
        subjects = len(self._col.distinct("subject"))
        return {"documents": documents, "subjects": subjects}


class ChunkRepository:
    def __init__(self, db: Database) -> None:
        self._col = db["document_chunks"]

    def insert_many(self, records: list[dict[str, Any]]) -> None:
        if records:
            self._col.insert_many(records)

    def count_by_document(self, document_id: str) -> int:
        return self._col.count_documents({"document_id": document_id})

    def list_by_document(
        self,
        document_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        query = {"document_id": document_id}
        total = self._col.count_documents(query)
        items = list(
            self._col.find(query)
            .sort("chunk_index", ASCENDING)
            .skip(offset)
            .limit(limit)
        )
        return items, total

    def delete_by_document(self, document_id: str) -> int:
        return self._col.delete_many({"document_id": document_id}).deleted_count


class ConversationRepository:
    def __init__(self, db: Database) -> None:
        self._col = db["conversations"]

    def ensure_indexes(self) -> None:
        self._col.create_index([("updated_at", DESCENDING)])

    def create(self, title: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        record: dict[str, Any] = {
            "title": title,
            "turns": [],
            "turn_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        result = self._col.insert_one(record)
        record["_id"] = result.inserted_id
        return record

    def get(self, conversation_id: str) -> dict[str, Any] | None:
        oid = to_object_id(conversation_id)
        if oid is None:
            return None
        return self._col.find_one({"_id": oid})

    def list(self) -> list[dict[str, Any]]:
        # Empty conversations (created but never answered) stay hidden.
        return list(
            self._col.find({"turn_count": {"$gt": 0}}, {"turns": 0}).sort(
                "updated_at", DESCENDING
            )
        )

    def append_turn(self, conversation_id: str, turn: dict[str, Any]) -> dict[str, Any] | None:
        oid = to_object_id(conversation_id)
        if oid is None:
            return None
        return self._col.find_one_and_update(
            {"_id": oid},
            {
                "$push": {"turns": turn},
                "$inc": {"turn_count": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )

    def delete(self, conversation_id: str) -> bool:
        oid = to_object_id(conversation_id)
        if oid is None:
            return False
        result = self._col.delete_one({"_id": oid})
        return result.deleted_count > 0
