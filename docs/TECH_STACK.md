# Tech Stack

| Layer | Choice |
|---|---|
| Language | Python |
| Backend | FastAPI |
| Frontend | React + Vite |
| UI | shadcn/ui + ReactBits Pro |
| Database | MongoDB |
| Vector search | MongoDB Vector Search |
| Local LLM | Ollama |
| Embeddings | Configurable local embedding model |
| PDF | PyMuPDF |
| DOCX | python-docx |
| PPTX | python-pptx |
| Testing | pytest |

## Frontend components

Use shadcn/ui components as the UI foundation (installed via the shadcn CLI):

```bash
npx shadcn@latest add button card input textarea dialog badge separator skeleton scroll-area alert
```

Note: ReactBits Pro components (`chat-1`, `prompt-input-3`, `app-dialog-7`) were
evaluated during Phase 0 but dropped from the MVP — the registry requires a paid
license key. Equivalent behaviour is built with shadcn/ui components
(`dialog` for source/confirmation dialogs, `textarea`/`input` for the question
composer, and a custom evidence-first message list for chat).

## Principles
- Local-first
- Lightweight
- Evidence-grounded
- Modular
- Configurable
- Easy to test
