# Testing

## Unit tests

Cover:
- parsers
- cleaning
- chunking
- metadata
- file hashing
- MongoDB repositories
- vector retrieval
- evidence construction
- prompt construction
- API validation
- citation generation

## Integration test

```text
upload
→ parse
→ chunk
→ embed
→ MongoDB
→ retrieve evidence
→ Ollama
→ answer
→ citations
```

## RAG evaluation

Maintain a small trusted dataset:

```text
question
expected document
expected page
expected facts
```

Measure:
- retrieval accuracy
- evidence relevance
- citation accuracy
- answer faithfulness
- unsupported-answer rate
- latency

## Important acceptance test

Ask questions whose answers are deliberately absent from the uploaded documents.

The assistant must refuse to invent an answer.

## Reasoning evaluation

Evaluate the final answer against retrieved evidence, not hidden chain-of-thought. The goal is correct, document-supported reasoning, not exposing private reasoning traces.
