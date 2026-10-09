# API

Base path: `/api`

## Documents

```text
POST   /documents
GET    /documents
GET    /documents/{id}
DELETE /documents/{id}
```

## Search

```text
POST /search
```

Request:

```json
{
  "query": "normalization",
  "subject": "DBMS",
  "semester": 5,
  "document_id": "optional",
  "top_k": 5
}
```

`query` is required (1–2000 chars). `subject`, `semester`, `document_id` and `top_k`
(1–50, default `RETRIEVAL_TOP_K`) are optional metadata filters.

Response:

```json
{
  "query": "normalization",
  "evidence": [
    {
      "id": "evidence-1",
      "document_id": "...",
      "filename": "DBMS Notes.pdf",
      "page": 42,
      "section": "Normalization",
      "chunk_id": "...",
      "text": "...",
      "relevance": 0.91
    }
  ],
  "count": 1
}
```

Evidence objects carry document, page, section, chunk and relevance metadata.
Evidence IDs are sequential (`evidence-1`, `evidence-2`, …) in relevance order.

## Chat

```text
POST /chat
POST /chat/stream
```

Request:

```json
{
  "question": "Explain paging",
  "subject": "Operating Systems"
}
```

Response:

```json
{
  "answer": "...",
  "evidence": [
    {
      "id": "evidence-1",
      "document": "OS Notes.pdf",
      "page": 42,
      "section": "Memory Management",
      "relevance": 0.91
    }
  ],
  "grounded": true
}
```

The frontend uses `evidence` to render source/context references. The backend, not the LLM, creates this metadata.

## Errors

Use consistent error codes and human-readable messages. Never expose stack traces to users.
