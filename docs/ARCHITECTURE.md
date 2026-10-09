# Architecture

```text
                    React UI
                       |
              shadcn + ReactBits
                       |
                    FastAPI
                       |
                  RAG Engine
        ┌──────────────┼──────────────┐
        |              |              |
    Retriever     Evidence/Context   Ollama
        |            Builder            |
        |              |                |
        └──────────────┴───────┐        |
                               ▼        |
                            MongoDB ◄───┘
                               |
                  Documents + Chunks
                  Metadata + Vectors
```

## Core components

- **Frontend:** React, shadcn/ui and selected ReactBits Pro components.
- **API:** FastAPI.
- **Ingestion:** validate → parse → clean → chunk → embed → store.
- **Retriever:** MongoDB vector search with metadata filters; uses Atlas `$vectorSearch`
  when available, otherwise scores cosine similarity in-process (standalone MongoDB).
- **Evidence layer:** preserves retrieved chunks and source metadata separately from generated text.
- **RAG engine:** retrieve → validate evidence → build context → generate → attach citations.
- **LLM adapter:** Ollama.
- **MongoDB:** application records, chunks, embeddings and future study data.

## Important separation

The LLM must never be the source of citation metadata.

```text
Retrieved chunks
      |
      +----> Evidence objects ----------------> UI source cards
      |
      +----> Context --------------------------> Local LLM
                                                   |
                                                   ▼
                                                Answer
```

The application owns evidence and citations. The LLM only generates the answer from supplied context.

## Interfaces

Keep these replaceable:

```text
VectorStore
  └── MongoVectorStore

LLMProvider
  └── OllamaProvider

EmbeddingProvider
  └── LocalEmbeddingProvider
```
