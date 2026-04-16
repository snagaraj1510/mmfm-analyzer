#!/usr/bin/env python3
"""
Standalone script to validate an Excel financial model.

Usage:
    python scripts/validate_model.py resources/models/my_model.xlsx
    python scripts/validate_model.py resources/models/my_model.xlsx --schema capex_schema
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def main(
    file: Path = typer.Argument(..., help="Path to Excel model"),
    schema: str = typer.Option(None, "--schema", help="Schema name to validate against"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    from mmfm.ingestion.excel_parser import parse_excel
    from mmfm.output.terminal import print_header, print_validation_result

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    model = parse_excel(file, schema_name=schema, validate=True)

    print_header(f"Model Validation: {file.name}")

    console.print(f"  Sheets found: {', '.join(model.sheets.keys())}")
    console.print(f"  Detected schema: {model.detected_schema or 'None'}")
    console.print(f"  Base currency: {model.base_currency}")

    if verbose:
        for sheet_name, df in model.sheets.items():
            console.print(f"\n  [bold]{sheet_name}[/bold]: {len(df)} rows, columns: {list(df.columns)}")

    console.print()

    if model.validation_result:
        print_validation_result(model.validation_result)
        sys.exit(0 if model.validation_result.passed else 1)
    else:
        console.print("[yellow]No schema validation performed.[/yellow]")


if __name__ == "__main__":
    app()
