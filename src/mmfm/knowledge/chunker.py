"""
Document chunking logic for RAG indexing.

Splits documents into ~500-token chunks with configurable overlap.
Uses tiktoken for token counting to stay consistent with Claude's tokenizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tiktoken


DEFAULT_CHUNK_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 50
TOKENIZER_MODEL = "cl100k_base"  # Compatible with Claude's tokenizer family


@dataclass
class DocumentChunk:
    """A single chunk of text from a source document."""
    chunk_id: str                # e.g., "pemba_report_001_chunk_023"
    doc_id: str                  # Parent document ID
    source_file: str             # Original file path
    chunk_index: int             # Index within the document (0-based)
    text: str                    # Chunk text content
    token_count: int             # Approximate token count
    page_numbers: list[int] = field(default_factory=list)   # Source pages (for PDFs)
    section_heading: Optional[str] = None                   # Source section (for DOCX)
    metadata: dict = field(default_factory=dict)


def _get_tokenizer() -> tiktoken.Encoding:
    return tiktoken.get_encoding(TOKENIZER_MODEL)


def _count_tokens(text: str, enc: tiktoken.Encoding) -> int:
    return len(enc.encode(text))


def chunk_text(
    text: str,
    doc_id: str,
    source_file: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    page_numbers: Optional[list[int]] = None,
    section_heading: Optional[str] = None,
) -> list[DocumentChunk]:
    """
    Split text into overlapping token-bounded chunks.

    Args:
        text: The text to chunk
        doc_id: Parent document identifier
        source_file: Original file path string
        chunk_tokens: Target tokens per chunk
        overlap_tokens: Token overlap between consecutive chunks
        page_numbers: Page numbers these chunks come from
        section_heading: Section heading for DOCX content

    Returns:
        List of DocumentChunk objects
    """
    enc = _get_tokenizer()
    tokens = enc.encode(text)

    if not tokens:
        return []

    chunks: list[DocumentChunk] = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = min(start + chunk_tokens, len(tokens))
        chunk_tokens_list = tokens[start:end]
        chunk_text_str = enc.decode(chunk_tokens_list)

        chunk_id = f"{doc_id}_chunk_{chunk_index:03d}"
        chunks.append(DocumentChunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            source_file=source_file,
            chunk_index=chunk_index,
            text=chunk_text_str.strip(),
            token_count=len(chunk_tokens_list),
            page_numbers=page_numbers or [],
            section_heading=section_heading,
            metadata={
                "start_token": start,
                "end_token": end,
            },
        ))

        chunk_index += 1
        # Advance by chunk_tokens - overlap_tokens to create overlap
        advance = chunk_tokens - overlap_tokens
        if advance <= 0:
            advance = chunk_tokens  # Safety: avoid infinite loop
        start += advance

    return chunks


def chunk_pdf(parsed_pdf, doc_id: str, **kwargs) -> list[DocumentChunk]:
    """
    Chunk a ParsedPDF object, preserving page attribution.

    Chunks page by page but merges short pages to avoid tiny chunks.
    """
    enc = _get_tokenizer()
    chunks: list[DocumentChunk] = []
    buffer_text = ""
    buffer_pages: list[int] = []

    chunk_tokens = kwargs.get("chunk_tokens", DEFAULT_CHUNK_TOKENS)
    overlap_tokens = kwargs.get("overlap_tokens", DEFAULT_OVERLAP_TOKENS)

    for page in parsed_pdf.pages:
        if not page.text:
            continue

        buffer_text += ("\n\n" if buffer_text else "") + page.text
        buffer_pages.append(page.page_number)

        # Flush buffer when it reaches chunk size
        if _count_tokens(buffer_text, enc) >= chunk_tokens:
            page_chunks = chunk_text(
                buffer_text,
                doc_id=doc_id,
                source_file=str(parsed_pdf.source_file),
                chunk_tokens=chunk_tokens,
                overlap_tokens=overlap_tokens,
                page_numbers=list(buffer_pages),
            )
            # Re-index chunks
            for chunk in page_chunks:
                chunk.chunk_index = len(chunks) + chunk.chunk_index
                chunk.chunk_id = f"{doc_id}_chunk_{chunk.chunk_index:03d}"
            chunks.extend(page_chunks)
            # Keep overlap: retain last overlap_tokens worth of text in buffer
            tokens = enc.encode(buffer_text)
            if len(tokens) > overlap_tokens:
                buffer_text = enc.decode(tokens[-overlap_tokens:])
            buffer_pages = [buffer_pages[-1]] if buffer_pages else []

    # Flush remaining buffer
    if buffer_text.strip():
        remaining_chunks = chunk_text(
            buffer_text,
            doc_id=doc_id,
            source_file=str(parsed_pdf.source_file),
            chunk_tokens=chunk_tokens,
            overlap_tokens=overlap_tokens,
            page_numbers=list(buffer_pages),
        )
        for chunk in remaining_chunks:
            chunk.chunk_index = len(chunks) + chunk.chunk_index
            chunk.chunk_id = f"{doc_id}_chunk_{chunk.chunk_index:03d}"
        chunks.extend(remaining_chunks)

    return chunks


def chunk_docx(parsed_docx, doc_id: str, **kwargs) -> list[DocumentChunk]:
    """
    Chunk a ParsedDocx object, preserving section attribution.
    """
    chunks: list[DocumentChunk] = []
    chunk_tokens = kwargs.get("chunk_tokens", DEFAULT_CHUNK_TOKENS)
    overlap_tokens = kwargs.get("overlap_tokens", DEFAULT_OVERLAP_TOKENS)

    for section in parsed_docx.sections:
        section_text = ""
        if section.heading:
            section_text = section.heading + "\n\n"
        section_text += "\n\n".join(section.paragraphs)

        if not section_text.strip():
            continue

        section_chunks = chunk_text(
            section_text,
            doc_id=doc_id,
            source_file=str(parsed_docx.source_file),
            chunk_tokens=chunk_tokens,
            overlap_tokens=overlap_tokens,
            section_heading=section.heading,
        )
        for chunk in section_chunks:
            chunk.chunk_index = len(chunks) + chunk.chunk_index
            chunk.chunk_id = f"{doc_id}_chunk_{chunk.chunk_index:03d}"
        chunks.extend(section_chunks)

    return chunks
