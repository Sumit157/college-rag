# Current State

This file is the **single source of truth for the current implementation state of the project**.

It must always reflect what has actually been implemented, tested and verified.

The AI coding agent MUST read this file before starting work and MUST update it whenever meaningful implementation work is completed.

---

## Current Phase

```text
Phase: 2
Name: Retrieval
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
Phase 2 — Retrieval        [x] Completed
Phase 3 — Core RAG         [ ] Not started
Phase 4 — Chat UI          [ ] Not started
Phase 5 — MVP Hardening    [ ] Not started
Phase 6 — Study Features   [ ] Not started
Phase 7 — Advanced         [ ] Not started
```

---

## Current Objective

```text
Start Phase 3 — Core RAG.
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

### Phase 2 — Retrieval
- `EmbeddingProvider` interface + `LocalEmbeddingProvider` (Ollama `/api/embed`,
  batched, automatic `/api/embeddings` fallback for older servers); model from
  `EMBEDDING_MODEL` (nomic-embed-text, 768 dims).
- Chunks are embedded at ingestion time; chunks ingested earlier (embedding null)
  are backfilled automatically at application startup (best-effort, non-blocking).
- `MongoVectorStore` dual mode (`VECTOR_SEARCH_MODE`):
  Atlas `$vectorSearch` + vector search index when available; automatic
  in-process cosine fallback on standalone MongoDB (this machine's build rejects
  the Atlas stage). One capability probe per process.
- `POST /api/search`: question → query embedding → vector search → metadata
  filters (subject / semester / document_id / top_k) → evidence objects
  (`id` sequential, `document_id`, `filename`, `page`, `section`, `chunk_id`,
  `text`, `relevance` clamped 0..1), sorted by relevance.
- Validation: query 1–2000 chars (blank-after-trim → 422), top_k 1–50, semester 1–12;
  embedding/retrieval failures → user-safe 503, never stack traces.
- New config: `RETRIEVAL_TOP_K` (5), `EMBEDDING_DIMS` (768), `VECTOR_SEARCH_MODE` (auto).

---

## In Progress

- Nothing yet.

---

## Remaining

- Phase 3+ requirements (context builder, grounded generation, chat UI, hardening).

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
  app/ingestion/pipeline.py        validate → hash → parse → chunk → embed → store
  app/ingestion/errors.py          user-safe errors with HTTP status codes
  app/embeddings/provider.py       EmbeddingProvider + LocalEmbeddingProvider (Ollama)
  app/embeddings/errors.py         EmbeddingError (user-safe, HTTP 503)
  app/embeddings/backfill.py       startup backfill of missing chunk embeddings
  app/retrieval/vector_store.py    MongoVectorStore ($vectorSearch / local cosine)
  app/retrieval/retriever.py       question → embedding → search → evidence
  app/retrieval/evidence.py        evidence object builder (sequential ids)
  app/retrieval/startup.py         vector index + backfill at startup (best-effort)
  app/api/routes/search.py         POST /api/search
  app/models/health.py, document.py, evidence.py

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
Tests written: 126
Tests passing: 126
Tests failing: 0
```

Covers: validation, hashing, cleaning, section heuristics, chunking, all four parsers,
repositories (live MongoDB), document API end-to-end (upload/duplicate/filters/chunks/delete/stats),
config, health endpoint, Ollama adapter, live infrastructure, embedding provider
(MockTransport: batching, legacy fallback, error mapping), vector store (live MongoDB:
cosine math, ranking, top_k, metadata filters, auto-fallback), retriever (evidence ids,
filter pass-through, relevance clamping), search API (evidence shape, ranking,
subject/semester/document filters, validation, safe 503).

Frontend: `npm run build` (tsc + vite) and `npm run lint` (oxlint) pass (warnings only).

---

## Known Issues

- Port 8000 on this machine is occupied by an unrelated process; local verification runs the
  backend on port 8010 with `VITE_API_PROXY_TARGET=http://localhost:8010`. Defaults remain 8000.
- This machine's MongoDB rejects Atlas `$vectorSearch`; semantic search runs in automatic
  local-cosine mode (fine for MVP scale). Switching to Atlas later enables `VECTOR_SEARCH_MODE=auto`
  native vector search without code changes.
- Changing `EMBEDDING_MODEL` (different dimensions) requires re-uploading documents;
  chunks embedded with an old model are skipped by cosine scoring (length mismatch).

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
- Vector search is dual-mode: Atlas `$vectorSearch` when the deployment supports it,
  in-process cosine otherwise (2026-10-09) — keeps the product local-first on
  standalone MongoDB while staying Atlas-ready.
- Evidence metadata (ids, filenames, pages, sections, relevance) is created by backend
  code, never by the LLM.

---

## Recent Progress

- Phase 0 verified: health endpoint, UI shell, 16 tests.
- Phase 1 verified end-to-end: TXT + PDF uploaded through the dev proxy → indexed →
  3 chunks with page/section/subject/semester in MongoDB; duplicate → 409; `.exe` → 415;
  Documents page screenshot confirmed upload/list/status/actions UI.
- Phase 1 committed and pushed (`0c04265`).
- Phase 2 verified live: upload stored real 768-dim nomic-embed-text vectors;
  `POST /api/search` returned evidence ranked correctly (related query 0.72 vs
  unrelated 0.36); subject/semester filters narrow results; blank query → 422;
  startup backfill embedded a document uploaded before Phase 2 existed.

---

## Last Completed Task

```text
Phase 2 acceptance verified: 126/126 tests pass, real-embedding end-to-end search
confirmed (evidence objects with page/section/relevance, metadata filters, validation,
safe 503s), docs (API/DATABASE/RAG/ARCHITECTURE/ROADMAP) updated to match reality.
```

---

## Next Task

```text
Start Phase 3 — Core RAG.
Read docs/ROADMAP.md Phase 3: context builder, grounded system prompt, Ollama
generation, evidence-aware answers, programmatic citations, missing-context
behaviour, chat API (POST /api/chat).
```

---

## Last Updated

```text
2026-10-09 (Phase 2 — Retrieval: COMPLETED)
```
