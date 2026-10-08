# Current State

This file is the **single source of truth for the current implementation state of the project**.

It must always reflect what has actually been implemented, tested and verified.

The AI coding agent MUST read this file before starting work and MUST update it whenever meaningful implementation work is completed.

---

## Current Phase

```text
Phase: 0
Name: Foundation
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
Phase 1 — Ingestion        [ ] Not started
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
Start Phase 1 — Document Ingestion.
```

---

## Completed

- Repository structure (`app/`, `frontend/`, `tests/`, `data/`, `docs/`, `prompts/`).
- Environment configuration (`.env.example`, `app/core/config.py` via pydantic-settings).
- FastAPI skeleton (`app/main.py`) with CORS, lifespan-managed MongoDB connection.
- `GET /api/health` endpoint: MongoDB ping + Ollama health/model check.
- MongoDB connection wrapper (`app/database/mongo.py`).
- Ollama adapter with health, ping, model list and structured health report (`app/llm/ollama.py`).
- React + Vite + TypeScript frontend scaffold with Tailwind v4 and shadcn/ui (radix style).
- shadcn/ui components installed: button, card, input, textarea, dialog, badge, separator, skeleton, scroll-area, alert.
- Base UI shell: sidebar navigation (Dashboard / Documents / Chat / Settings), four pages with empty states, live system-status panels.
- Frontend API client (`src/lib/api.ts`), health hook (`src/hooks/useHealth.ts`), Vite dev proxy to the backend.
- Backend test suite (16 tests) covering config, health endpoint, Ollama adapter and live infrastructure checks.

---

## In Progress

- Nothing yet.

---

## Remaining

- Phase 1 requirements (upload, validation, parsers, chunking, metadata, persistence).

---

## Files/Components Implemented

```text
app/main.py                    FastAPI app factory, CORS, lifespan
app/core/config.py             Settings (env-driven, centralised)
app/database/mongo.py          Mongo wrapper (ping/close, app-wide connection)
app/llm/ollama.py              OllamaProvider (ping, list_models, health)
app/api/routes/health.py       GET /api/health
app/models/health.py           Health response schemas
frontend/                      Vite + React + TS + Tailwind v4 + shadcn/ui
frontend/src/App.tsx           Router (Dashboard/Documents/Chat/Settings)
frontend/src/components/layout/AppShell.tsx
frontend/src/pages/{Dashboard,Documents,Chat,Settings}.tsx
frontend/src/lib/api.ts        Typed fetch helper with safe error messages
frontend/src/hooks/useHealth.ts
tests/test_config.py           4 tests
tests/test_health.py           4 tests
tests/test_ollama.py           6 tests
tests/test_live_infra.py       2 tests (skip-safe)
```

---

## Tests

```text
Tests written: 16
Tests passing: 16
Tests failing: 0
```

Frontend: `npm run build` (tsc + vite) passes, `npm run lint` (oxlint) passes with warnings only.

---

## Known Issues

- Port 8000 on this machine is occupied by an unrelated process; local verification ran the backend on port 8010 with `VITE_API_PROXY_TARGET=http://localhost:8010`. Default config remains 8000 (`uvicorn app.main:app --reload`).
- The shadcn CLI created component files under a literal `@\components` directory on first install (root tsconfig.json lacked path aliases); fixed by adding `paths` to `tsconfig.json` and reinstalling components into `src/components/ui`.

---

## Blockers

```text
None.
```

---

## Architecture Decisions

- MongoDB is the primary database and vector-search store.
- Ollama is the local LLM runtime.
- React + Vite is the frontend.
- FastAPI is the backend.
- RAG answers must be grounded exclusively in uploaded documents.
- **ReactBits Pro components are not used** (user decision, 2026-10-08): the registry requires a paid
  license key. Chat, composer and dialogs are built with shadcn/ui. Docs updated
  (docs/TECH_STACK.md, docs/UI.md, docs/ROADMAP.md, docs/DEVELOPMENT.md, README.md).
- Backend uses synchronous pymongo wrapped with `run_in_threadpool` in async routes (kept simple; revisit if needed).

---

## Recent Progress

- Phase 0 scaffolded: FastAPI skeleton + React/Vite skeleton + shadcn/ui.
- Health endpoint verified live: MongoDB `ok`, Ollama `ok` (llama3.2:3b, nomic-embed-text).
- UI shell verified in headless Chrome (Dashboard and Settings render with live data).

---

## Last Completed Task

```text
Phase 0 acceptance verified: backend tests (16/16) pass, frontend builds and
renders, MongoDB and Ollama health checks report ok.
```

---

## Next Task

```text
Start Phase 1 — Document Ingestion.
Read docs/ROADMAP.md Phase 1, then implement upload, validation, hashing,
PDF/DOCX/PPTX/TXT parsing, cleaning, chunking, metadata, MongoDB persistence
and indexing status.
```

---

## Last Updated

```text
2026-10-08
```
