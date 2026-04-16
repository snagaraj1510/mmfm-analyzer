"""Tests for document chunker."""

from __future__ import annotations

import pytest

from mmfm.knowledge.chunker import chunk_text, DocumentChunk, DEFAULT_CHUNK_TOKENS


class TestChunker:
    def test_empty_text_returns_no_chunks(self):
        chunks = chunk_text("", doc_id="test", source_file="test.pdf")
        assert chunks == []

    def test_short_text_returns_one_chunk(self):
        text = "This is a short municipal market report."
        chunks = chunk_text(text, doc_id="test_001", source_file="test.pdf")
        assert len(chunks) == 1
        assert chunks[0].doc_id == "test_001"
        assert chunks[0].chunk_index == 0

    def test_long_text_produces_multiple_chunks(self):
        # Generate text that exceeds one chunk
        word = "municipal-market-revenue-projections "
        text = word * 200  # Should exceed 500 tokens
        chunks = chunk_text(text, doc_id="test_001", source_file="test.pdf", chunk_tokens=100)
        assert len(chunks) > 1

    def test_chunk_ids_are_unique(self):
        word = "revenue projections data analysis "
        text = word * 300
        chunks = chunk_text(text, doc_id="doc_001", source_file="test.pdf", chunk_tokens=100)
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunk_text_preserves_content(self):
        text = "The occupancy rate is 70 percent. Revenue exceeds projections."
        chunks = chunk_text(text, doc_id="doc_001", source_file="test.pdf")
        full_text = " ".join(c.text for c in chunks)
        assert "occupancy rate" in full_text
        assert "Revenue" in full_text

    def test_chunk_token_count_within_limit(self):
        word = "market revenue capex opex financial "
        text = word * 500
        limit = 100
        chunks = chunk_text(text, doc_id="doc", source_file="test.pdf", chunk_tokens=limit, overlap_tokens=10)
        for chunk in chunks:
            # Each chunk should not exceed limit + some tolerance
            assert chunk.token_count <= limit + 20, f"Chunk {chunk.chunk_id} exceeds token limit"

    def test_page_numbers_propagated(self):
        text = "Revenue analysis for municipal market stall vendors."
        chunks = chunk_text(text, doc_id="doc", source_file="test.pdf", page_numbers=[5, 6])
        assert chunks[0].page_numbers == [5, 6]

    def test_section_heading_propagated(self):
        text = "Operating margin analysis shows improvement over 5 years."
        chunks = chunk_text(text, doc_id="doc", source_file="test.docx", section_heading="Financial Analysis")
        assert chunks[0].section_heading == "Financial Analysis"
