"""Grounded prompting: context formatting and chat message construction.

The system prompt makes the context the only permitted knowledge source; the
backend (never the LLM) numbers sources and owns citation metadata.
"""

from __future__ import annotations

from app.models.evidence import Evidence

MISSING_CONTEXT_MESSAGE = (
    "I couldn't find enough information about this in the uploaded study material."
)

# Historical answers are replayed for follow-up questions; cap them so a long
# conversation cannot crowd out the current context.
HISTORY_ANSWER_MAX_CHARS = 2000

SYSTEM_PROMPT = """You are a study assistant for a college student's uploaded study material.

Strict rules:
- The context below is your ONLY knowledge source. Never answer from outside knowledge.
- Earlier conversation turns are previous questions and your own earlier grounded answers; use them to understand follow-up questions, but every fact must still come from the context below or those earlier answers.
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


def build_messages(
    question: str,
    evidence: list[Evidence],
    history: list[dict] | None = None,
) -> list[dict]:
    """Build chat messages; `history` is prior turns as {question, answer}."""
    context = format_context(evidence)
    user = f"Context:\n{context}\n\nQuestion: {question}"
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history or []:
        prior_question = str(turn.get("question", "")).strip()
        prior_answer = str(turn.get("answer", ""))[:HISTORY_ANSWER_MAX_CHARS].strip()
        if not prior_question or not prior_answer:
            continue
        messages.append({"role": "user", "content": prior_question})
        messages.append({"role": "assistant", "content": prior_answer})
    messages.append({"role": "user", "content": user})
    return messages
