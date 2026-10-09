# Database

MongoDB is the primary application database and vector-search store.

## Collections

```text
documents
document_chunks
subjects
conversations
messages
```

Only `documents` and `document_chunks` are required for the MVP;
`conversations` is implemented (chat history). `subjects` and `messages` are
planned — chat history stores its turns embedded in each conversation instead
of a separate `messages` collection.

## Document

```json
{
  "_id": "...",
  "filename": "OS Notes.pdf",
  "file_hash": "...",
  "file_type": "pdf",
  "subject": "Operating Systems",
  "semester": 5,
  "status": "indexed",
  "created_at": "..."
}
```

## Chunk

```json
{
  "_id": "...",
  "document_id": "...",
  "text": "...",
  "embedding": [],
  "page": 42,
  "section": "Memory Management",
  "subject": "Operating Systems",
  "semester": 5,
  "chunk_index": 18
}
```

## Conversation

```json
{
  "_id": "...",
  "title": "Explain paging",
  "turns": [
    {
      "id": "turn-1",
      "question": "Explain paging",
      "answer": "...",
      "grounded": true,
      "evidence": [],
      "subject": null,
      "semester": null,
      "document_id": null,
      "created_at": "..."
    }
  ],
  "turn_count": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

Title is the first question (truncated to 80 chars). Turns are appended after
each successful chat request; `updated_at` changes with them. Index:
`updated_at` descending (conversation list order). Conversations with
`turn_count: 0` are created when a chat starts but hidden from the list until
the first turn is saved.

## Vector index

Chunk embeddings are searched in one of two modes (`VECTOR_SEARCH_MODE`):

- `auto` (default): use MongoDB Atlas `$vectorSearch` with a vector search index
  when the deployment supports it; otherwise fall back to cosine similarity
  computed in-process over metadata-filtered chunks (standalone Community
  MongoDB has no vector search stage).
- `vector`: require Atlas `$vectorSearch` (fail loudly when unavailable).
- `local`: always score in-process.

Index creation and mode probing are best-effort at startup; search never blocks
on them. `EMBEDDING_DIMS` must match the configured embedding model
(nomic-embed-text=768, bge-m3=1024).

Chunks missing an embedding (ingested before embeddings were wired up) are
backfilled automatically at application startup.

Also filter on common metadata:
- document_id
- subject
- semester

Use a file hash to prevent duplicate indexing.
