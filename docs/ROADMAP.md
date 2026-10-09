# Roadmap

The project is developed in explicit phases. Each phase must produce a usable, tested result.

## Phase 0 — Foundation
- [x] Repository structure
- [x] Backend/frontend scaffolding
- [x] Environment configuration
- [x] MongoDB connection
- [x] Ollama health check
- [x] Base UI shell
- [x] shadcn/ui components installed

**Checkpoint:** application starts and infrastructure connections work.

## Phase 1 — Document ingestion
- [x] Upload UI
- [x] File validation
- [x] PDF/DOCX/PPTX/TXT parsing
- [x] Cleaning
- [x] Chunking
- [x] Metadata
- [x] Duplicate detection
- [x] MongoDB document/chunk persistence
- [x] Indexing status

**Checkpoint:** a document can be uploaded, indexed and inspected.

## Phase 2 — Retrieval
- [x] Embedding provider
- [x] MongoDB vector index
- [x] Semantic search
- [x] Subject/semester/document filters
- [x] Evidence objects
- [x] Retrieval tests

**Checkpoint:** relevant source chunks can be retrieved reliably.

## Phase 3 — Core RAG
- [x] Context builder
- [x] Grounded system prompt
- [x] Ollama generation
- [x] Evidence-aware answers
- [x] Programmatic citations
- [x] Missing-context behaviour
- [x] Chat API

**Checkpoint:** end-to-end document-grounded Q&A works.

## Phase 4 — Chat UI
- [ ] React chat
- [ ] Conversation message list
- [ ] Question composer with filters
- [ ] Streaming
- [ ] Source cards
- [ ] Source detail dialog (shadcn/ui dialog)
- [ ] Grounding states

**Checkpoint:** students can comfortably ask questions and verify sources.

## Phase 5 — MVP hardening
- [ ] Error handling
- [ ] Security checks
- [ ] Performance improvements
- [ ] RAG evaluation
- [ ] Integration tests
- [ ] Documentation
- [ ] Clean installation process

**Checkpoint:** Core MVP is reliable.

## Phase 6 — Study features
Only after MVP acceptance:
- [ ] PYQ analysis
- [ ] Study mode
- [ ] Quiz generation
- [ ] Summaries
- [ ] Flashcards
- [ ] Exam revision

## Phase 7 — Advanced retrieval/platform
- [ ] Hybrid search
- [ ] Reranking
- [ ] OCR
- [ ] Progress tracking
- [ ] Authentication
- [ ] Multi-user support

Never begin a later phase while the current phase has failing acceptance criteria.
