"""
ChromaDB vector store indexer for RAG.

Embeds document chunks and stores them in a local ChromaDB collection.
Uses sentence-transformers or OpenAI-compatible embeddings.
No data is sent to external APIs during indexing (local embeddings only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mmfm.config import KNOWLEDGE_BASE_DIR
from mmfm.knowledge.chunker import DocumentChunk

CHROMA_DIR = KNOWLEDGE_BASE_DIR / "embeddings"
COLLECTION_NAME = "mmfm_knowledge_base"

# Embedding model — uses ChromaDB's default (sentence-transformers, local)
# This runs entirely locally; no API calls are made during embedding.
DEFAULT_EMBEDDING_FUNCTION = None  # Uses ChromaDB default (all-MiniLM-L6-v2)


def _get_client():
    """Get or create ChromaDB persistent client."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _get_collection(client=None):
    """Get or create the MMFM knowledge base collection."""
    if client is None:
        client = _get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "MMFM Analyzer knowledge base — municipal market documents"},
    )


def index_chunks(chunks: list[DocumentChunk], batch_size: int = 50) -> int:
    """
    Add document chunks to the ChromaDB vector store.

    Chunks are deduplicated by chunk_id — re-indexing a document
    will overwrite existing chunks with the same IDs.

    Args:
        chunks: List of DocumentChunk objects to index
        batch_size: Number of chunks to add per batch (memory management)

    Returns:
        Number of chunks successfully indexed
    """
    if not chunks:
        return 0

    collection = _get_collection()
    indexed = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        ids = [c.chunk_id for c in batch]
        documents = [c.text for c in batch]
        metadatas = [
            {
                "doc_id": c.doc_id,
                "source_file": c.source_file,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
                "page_numbers": json.dumps(c.page_numbers),
                "section_heading": c.section_heading or "",
            }
            for c in batch
        ]

        # Upsert: add or update existing
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        indexed += len(batch)

    return indexed


def delete_document_chunks(doc_id: str) -> int:
    """Remove all chunks for a given document from the vector store."""
    collection = _get_collection()
    results = collection.get(where={"doc_id": doc_id})
    if results and results["ids"]:
        collection.delete(ids=results["ids"])
        return len(results["ids"])
    return 0


def get_collection_stats() -> dict:
    """Return statistics about the indexed collection."""
    try:
        collection = _get_collection()
        count = collection.count()
        return {"total_chunks": count, "collection_name": COLLECTION_NAME}
    except Exception as exc:
        return {"total_chunks": 0, "error": str(exc)}
