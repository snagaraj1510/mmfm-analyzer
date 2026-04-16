"""Tests for document registry."""

from __future__ import annotations

import json
import pytest
from pathlib import Path


@pytest.fixture
def temp_registry(tmp_path, monkeypatch):
    """Redirect registry to a temp dir for testing."""
    import mmfm.knowledge.registry as reg_module
    temp_file = tmp_path / "registry.json"
    monkeypatch.setattr(reg_module, "REGISTRY_FILE", temp_file)
    return temp_file


class TestRegistry:
    def test_register_document(self, temp_registry):
        from mmfm.knowledge.registry import register_document, get_document

        entry = register_document(
            doc_id="test_doc_001",
            source_file="resources/reports/test.pdf",
            doc_type="pdf",
            chunk_count=25,
            checksum="sha256:abc123",
            language="en",
            topics=["finance", "east_africa"],
        )
        assert entry["doc_id"] == "test_doc_001"
        assert entry["chunk_count"] == 25

        retrieved = get_document("test_doc_001")
        assert retrieved is not None
        assert retrieved["doc_id"] == "test_doc_001"

    def test_get_nonexistent_document_returns_none(self, temp_registry):
        from mmfm.knowledge.registry import get_document
        assert get_document("nonexistent_doc") is None

    def test_update_existing_document(self, temp_registry):
        from mmfm.knowledge.registry import register_document, get_document

        register_document("doc_001", "file.pdf", "pdf", 10, "sha256:aaa")
        register_document("doc_001", "file.pdf", "pdf", 20, "sha256:bbb")

        doc = get_document("doc_001")
        assert doc["chunk_count"] == 20  # Updated
        assert doc["checksum"] == "sha256:bbb"

    def test_is_registered_check(self, temp_registry):
        from mmfm.knowledge.registry import register_document, is_registered

        register_document("doc_001", "file.pdf", "pdf", 10, "sha256:abc")

        assert is_registered("file.pdf", "sha256:abc") is True
        assert is_registered("file.pdf", "sha256:different") is False
        assert is_registered("other.pdf", "sha256:abc") is False

    def test_get_all_source_names(self, temp_registry):
        from mmfm.knowledge.registry import register_document, get_all_source_names

        register_document("doc_001", "resources/reports/report_a.pdf", "pdf", 10, "sha256:aaa")
        register_document("doc_002", "resources/reports/report_b.pdf", "pdf", 15, "sha256:bbb")

        names = get_all_source_names()
        assert "report_a.pdf" in names
        assert "report_b.pdf" in names

    def test_registry_status_totals(self, temp_registry):
        from mmfm.knowledge.registry import register_document, get_registry_status

        register_document("doc_001", "file_a.pdf", "pdf", 10, "sha256:aaa")
        register_document("doc_002", "file_b.docx", "docx", 5, "sha256:bbb")

        status = get_registry_status()
        assert status["total_documents"] == 2
        assert status["total_chunks"] == 15
        assert status["by_type"]["pdf"] == 1
        assert status["by_type"]["docx"] == 1
