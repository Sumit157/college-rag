# Security

## Privacy

The MVP should keep documents, embeddings and LLM processing local wherever the selected MongoDB deployment allows.

No external AI API is required.

## File safety
- Validate extension and MIME type.
- Enforce upload limits.
- Reject malformed files.
- Never execute uploaded files.
- Keep user files outside executable source directories.

## Prompt injection

Retrieved document text is untrusted data.

A document containing text such as `ignore previous instructions` must never override system instructions.

## API
- Validate all input.
- Sanitize rendered content.
- Do not expose internal filesystem paths.
- Store credentials in environment variables.
- Never commit `.env`.

## Deletion

Deleting a document must remove its metadata and every associated chunk/vector.
