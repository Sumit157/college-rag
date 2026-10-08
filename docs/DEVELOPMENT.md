# Development

## Phase-based workflow

The project must be built like a sequence of working milestones.

For each phase:

1. Read the phase requirements.
2. Inspect the current implementation.
3. Implement only that phase.
4. Run tests.
5. Manually verify the user flow.
6. Fix issues.
7. Update documentation.
8. Only then begin the next phase.

Do not implement future-phase features early.

## Setup

```bash
python -m venv .venv
pip install -r requirements.txt
```

Configure `.env`:

```env
MONGODB_URI=<mongodb-connection-string>
MONGODB_DATABASE=college_rag
LLM_MODEL=<ollama-model>
EMBEDDING_MODEL=<embedding-model>
LLM_TEMPERATURE=0.2
```

Install/run Ollama separately.

## Frontend components

Install shadcn/ui components as needed:

```bash
cd frontend
npx shadcn@latest add button card input textarea dialog badge separator skeleton scroll-area alert
```

## Run backend

```bash
uvicorn app.main:app --reload
```

Run the frontend using the project's configured npm command.

## Development rule

Never move forward with known failing tests or broken core flows.
