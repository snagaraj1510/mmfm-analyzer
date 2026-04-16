#!/usr/bin/env python3
"""
Rebuild the entire knowledge base from scratch.

Clears all embeddings and re-ingests all resources.
Use when you've updated the chunking parameters or embedding model.

Usage:
    python scripts/rebuild_knowledge_base.py
    python scripts/rebuild_knowledge_base.py --confirm
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
) -> None:
    if not confirm:
        console.print("[yellow]WARNING:[/yellow] This will delete all embeddings and re-index from scratch.")
        confirmed = typer.confirm("Continue?")
        if not confirmed:
            console.print("Aborted.")
            raise typer.Exit(0)

    from mmfm.config import KNOWLEDGE_BASE_DIR

    # Clear ChromaDB
    chroma_dir = KNOWLEDGE_BASE_DIR / "embeddings"
    if chroma_dir.exists():
        import shutil
        shutil.rmtree(chroma_dir)
        console.print(f"[green]Cleared:[/green] {chroma_dir}")

    # Clear chunks
    chunks_dir = KNOWLEDGE_BASE_DIR / "chunks"
    if chunks_dir.exists():
        for f in chunks_dir.glob("*.json"):
            f.unlink()
        console.print(f"[green]Cleared:[/green] chunks directory")

    # Reset registry (keep placeholder entries but reset ingestion state)
    import json
    registry_file = KNOWLEDGE_BASE_DIR / "registry.json"
    if registry_file.exists():
        with open(registry_file) as f:
            registry = json.load(f)
        for doc in registry.get("documents", []):
            doc["ingested_at"] = None
            doc["chunk_count"] = 0
            doc["checksum"] = None
        registry["last_updated"] = None
        registry["total_chunks"] = 0
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        console.print(f"[green]Reset:[/green] registry.json")

    console.print("\nRe-indexing all resources...")

    # Run ingestion
    import subprocess
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "ingest_resources.py"), "--force"],
        capture_output=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    app()
