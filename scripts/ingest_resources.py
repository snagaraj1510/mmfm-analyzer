#!/usr/bin/env python3
"""
Batch ingestion script — processes all files in resources/ into the knowledge base.

Usage:
    python scripts/ingest_resources.py           # Process all new files
    python scripts/ingest_resources.py --file resources/reports/report.pdf
    python scripts/ingest_resources.py --type pdf
    python scripts/ingest_resources.py --force   # Re-ingest even if already indexed
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer()
console = Console()

SUPPORTED_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".xlsm": "xlsx",
    ".csv": "csv",
    ".tsv": "csv",
}


def _make_doc_id(file_path: Path) -> str:
    """Generate a stable document ID from the file name."""
    stem = file_path.stem.lower().replace(" ", "_").replace("-", "_")
    return f"{stem}_001"


def _ingest_pdf(file_path: Path, doc_id: str, force: bool = False) -> int:
    """Ingest a PDF file. Returns chunk count."""
    from mmfm.ingestion.pdf_reader import parse_pdf
    from mmfm.knowledge.chunker import chunk_pdf
    from mmfm.knowledge.indexer import index_chunks, delete_document_chunks
    from mmfm.knowledge.registry import register_document, is_registered

    parsed = parse_pdf(file_path)

    if not force and is_registered(str(file_path), parsed.checksum):
        console.print(f"  [dim]Skipping (already indexed): {file_path.name}[/dim]")
        return 0

    if force:
        delete_document_chunks(doc_id)

    chunks = chunk_pdf(parsed, doc_id=doc_id)
    if not chunks:
        console.print(f"  [yellow]No text extracted from: {file_path.name}[/yellow]")
        return 0

    indexed = index_chunks(chunks)
    register_document(
        doc_id=doc_id,
        source_file=str(file_path),
        doc_type="pdf",
        chunk_count=indexed,
        checksum=parsed.checksum,
        topics=[],
        metadata={"filename": file_path.name},
    )
    return indexed


def _ingest_docx(file_path: Path, doc_id: str, force: bool = False) -> int:
    """Ingest a DOCX file. Returns chunk count."""
    from mmfm.ingestion.docx_reader import parse_docx
    from mmfm.knowledge.chunker import chunk_docx
    from mmfm.knowledge.indexer import index_chunks, delete_document_chunks
    from mmfm.knowledge.registry import register_document, is_registered

    parsed = parse_docx(file_path)

    if not force and is_registered(str(file_path), parsed.checksum):
        console.print(f"  [dim]Skipping (already indexed): {file_path.name}[/dim]")
        return 0

    if force:
        delete_document_chunks(doc_id)

    chunks = chunk_docx(parsed, doc_id=doc_id)
    if not chunks:
        console.print(f"  [yellow]No text extracted from: {file_path.name}[/yellow]")
        return 0

    indexed = index_chunks(chunks)
    register_document(
        doc_id=doc_id,
        source_file=str(file_path),
        doc_type="docx",
        chunk_count=indexed,
        checksum=parsed.checksum,
        topics=[],
        metadata={"filename": file_path.name},
    )
    return indexed


@app.command()
def main(
    file: Path = typer.Option(None, "--file", help="Process a single file"),
    type_filter: str = typer.Option(None, "--type", help="Filter by type: pdf | docx | xlsx | csv"),
    force: bool = typer.Option(False, "--force", help="Re-ingest even if already indexed"),
) -> None:
    from mmfm.config import RESOURCES_DIR

    console.print("[bold]MMFM Resource Ingestion[/bold]")
    console.print(f"Resources directory: {RESOURCES_DIR}")

    if file:
        files = [file] if file.exists() else []
        if not files:
            console.print(f"[red]File not found:[/red] {file}")
            raise typer.Exit(1)
    else:
        # Collect all supported files from resources/
        files = []
        for ext in SUPPORTED_TYPES:
            if type_filter is None or SUPPORTED_TYPES[ext] == type_filter:
                files.extend(RESOURCES_DIR.rglob(f"*{ext}"))
        files = [f for f in files if not f.name.startswith(".")]

    if not files:
        console.print("[yellow]No files found to ingest.[/yellow]")
        console.print("  Drop files into resources/models/, resources/reports/, or resources/reference_docs/")
        return

    console.print(f"Found {len(files)} file(s) to process.\n")
    total_chunks = 0

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task("Ingesting...", total=len(files))

        for f in files:
            ext = f.suffix.lower()
            doc_id = _make_doc_id(f)
            progress.update(task, description=f"Processing {f.name}")

            try:
                if ext == ".pdf":
                    n = _ingest_pdf(f, doc_id, force=force)
                elif ext in (".docx",):
                    n = _ingest_docx(f, doc_id, force=force)
                else:
                    console.print(f"  [dim]Skipping unsupported type: {f.name}[/dim]")
                    n = 0

                if n > 0:
                    console.print(f"  [green]✓[/green] {f.name} → {n} chunks")
                total_chunks += n
            except Exception as exc:
                console.print(f"  [red]ERROR[/red] {f.name}: {exc}")

            progress.advance(task)

    console.print(f"\n[green]Done.[/green] Total chunks indexed: {total_chunks}")


if __name__ == "__main__":
    app()
