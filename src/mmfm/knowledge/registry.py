"""
Document registry for knowledge base provenance tracking.

Tracks all ingested documents: source file, type, chunk count,
checksum, and metadata. Persists to knowledge_base/registry.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from mmfm.config import KNOWLEDGE_BASE_DIR

REGISTRY_FILE = KNOWLEDGE_BASE_DIR / "registry.json"


def _load_registry() -> dict:
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"documents": [], "last_updated": None, "total_chunks": 0}


def _save_registry(registry: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    registry["last_updated"] = datetime.now(timezone.utc).isoformat()
    registry["total_chunks"] = sum(
        doc.get("chunk_count", 0) for doc in registry.get("documents", [])
    )
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2)


def register_document(
    doc_id: str,
    source_file: str,
    doc_type: str,
    chunk_count: int,
    checksum: str,
    language: str = "en",
    topics: Optional[list[str]] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Add or update a document entry in the registry.

    Args:
        doc_id: Unique document identifier (e.g., "pemba_report_001")
        source_file: Path to the source file
        doc_type: "pdf" | "docx" | "xlsx" | "csv"
        chunk_count: Number of chunks generated
        checksum: SHA-256 checksum of the file
        language: ISO language code (e.g., "en", "pt")
        topics: List of topic tags
        metadata: Additional metadata dict

    Returns:
        The registry entry dict
    """
    registry = _load_registry()

    entry = {
        "doc_id": doc_id,
        "source_file": source_file,
        "doc_type": doc_type,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": chunk_count,
        "language": language,
        "topics": topics or [],
        "checksum": checksum,
        "metadata": metadata or {},
    }

    # Update if exists, append if new
    existing = [d for d in registry["documents"] if d["doc_id"] == doc_id]
    if existing:
        idx = registry["documents"].index(existing[0])
        registry["documents"][idx] = entry
    else:
        registry["documents"].append(entry)

    _save_registry(registry)
    return entry


def get_document(doc_id: str) -> Optional[dict]:
    """Return a single document entry by ID, or None if not found."""
    registry = _load_registry()
    for doc in registry["documents"]:
        if doc["doc_id"] == doc_id:
            return doc
    return None


def get_all_documents() -> list[dict]:
    """Return all registered documents."""
    return _load_registry().get("documents", [])


def get_all_source_names() -> set[str]:
    """Return set of all source file basenames (for provenance checks)."""
    docs = get_all_documents()
    return {Path(d["source_file"]).name for d in docs}


def is_registered(source_file: str, checksum: str) -> bool:
    """Check if a file with this checksum is already in the registry."""
    docs = get_all_documents()
    for doc in docs:
        if doc["source_file"] == source_file and doc["checksum"] == checksum:
            return True
    return False


def get_registry_status() -> dict:
    """Return summary statistics about the knowledge base."""
    registry = _load_registry()
    docs = registry.get("documents", [])
    by_type: dict[str, int] = {}
    for doc in docs:
        t = doc.get("doc_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_documents": len(docs),
        "total_chunks": registry.get("total_chunks", 0),
        "last_updated": registry.get("last_updated"),
        "by_type": by_type,
        "documents": [{"doc_id": d["doc_id"], "source_file": d["source_file"], "chunk_count": d["chunk_count"]} for d in docs],
    }
