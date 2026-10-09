# Current State

This file is the **single source of truth for the current implementation state of the project**.

It must always reflect what has actually been implemented, tested and verified.

The AI coding agent MUST read this file before starting work and MUST update it whenever meaningful implementation work is completed.

---

## Current Phase

```text
Phase: 4
Name: Chat UI
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
Phase 3 — Core RAG         [x] Completed
Phase 4 — Chat UI          [x] Completed
Phase 5 — MVP Hardening    [ ] Not started
Phase 6 — Study Features   [ ] Not started
Phase 7 — Advanced         [ ] Not started
```

---

## Current Objective

```text
Start Phase 5 — MVP hardening.
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

### Phase 3 — Core RAG
- Context builder (`app/rag/context.py`): dedupe, relevance order, token budget
  (`CONTEXT_MAX_TOKENS`, default 3000), document/page/section preserved as
  numbered blocks, first chunk always included (truncated if oversized).
- Grounded system prompt (`app/rag/prompts.py`): context is the only knowledge
  source; fixed missing-context sentence; no invented citations; no chain-of-thought.
- Ollama generation (`app/llm/ollama.py`): `chat` (one-shot) + `chat_stream`
  (NDJSON deltas), temperature from `LLM_TEMPERATURE`; clear `OllamaError`s.
- ChatEngine (`app/rag/engine.py`): retrieve → threshold filter
  (`RELEVANCE_THRESHOLD`, default 0.5) → build context → generate.
- `POST /api/chat`: `{answer, evidence, grounded}`; no evidence above threshold →
  fixed missing-context message, `grounded: false`, LLM never called;
  LLM failure → friendly 503, no stack traces.
- `POST /api/chat/stream`: SSE events `meta` (evidence first) → `token`* → `done`,
  or `error` on failure; no-evidence path emits `meta` + `done` without tokens.
- Citations/evidence are assembled by backend code only; the LLM answers from
  numbered context blocks `[1] [2] ...`.
- New config: `RELEVANCE_THRESHOLD` (0.5, calibrated against measured score gap:
  related ≥ 0.55, unrelated ≤ 0.49), `CONTEXT_MAX_TOKENS` (3000).

### Phase 4 — Chat UI
- `frontend/src/types/chat.ts`: evidence/chat request-response/SSE event types.
- `frontend/src/lib/chat.ts`: `streamChat` — fetch POST to `/api/chat/stream`,
  incremental SSE parsing (`\n\n` frames, `data:` lines), user-safe `ApiError`s,
  abort support (AbortController stops reading without an error).
- `frontend/src/pages/Chat.tsx` (full rewrite):
  - Conversation message list (user bubbles right with filter chips, assistant
    answers left, auto-scroll), empty state, Clear button.
  - Composer: textarea (Enter sends, Shift+Enter newline, 2000 max),
    subject / semester / document filters populated from indexed documents,
    Send ↔ Stop (aborts the in-flight stream; partial answer is kept).
  - Streaming states: "Searching your library…" → "Reviewing sources…" →
    token-by-token render with caret → final.
  - Grounding states (per docs/UI.md): ✓ "Answered from your study material"
    (top relevance ≥ 0.55), ⚠ "partially covers" (0.50–0.55 band),
    ○ "couldn't find enough information" (grounded=false), red friendly error box.
  - Source cards under "Supported by": numbered `[1] …` matching the prompt's
    context blocks, filename · page · section · relevance %, hover "View source".
  - Source detail dialog (shadcn/ui): page/section/relevance + full retrieved
    chunk text (scrollable).
- `ollama_timeout_s` raised 60 → 180 s: a cold Ollama model load (first call
  after idle) exceeded 60 s and produced `httpx.ReadTimeout`; the stream now
  waits for generation instead of failing.
- Verified live through the Vite dev proxy against real llama3.2:3b, driven by
  headless Chrome (CDP): streamed Docker answer with ✓ badge + source card,
  source dialog with page/section/55.5% relevance + chunk text, unrelated
  question → missing-context answer with ○ badge and no LLM call, streaming
  error path shows friendly `LLM_UNAVAILABLE` detail.
- Frontend verification: `npm run build` (tsc strict caught a null-dialog bug)
  + `npm run lint` clean (pre-existing warnings only); 150/150 backend tests.

---

## In Progress

- Nothing yet.

---

## Remaining

- Phase 5+ requirements (MVP hardening, study features, advanced retrieval).

---

## Files/Components Implemented

```text
Backend
  app/main.py                      app factory, CORS, upload size guard, routers
  app/core/config.py               settings (env-driven)
  app/database/mongo.py            connection wrapper
  app/database/repositories.py     DocumentRepository, ChunkRepository + indexes
  app/llm/ollama.py                Ollama adapter: health, chat, chat_stream, get_llm_provider
  app/api/routes/health.py         GET /api/health
  app/api/routes/documents.py      upload/list/detail/chunks/delete
  app/api/routes/search.py         POST /api/search
  app/api/routes/chat.py           POST /api/chat + /api/chat/stream (SSE)
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
  app/rag/prompts.py               grounded system prompt + message builder
  app/rag/context.py               context dedupe/budget/truncation
  app/rag/engine.py                ChatEngine: retrieve → threshold → generate
  app/models/health.py, document.py, evidence.py, chat.py

Frontend
  frontend/src/pages/Chat.tsx        chat: message list, composer, streaming, sources, dialogs
  frontend/src/pages/Documents.tsx  upload, table, filters, detail + delete dialogs
  frontend/src/pages/Dashboard.tsx  stats + recent documents
  frontend/src/types/document.ts    API types
  frontend/src/types/chat.ts        chat request/response/evidence/SSE types
  frontend/src/lib/api.ts           apiFetch + apiUpload (safe error messages)
  frontend/src/lib/chat.ts          streamChat (SSE parser, abort support)
  frontend/src/components/ui/{select,table,...}.tsx
```

---

## Tests

```text
Tests written: 150
Tests passing: 150
Tests failing: 0
```

Covers: validation, hashing, cleaning, section heuristics, chunking, all four parsers,
repositories (live MongoDB), document API end-to-end (upload/duplicate/filters/chunks/delete/stats),
config, health endpoint, Ollama adapter (health + chat + streaming), live infrastructure,
embedding provider (MockTransport: batching, legacy fallback, error mapping), vector store
(live MongoDB: cosine math, ranking, top_k, metadata filters, auto-fallback), retriever
(evidence ids, filter pass-through, relevance clamping), search API (evidence shape, ranking,
subject/semester/document filters, validation, safe 503), context builder (dedupe/budget/
truncation), grounded prompts, chat engine (threshold/filters/generation), chat API
(grounded answers, missing-context without LLM call, safe 503s, SSE event order).

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
- Grounding is enforced twice: evidence below `RELEVANCE_THRESHOLD` never reaches the
  prompt, and the system prompt restricts answers to the supplied context with a fixed
  missing-context sentence.

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
- Phase 2 committed and pushed (`538cb42`).
- Phase 3 verified live with real llama3.2:3b: `POST /api/chat` answered a Docker
  question grounded in the uploaded PDF (evidence with pages + relevance 0.47–0.57,
  `grounded: true`); unrelated question → missing-context message; `POST /api/chat/stream`
  emitted meta → token → done events and streamed `docker rmi <image_name>`.
- `RELEVANCE_THRESHOLD` raised 0.4 → 0.5 after measuring score separation on 10
  questions (related top scores 0.555–0.654, unrelated 0.402–0.487). Battery re-run:
  7/7 related questions grounded with correct Docker answers, 3/3 unrelated rejected
  at retrieval (evidence=[], grounded=false, no LLM call, ~4.7s).
- Phase 4 verified live in a real browser (headless Chrome + CDP): question →
  streamed tokens → ✓ badge + "Supported by" source card → source dialog
  (page/section/relevance/full chunk text); unrelated question → ○
  missing-context state; SSE error events surface the friendly backend detail.
- Fixed during Phase 4 verification: dialog evaluated `sourceLocation(null)`
  during render (crashed the whole page — `tsc`'s non-null assertion hid it);
  stream error detail was overwritten by the client's "connection ended
  unexpectedly" fallback; grounding partial-support boundary corrected from
  0.65 → 0.55 to match measured corpus scores; Ollama timeout 60 → 180 s.

---

## Last Completed Task

```text
Phase 4 acceptance verified: chat UI streams grounded answers with source cards
and detail dialog in a real browser (both grounding states), Stop/Clear/filters
work, build + lint + 150/150 tests pass, ROADMAP + CURRENT_STATE updated.
```

---

## Next Task

```text
Start Phase 5 — MVP hardening.
Read docs/ROADMAP.md Phase 5: error handling, security checks, performance
improvements, RAG evaluation, integration tests, documentation, clean
installation process.
```

---

## Last Updated

```text
2026-10-09 (Phase 4 — Chat UI: COMPLETED)
```
