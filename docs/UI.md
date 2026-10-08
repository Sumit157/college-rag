# UI

## Design direction

The UI should feel like a focused study workspace: clean, calm, fast and evidence-first.

### Approved components

Build on shadcn/ui components installed with the shadcn CLI:

```bash
npx shadcn@latest add button card input textarea dialog badge separator skeleton scroll-area alert
```

ReactBits Pro components were dropped from the MVP (paid license required);
the chat, prompt composer and dialogs are built from shadcn/ui primitives
instead of rebuilding equivalents from scratch.

## MVP navigation

```text
Dashboard
Documents
Chat
Settings
```

## Chat

The chat screen is the primary experience.

Use:
- shadcn/ui dialog for the conversation surface, source cards and confirmations.
- `textarea`/`input` for the question composer.
- shadcn/ui dialog for document actions, confirmations and focused source details.

The prompt input should support:
- question text
- subject filter
- semester filter
- optional document filter
- send
- loading/streaming state

## Evidence-first answer UI

Do not display an answer as an unsupported block of text.

Use this structure:

```text
┌─────────────────────────────────────────────┐
│ Assistant                                   │
│                                             │
│ Paging divides memory into fixed-size...   │
│                                             │
│ Supported by                                │
│ ┌─────────────────────────────────────────┐ │
│ │ OS Notes.pdf · Page 42                  │ │
│ │ Memory Management                       │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ Relevant context                            │
│ "Paging divides..."                         │
│                                             │
│ [View source]                               │
└─────────────────────────────────────────────┘
```

The user must be able to see **where the answer came from**.

If possible, clicking a source should open a dialog containing:
- filename
- page
- section
- retrieved text
- relevance information

Do not claim that a source supports an answer unless it was actually retrieved.

## Grounding states

Show clear states:

### Grounded

`✓ Answered from your study material`

### Partially supported

`⚠ The uploaded material only partially covers this`

### Not found

`○ I couldn't find enough information in your uploaded material`

Do not silently answer from general model knowledge.

## Dashboard

Show:
- document count
- subject count
- recent documents
- quick access to Chat

## Documents

Support:
- upload
- subject/semester selection
- indexing progress
- indexed/failed state
- filter
- delete

Use `app-dialog-7` for destructive confirmation and useful document details.

## Visual rules

- Clear typography
- Consistent spacing
- Accessible contrast
- Responsive layout
- Minimal animation
- Obvious loading/error states
- Evidence should be visually distinct from generated text

Avoid a generic AI-chat aesthetic. The product should feel like a study/research tool.
