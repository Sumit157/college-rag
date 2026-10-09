# Current State

This file is the **single source of truth for the current implementation state of the project**.

It must always reflect what has actually been implemented, tested and verified.

The AI coding agent MUST read this file before starting work and MUST update it whenever meaningful implementation work is completed.

---

## Current Phase

```text
Phase: 1
Name: Document Ingestion
Status: COMPLETED
```

Possible statuses:

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
COMPLETED
```

---

## Overall Progress

```text
Phase 0 — Foundation       [x] Completed
Phase 1 — Ingestion        [x] Completed
Phase 2 — Retrieval        [ ] Not started
Phase 3 — Core RAG         [ ] Not started
Phase 4 — Chat UI          [ ] Not started
Phase 5 — MVP Hardening    [ ] Not started
Phase 6 — Study Features   [ ] Not started
Phase 7 — Advanced         [ ] Not started
```

---

## Current Objective

```text
Start Phase 2 — Retrieval.
```

---

## Completed

### Phase 0 — Foundation
- FastAPI skeleton, centralised env config, CORS, lifespan-managed MongoDB connection.
- `GET /api/health`: MongoDB ping + Ollama health/model report.
- React + Vite + TypeScript frontend, Tailwind v4, shadcn/ui, base shell
  (Dashboard / Documents / Chat / Settings) with live status panels.
- ReactBits Pro dropped (paid registry) — shadcn/ui is the UI foundation (docs updated).

### Phase 1 — Document Ingestion
- `POST/GET/DELETE /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/chunks`,
  `GET /api/stats` (all under `/api`).
- Validation chain: extension whitelist → size limit (middleware + byte check, 413) →
  declared-MIME check → byte-level content sniffing (PDF magic, DOCX/PPTX zip parts, TXT binary guard).
- SHA-256 hashing with duplicate detection (409 with existing document).
- Parsers preserving source metadata: PDF (PyMuPDF, per-page + heading heuristic sections),
  DOCX (heading styles, tables, no pages), PPTX (per-slide, slide titles), TXT (heading heuristic).
- Cleaning (line endings, control chars, blank-line collapse) + section heuristics.
- Configurable chunking (default 600 tokens, 80 overlap; `CHUNK_SIZE_TOKENS`/`CHUNK_OVERLAP_TOKENS`),
  never crosses page boundaries, hard-splits oversized units, section/page metadata per chunk.
- Ingestion pipeline with status lifecycle `processing → indexed | failed`; failures keep a
  user-safe error message on the document record.
- MongoDB repositories with indexes (file_hash, subject+semester, status, created_at, document_id);
  deletion removes document **and** all its chunks.
- Documents UI: upload form (file + subject + semester), status badges, filters, table,
  detail dialog with chunk preview, delete confirmation dialog.
- Dashboard wired to `/api/stats` and recent documents.

---

## In Progress

- Nothing yet.

---

## Remaining

- Phase 2 requirements (embedding provider, vector index, semantic search, evidence objects).

---

## Files/Components Implemented

```text
Backend
  app/main.py                      app factory, CORS, upload size guard, routers
  app/core/config.py               settings (env-driven)
  app/database/mongo.py            connection wrapper
  app/database/repositories.py     DocumentRepository, ChunkRepository + indexes
  app/llm/ollama.py                Ollama health/model adapter
  app/api/routes/health.py         GET /api/health
  app/api/routes/documents.py      upload/list/detail/chunks/delete
  app/api/routes/stats.py          GET /api/stats
  app/ingestion/validation.py      extension/MIME/size/content checks
  app/ingestion/hashing.py         sha256
  app/ingestion/cleaning.py        text normalisation
  app/ingestion/sections.py        heading heuristics
  app/ingestion/parsers.py         PDF/DOCX/PPTX/TXT parsers (ParsedUnit)
  app/ingestion/chunking.py        page-safe chunker with overlap
  app/ingestion/pipeline.py        validate → hash → parse → chunk → store
  app/ingestion/errors.py          user-safe errors with HTTP status codes
  app/models/health.py, document.py

Frontend
  frontend/src/pages/Documents.tsx  upload, table, filters, detail + delete dialogs
  frontend/src/pages/Dashboard.tsx  stats + recent documents
  frontend/src/types/document.ts    API types
  frontend/src/lib/api.ts           apiFetch + apiUpload (safe error messages)
  frontend/src/components/ui/{select,table,...}.tsx
```

---

## Tests

```text
Tests written: 93
Tests passing: 93
Tests failing: 0
```

Covers: validation, hashing, cleaning, section heuristics, chunking, all four parsers,
repositories (live MongoDB), document API end-to-end (upload/duplicate/filters/chunks/delete/stats),
config, health endpoint, Ollama adapter, live infrastructure.

Frontend: `npm run build` (tsc + vite) and `npm run lint` (oxlint) pass (warnings only).

---

## Known Issues

- Port 8000 on this machine is occupied by an unrelated process; local verification runs the
  backend on port 8010 with `VITE_API_PROXY_TARGET=http://localhost:8010`. Defaults remain 8000.
- Chunk embeddings are stored as `embedding: null` — Phase 2 fills them.

---

## Blockers

```text
None.
```

---

## Architecture Decisions

- MongoDB is the primary database and vector-search store.
- Ollama is the local LLM runtime; React + Vite frontend; FastAPI backend.
- RAG answers must be grounded exclusively in uploaded documents.
- ReactBits Pro components are not used (paid license); shadcn/ui instead (2026-10-08).
- Uploads are parsed in-memory (max `MAX_UPLOAD_SIZE_MB`, default 20 MB); raw files are not stored —
  MongoDB holds document metadata + chunks only.
- Chunks never cross page boundaries; section metadata comes from the chunk's first unit.
- Document IDs are exposed as strings; `to_object_id` guards invalid IDs (404).

---

## Recent Progress

- Phase 0 verified: health endpoint, UI shell, 16 tests.
- Phase 1 verified end-to-end: TXT + PDF uploaded through the dev proxy → indexed →
  3 chunks with page/section/subject/semester in MongoDB; duplicate → 409; `.exe` → 415;
  Documents page screenshot confirmed upload/list/status/actions UI.
- Library cleaned up after verification (0 documents left behind).

---

## Last Completed Task

```text
Phase 1 acceptance verified: 93/93 tests pass, end-to-end upload → parse → chunk →
MongoDB confirmed (chunks carry page/section metadata), UI renders the library with
status/filters/detail/delete.
```

---

## Next Task

```text
Start Phase 2 — Retrieval.
Read docs/ROADMAP.md Phase 2: embedding provider (configurable local model via Ollama),
MongoDB vector index, semantic search with subject/semester/document filters,
evidence objects and retrieval tests.
```

---

## Last Updated

```text
2026-10-09
```
