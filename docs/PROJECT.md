# Project

## Goal

Build a local-first college study assistant that indexes uploaded material and answers questions using a local LLM.

The defining rule is:

> **The assistant must answer according to uploaded documents only.**

If the uploaded material does not contain enough evidence, it must say so rather than fill the gap from general model knowledge.

## MVP

### Must have
- PDF, DOCX, PPTX and TXT ingestion
- Subject and semester metadata
- MongoDB document and chunk storage
- MongoDB vector search
- Local embeddings
- Ollama generation
- Grounded chat
- Evidence/source citations
- Document management
- Dashboard, Documents, Chat and Settings
- Basic RAG evaluation

### Explicitly out of MVP
- Authentication
- Multi-user support
- OCR
- PYQ analysis
- Quizzes
- Flashcards
- Study plans
- Progress tracking
- Agents
- Web search
- Fine-tuning
- Cloud LLM APIs
- Advanced hybrid retrieval

## Phased development

Build and validate the system phase-by-phase. A phase is complete only when its acceptance criteria pass.

Do not implement later features merely because the architecture could support them.
