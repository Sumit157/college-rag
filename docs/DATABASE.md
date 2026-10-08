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

Create a MongoDB vector index over chunk embeddings.

Also index common filters such as:
- document_id
- subject
- semester

Use a file hash to prevent duplicate indexing.
