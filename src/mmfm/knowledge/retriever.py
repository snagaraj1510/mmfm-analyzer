"""
RAG retrieval logic for MMFM Analyzer.

Queries the ChromaDB vector store to retrieve relevant document chunks
for context-enriched financial analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from mmfm.knowledge.indexer import _get_collection


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_id: str
    source_file: str
    text: str
    distance: float          # Lower = more relevant
    chunk_index: int
    token_count: int = 0
    page_numbers: list[int] = field(default_factory=list)
    section_heading: Optional[str] = None


@dataclass
class RetrievalResult:
    query: str
    chunks: list[RetrievedChunk] = field(default_factory=list)
    total_tokens: int = 0

    def format_context(self, max_tokens: int = 4000) -> str:
        """
        Format retrieved chunks into a context string for Claude.

        Includes source attribution for each chunk (anti-hallucination).
        """
        parts = []
        token_budget = max_tokens
        for chunk in self.chunks:
            if chunk.token_count <= token_budget:
                source = chunk.source_file.split("/")[-1].split("\\")[-1]
                page_ref = f" (p.{','.join(str(p) for p in chunk.page_numbers)})" if chunk.page_numbers else ""
                heading_ref = f" — {chunk.section_heading}" if chunk.section_heading else ""
                parts.append(f"[SOURCE: {source}{page_ref}{heading_ref}]\n{chunk.text}")
                token_budget -= chunk.token_count
            if token_budget <= 0:
                break
        return "\n\n---\n\n".join(parts)

    @property
    def source_files(self) -> list[str]:
        """Unique source files referenced in retrieved chunks."""
        seen = []
        for chunk in self.chunks:
            if chunk.source_file not in seen:
                seen.append(chunk.source_file)
        return seen


def retrieve(
    query: str,
    n_results: int = 5,
    doc_id_filter: Optional[str] = None,
    min_relevance: float = 1.5,  # ChromaDB L2 distance threshold
) -> RetrievalResult:
    """
    Retrieve the most relevant chunks for a query.

    Args:
        query: Natural language query string
        n_results: Number of chunks to retrieve
        doc_id_filter: Restrict retrieval to a specific document
        min_relevance: Maximum L2 distance to include (filter out irrelevant chunks)

    Returns:
        RetrievalResult with ranked chunks and formatted context
    """
    try:
        collection = _get_collection()
    except Exception:
        # If collection doesn't exist yet, return empty result
        return RetrievalResult(query=query)

    where = {"doc_id": doc_id_filter} if doc_id_filter else None

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, max(collection.count(), 1)),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return RetrievalResult(query=query)

    retrieval = RetrievalResult(query=query)

    if not results or not results.get("ids"):
        return retrieval

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    import json as _json
    for chunk_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        if dist > min_relevance:
            continue

        page_nums_raw = meta.get("page_numbers", "[]")
        try:
            page_nums = _json.loads(page_nums_raw)
        except (ValueError, TypeError):
            page_nums = []

        chunk = RetrievedChunk(
            chunk_id=chunk_id,
            doc_id=meta.get("doc_id", ""),
            source_file=meta.get("source_file", ""),
            text=text,
            distance=dist,
            chunk_index=meta.get("chunk_index", 0),
            page_numbers=page_nums,
            section_heading=meta.get("section_heading") or None,
        )
        # Estimate token count
        chunk.token_count = meta.get("token_count", len(text.split()) * 4 // 3)
        retrieval.chunks.append(chunk)
        retrieval.total_tokens += chunk.token_count

    return retrieval


def retrieve_for_context(
    query: str,
    max_tokens: int = 4000,
    n_results: int = 8,
) -> str:
    """
    Convenience wrapper: retrieve chunks and return formatted context string.
    Used directly in AI narrative prompts.
    """
    result = retrieve(query, n_results=n_results)
    return result.format_context(max_tokens=max_tokens)
