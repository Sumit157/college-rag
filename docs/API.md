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
  "subject": "Operating Systems",
  "semester": 5,
  "document_id": "optional",
  "top_k": 5
}
```

`question` is required (1–2000 chars); all filters are optional.

Response (`POST /chat`):

```json
{
  "answer": "...",
  "evidence": [
    {
      "id": "evidence-1",
      "document_id": "...",
      "filename": "OS Notes.pdf",
      "page": 42,
      "section": "Memory Management",
      "chunk_id": "...",
      "text": "...",
      "relevance": 0.91
    }
  ],
  "grounded": true
}
```

When no evidence passes the relevance threshold the answer is the fixed
missing-context message with `grounded: false` and `evidence: []` — the LLM is
not called. The frontend uses `evidence` to render source/context references.
The backend, not the LLM, creates this metadata.

### Streaming (`POST /chat/stream`)

Server-Sent Events (`text/event-stream`), one JSON object per `data:` line:

```text
{"type":"meta","question":"...","grounded":true,"evidence":[...]}   first: sources + grounding
{"type":"token","text":"Pag"}                                       answer deltas
{"type":"done","answer":"...","grounded":true,"evidence":[...]}     final state
{"type":"error","detail":"..."}                                     generation failed (replaces done)
```

Without evidence: `meta` (`grounded: false`) followed directly by `done` with
the missing-context answer; no `token` events.

## Errors

Use consistent error codes and human-readable messages. Never expose stack traces to users.
