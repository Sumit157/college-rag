"""Grounded prompting: context formatting and chat message construction.

The system prompt makes the context the only permitted knowledge source; the
backend (never the LLM) numbers sources and owns citation metadata.
"""

from __future__ import annotations

from app.models.evidence import Evidence

MISSING_CONTEXT_MESSAGE = (
    "I couldn't find enough information about this in the uploaded study material."
)

SYSTEM_PROMPT = """You are a study assistant for a college student's uploaded study material.

Strict rules:
- The context below is your ONLY knowledge source. Never answer from outside knowledge.
- If the context does not contain the answer, reply exactly: "I couldn't find enough information about this in the uploaded study material."
- Be concise and clear; write answers the student can revise from quickly.
- Never invent filenames, page numbers, sections, or sources.
- When you refer to a source, use only its context number, for example [1].
- Do not reveal your reasoning process; give the final answer directly."""


def format_context(evidence: list[Evidence]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(evidence, start=1):
        header = f"[{index}] {item.filename}"
        if item.page is not None:
            header += f" | page {item.page}"
        if item.section:
            header += f" | section {item.section}"
        blocks.append(f"{header}\n{item.text}")
    return "\n\n".join(blocks)


def build_messages(question: str, evidence: list[Evidence]) -> list[dict]:
    context = format_context(evidence)
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
