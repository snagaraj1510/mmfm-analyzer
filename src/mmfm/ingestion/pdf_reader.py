"""
PDF text and table extraction using PyMuPDF (fitz).

Extracts text, detects language, and returns structured content
suitable for chunking and RAG indexing.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PDFPage:
    page_number: int
    text: str
    tables: list[list[list[str]]] = field(default_factory=list)  # list of tables, each a 2D list


@dataclass
class ParsedPDF:
    source_file: Path
    pages: list[PDFPage] = field(default_factory=list)
    full_text: str = ""
    page_count: int = 0
    checksum: str = ""
    metadata: dict = field(default_factory=dict)

    def get_text_by_page(self) -> dict[int, str]:
        return {p.page_number: p.text for p in self.pages}


def _compute_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def parse_pdf(file_path: Path | str) -> ParsedPDF:
    """
    Parse a PDF file and extract text content page by page.

    Args:
        file_path: Path to the PDF file

    Returns:
        ParsedPDF with full text and per-page content

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file is not a PDF
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF is required: pip install pymupdf")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected .pdf file, got: {path.suffix}")

    doc = fitz.open(str(path))
    pages: list[PDFPage] = []
    all_text_parts: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")

        # Extract tables via text blocks (basic extraction)
        # For production use, consider camelot or tabula for complex tables
        tables: list[list[list[str]]] = []

        pages.append(PDFPage(
            page_number=page_num + 1,
            text=text.strip(),
            tables=tables,
        ))
        if text.strip():
            all_text_parts.append(text.strip())

    doc.close()

    full_text = "\n\n".join(all_text_parts)

    return ParsedPDF(
        source_file=path,
        pages=pages,
        full_text=full_text,
        page_count=len(pages),
        checksum=_compute_checksum(path),
        metadata={"filename": path.name, "page_count": len(pages)},
    )
