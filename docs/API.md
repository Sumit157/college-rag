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
  "top_k": 5
}
```

Return evidence objects with document, page, section, chunk and relevance metadata.

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
