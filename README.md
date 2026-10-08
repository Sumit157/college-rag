# College RAG

A local-first RAG assistant for college documents and study material.

## Stack
- Python + FastAPI
- React + Vite + TypeScript
- shadcn/ui
- MongoDB for application data and vector search
- Ollama for local LLM generation
- Local embedding model

## Core promise

The assistant answers **only from uploaded college material**. Retrieved evidence is kept separate from the generated answer so the UI can show exactly which document context supports each answer.

## Development

The project is built in explicit phases. Each phase has a working checkpoint before the next phase begins.

**Before starting work, read `CURRENT_STATE.md`** — it records the current phase, verified progress and next task.

See:
- `CURRENT_STATE.md`
- `docs/PROJECT.md`
- `docs/ARCHITECTURE.md`
- `docs/UI.md`
- `docs/RAG.md`
- `docs/ROADMAP.md`

## Quick start

### Prerequisites

- Python 3.12+
- Node.js 20+
- MongoDB running locally (default `mongodb://localhost:27017`)
- Ollama running locally (default `http://localhost:11434`) with an instruct model pulled

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then adjust model names if needed
uvicorn app.main:app --reload
```

Verify: `GET http://localhost:8000/api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000`
(override with the `VITE_API_PROXY_TARGET` environment variable).

### Tests

```bash
pytest
```
