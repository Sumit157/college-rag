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

Only `documents` and `document_chunks` are required for the MVP.

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
