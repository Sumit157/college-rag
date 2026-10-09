"""Context construction: deduplicate, order, and fit the model's budget.

Rules (docs/RAG.md): remove duplicate chunks, prefer high-relevance evidence,
preserve document/page boundaries, keep context within the model limit.
"""

from __future__ import annotations

from app.models.evidence import Evidence

HEADER_TOKENS = 10


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _block_tokens(item: Evidence) -> int:
    # crude estimate for the "[n] file | page | section" header + text
    return len(item.text) // 4 + HEADER_TOKENS


def _truncate_to_tokens(item: Evidence, token_budget: int) -> Evidence:
    max_chars = max(4, token_budget * 4)
    if len(item.text) <= max_chars:
        return item
    return item.model_copy(update={"text": item.text[:max_chars].rstrip() + " ..."})


def build_context(evidence: list[Evidence], max_tokens: int) -> list[Evidence]:
    """Return deduplicated evidence that fits the token budget.

    Evidence is assumed to arrive in relevance order. The first chunk is always
    included (truncated when it alone exceeds the budget) so an answer attempt
    is never handed an empty context.
    """
    selected: list[Evidence] = []
    seen: set[str] = set()
    used = 0
    for item in evidence:
        key = _normalize(item.text)
        if not key or key in seen:
            continue
        seen.add(key)
        tokens = _block_tokens(item)
        if selected and used + tokens > max_tokens:
            continue
        if not selected and tokens > max_tokens:
            item = _truncate_to_tokens(item, max_tokens)
            tokens = _block_tokens(item)
        selected.append(item)
        used += tokens
    return selected
