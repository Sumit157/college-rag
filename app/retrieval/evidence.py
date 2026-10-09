"""Build evidence objects from scored chunks.

Evidence is owned by the backend: the model never invents document ids, pages
or sections, and every piece of context handed to the LLM keeps its source.
"""

from __future__ import annotations

from app.models.evidence import Evidence
from app.retrieval.vector_store import ScoredChunk


def build_evidence(chunks: list[ScoredChunk]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for index, chunk in enumerate(chunks, start=1):
        relevance = min(max(chunk.score, 0.0), 1.0)
        evidence.append(
            Evidence(
                id=f"evidence-{index}",
                document_id=chunk.document_id,
                filename=chunk.filename,
                page=chunk.page,
                section=chunk.section,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                relevance=round(relevance, 4),
            )
        )
    return evidence
