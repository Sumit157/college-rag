# Local LLM

## Runtime

Use Ollama for local generation.

## Configuration

```env
LLM_MODEL=<local-model>
EMBEDDING_MODEL=<local-embedding-model>
LLM_TEMPERATURE=0.2
```

## Generation rules

The model receives:
- system instructions
- user question
- selected document context

The system prompt must explicitly state that context is the only knowledge source for the answer.

## Missing evidence

If the context cannot support an answer, the model must state that the uploaded material does not contain enough information.

## Reasoning

Allow the model to reason internally about the supplied evidence, but never expose chain-of-thought. Return only:
- final answer
- concise supporting explanation when useful
- application-generated evidence/citations

## Requirements

The adapter should support:
- generation
- streaming
- temperature
- context configuration
- health/model checks
- clear errors
