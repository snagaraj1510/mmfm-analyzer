"""Tests for PDF reader."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile


class TestPDFReader:
    def test_file_not_found_raises(self):
        from mmfm.ingestion.pdf_reader import parse_pdf
        with pytest.raises(FileNotFoundError):
            parse_pdf(Path("/nonexistent/file.pdf"))

    def test_wrong_extension_raises(self, tmp_path):
        from mmfm.ingestion.pdf_reader import parse_pdf
        bad_file = tmp_path / "test.txt"
        bad_file.write_text("hello")
        with pytest.raises(ValueError, match="Expected .pdf"):
            parse_pdf(bad_file)

    def test_parses_real_pdf(self, tmp_path):
        """Create a minimal PDF and verify it parses."""
        pytest.importorskip("fitz")
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Municipal Market Financial Analysis\nRevenue: $500,000\nOccupancy: 70%")
        pdf_path = tmp_path / "test_market.pdf"
        doc.save(str(pdf_path))
        doc.close()

        from mmfm.ingestion.pdf_reader import parse_pdf
        result = parse_pdf(pdf_path)
        assert result.page_count == 1
        assert "Municipal Market" in result.full_text
        assert result.checksum.startswith("sha256:")
        assert result.source_file == pdf_path
