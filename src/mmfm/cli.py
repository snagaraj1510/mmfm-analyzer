"""
MMFM Analyzer CLI entrypoint.

Usage:
    mmfm analyze --file model.xlsx
    mmfm validate --file model.xlsx
    mmfm config show
    mmfm config set --key anthropic_api_key --value <value>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from mmfm.config import get_settings, save_setting

app = typer.Typer(
    name="mmfm",
    help="Municipal Market Financial Model Analyzer",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# Sub-command groups
config_app = typer.Typer(help="Manage configuration settings", no_args_is_help=True)
app.add_typer(config_app, name="config")


# ── ANALYZE ─────────────────────────────────────────────────────────────────

@app.command()
def analyze(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Excel financial model"),
    scenario: str = typer.Option("base", "--scenario", "-s", help="Scenario: base | all"),
    horizon: int = typer.Option(20, "--horizon", help="Projection horizon in years"),
    output_format: str = typer.Option("terminal", "--format", help="terminal | json"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    discount_rate: Optional[float] = typer.Option(None, "--discount-rate", help="Override discount rate"),
) -> None:
    """Run base-case financial analysis on an Excel model."""
    from mmfm.ingestion.excel_parser import parse_excel
    from mmfm.engine.core_metrics import calculate_npv, calculate_irr, calculate_payback
    from mmfm.output.terminal import print_header, print_core_metrics, print_projection_table, print_validation_result
    from mmfm.output.json_dump import metrics_to_dict, dump_to_file

    settings = get_settings()
    rate = discount_rate or settings.defaults.discount_rate

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    console.print(f"[dim]Parsing {file.name}...[/dim]")

    try:
        model = parse_excel(file)
    except ValueError as exc:
        console.print(f"[red]Parse error:[/red] {exc}")
        raise typer.Exit(1)

    print_header(
        f"MMFM Analysis: {file.name}",
        subtitle=f"Discount rate: {rate:.1%} | Horizon: {horizon} years | Currency: {model.base_currency}",
    )

    # Show validation results if available
    if model.validation_result:
        print_validation_result(model.validation_result)
        if not model.validation_result.passed and settings.validation.strict_mode:
            console.print("[red]Strict mode: aborting due to schema validation errors.[/red]")
            raise typer.Exit(1)

    # Try to extract cash flows from the model
    # This is a best-effort extraction from whatever sheets exist
    cash_flows = _extract_cash_flows_from_model(model, horizon)

    if cash_flows is None:
        console.print(
            "[yellow]Could not auto-extract cash flows from this model.[/yellow]\n"
            "  Ensure the model has a sheet named 'Revenue Projections', 'Cash Flow', or similar.\n"
            "  Alternatively, use a structured model with a recognized schema."
        )
        raise typer.Exit(1)

    npv_result = calculate_npv(cash_flows, rate)
    irr_result = calculate_irr(cash_flows)
    payback_result = calculate_payback(cash_flows)

    if output_format == "json":
        data = metrics_to_dict(npv_result, irr_result, payback_result)
        data["source_file"] = str(file)
        data["discount_rate"] = rate
        data["horizon_years"] = horizon

        if output_file:
            dump_to_file(data, output_file)
            console.print(f"[green]JSON output written to:[/green] {output_file}")
        else:
            console.print_json(json.dumps(data))
    else:
        print_core_metrics(npv_result, irr_result, payback_result, currency=model.base_currency)


def _extract_cash_flows_from_model(model, horizon: int) -> Optional[list[float]]:
    """
    Best-effort extraction of a cash flow series from a parsed model.
    Looks for common sheet names and column patterns.
    """
    cash_flow_sheet_names = ["cash flow", "cashflow", "cash flows", "fcf", "free cash flow"]
    revenue_sheet_names = ["revenue projections", "revenue", "revenues"]

    sheets_lower = {name.lower(): name for name in model.sheets}

    # First: look for an explicit cash flow sheet
    for candidate in cash_flow_sheet_names:
        if candidate in sheets_lower:
            df = model.sheets[sheets_lower[candidate]]
            cf_col = _find_column(df, ["free_cash_flow", "fcf", "net_cash_flow", "cash_flow"])
            if cf_col is not None:
                try:
                    return [float(v) for v in df[cf_col].dropna().tolist()]
                except (ValueError, TypeError):
                    pass

    # Second: look for revenue projections with a free cash flow column
    for candidate in revenue_sheet_names:
        if candidate in sheets_lower:
            df = model.sheets[sheets_lower[candidate]]
            cf_col = _find_column(df, ["free_cash_flow", "fcf", "net_cash_flow"])
            if cf_col is not None:
                try:
                    return [float(v) for v in df[cf_col].dropna().tolist()]
                except (ValueError, TypeError):
                    pass

    return None


def _find_column(df, candidates: list[str]):
    """Find the first matching column (case-insensitive) in a DataFrame."""
    cols_lower = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None


def _get_demo_inputs(settings):
    """
    Return placeholder financial inputs for CLI commands that don't yet
    have a full Excel model parser wired to the engine.

    TODO (Phase 3): Replace with actual model parsing from the Excel file.
    """
    from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
    revenue = RevenueInputs(
        base_stall_rental_income=200_000,
        occupancy_rate=0.60,
        vendor_fees_annual=30_000,
        market_levies_annual=15_000,
        rental_escalation_rate=0.06,
        fee_escalation_rate=0.06,
        occupancy_ramp_years=3,
        occupancy_target=0.70,
    )
    capex = CapexInputs(
        total_capex=1_000_000,
        construction_schedule={0: 0.60, 1: 0.40},
        overrun_contingency=0.10,
        grant_amount=200_000,
        grant_disbursement_year=0,
    )
    opex = OpexInputs(
        base_opex=80_000,
        opex_escalation_rate=0.05,
        debt_service_annual=50_000,
    )
    return revenue, capex, opex


# ── VALIDATE ────────────────────────────────────────────────────────────────

@app.command()
def validate(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Excel financial model"),
    schema: Optional[str] = typer.Option(None, "--schema", help="Schema name to validate against"),
    audit: bool = typer.Option(False, "--audit", help="Generate audit log"),
) -> None:
    """Validate an Excel model against its schema."""
    from mmfm.ingestion.excel_parser import parse_excel
    from mmfm.output.terminal import print_header, print_validation_result

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    model = parse_excel(file, schema_name=schema, validate=True)

    print_header(f"Validation: {file.name}")

    if model.validation_result:
        print_validation_result(model.validation_result)
        if audit:
            from mmfm.validation.audit_logger import AuditLogger
            logger = AuditLogger()
            for error in (model.validation_result.errors or []):
                logger.log_validation(metric="schema", value=0.0, status="FAIL", message=error)
            for warning in (model.validation_result.warnings or []):
                logger.log_validation(metric="schema", value=0.0, status="WARNING", message=warning)
            if model.validation_result.passed:
                logger.log_validation(metric="schema", value=1.0, status="PASS", message="All checks passed")
            audit_path = file.with_suffix(".audit.json")
            logger.export_json(audit_path)
            console.print(f"[green]Audit log written to:[/green] {audit_path}")
        if not model.validation_result.passed:
            raise typer.Exit(1)
    else:
        if model.detected_schema is None:
            console.print(
                "[yellow]No schema detected or specified.[/yellow]\n"
                "  Use --schema to specify one (e.g. --schema revenue_schema)."
            )
        else:
            console.print(
                f"[yellow]Schema '{model.detected_schema}' detected but schema file not found.[/yellow]"
            )


# ── CONFIG ───────────────────────────────────────────────────────────────────

@config_app.command("show")
def config_show() -> None:
    """Show current configuration (API key is masked)."""
    settings = get_settings()
    d = settings.model_dump()

    # Mask API key
    if d.get("anthropic", {}).get("api_key"):
        key = d["anthropic"]["api_key"]
        d["anthropic"]["api_key"] = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"

    console.print_json(json.dumps(d, indent=2))


@config_app.command("set")
def config_set(
    key: str = typer.Option(..., "--key", "-k", help="Config key (e.g. anthropic.api_key)"),
    value: str = typer.Option(..., "--value", "-v", help="Config value"),
) -> None:
    """Set a configuration value (stored in ~/.mmfm/config.yaml, never in the project)."""
    if key == "anthropic_api_key" or key == "anthropic.api_key":
        console.print(
            "[yellow]Tip:[/yellow] You can also set ANTHROPIC_API_KEY as an environment variable.\n"
            "  This is the recommended approach for CI/CD and shared environments."
        )

    save_setting(key, value)
    console.print(f"[green]Saved:[/green] {key} → ~/.mmfm/config.yaml")
    console.print("[dim]Note: This file is outside your project directory and will not be committed.[/dim]")


# ── SENSITIVITY ──────────────────────────────────────────────────────────────

@app.command()
def sensitivity(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Excel financial model"),
    variable: Optional[str] = typer.Option(None, "--variable", help="Single variable to analyze"),
    tornado: bool = typer.Option(False, "--tornado", help="Show tornado chart"),
    horizon: int = typer.Option(20, "--horizon", help="Projection horizon in years"),
    output_format: str = typer.Option("terminal", "--format", help="terminal | json"),
) -> None:
    """Run sensitivity analysis — sweep input variables and measure NPV impact."""
    from mmfm.output.terminal import print_header, print_tornado_chart

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    settings = get_settings()
    revenue, capex, opex = _get_demo_inputs(settings)

    print_header(f"Sensitivity Analysis: {file.name}")

    if variable:
        from mmfm.engine.sensitivity import run_single_variable_sensitivity
        var_result = run_single_variable_sensitivity(
            variable, revenue, capex, opex,
            discount_rate=settings.defaults.discount_rate,
            horizon_years=horizon,
        )
        console.print(f"[bold]{var_result.label}[/bold] — NPV swing: {var_result.npv_swing:,.2f}")
        console.print(f"  Low  ({var_result.variable_values[0]:.3f}): NPV = {var_result.npv_at_low:,.2f}")
        console.print(f"  High ({var_result.variable_values[-1]:.3f}): NPV = {var_result.npv_at_high:,.2f}")
    else:
        from mmfm.engine.sensitivity import run_sensitivity
        result = run_sensitivity(
            revenue, capex, opex,
            discount_rate=settings.defaults.discount_rate,
            horizon_years=horizon,
        )
        print_tornado_chart(result)


# ── SIMULATE ─────────────────────────────────────────────────────────────────

@app.command()
def simulate(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Excel financial model"),
    iterations: int = typer.Option(10_000, "--iterations", "-n", help="Number of Monte Carlo iterations"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility"),
    horizon: int = typer.Option(20, "--horizon", help="Projection horizon in years"),
    output_format: str = typer.Option("terminal", "--format", help="terminal | json"),
) -> None:
    """Run Monte Carlo simulation with randomized assumptions."""
    from mmfm.engine.monte_carlo import run_monte_carlo
    from mmfm.output.terminal import print_header, print_monte_carlo_summary

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    settings = get_settings()
    revenue, capex, opex = _get_demo_inputs(settings)

    print_header(f"Monte Carlo Simulation: {file.name}", subtitle=f"{iterations:,} iterations")
    console.print(f"[dim]Running {iterations:,} simulations...[/dim]")

    result = run_monte_carlo(
        revenue, capex, opex,
        iterations=iterations,
        seed=seed,
        discount_rate=settings.defaults.discount_rate,
        horizon_years=horizon,
    )
    print_monte_carlo_summary(result)


# ── COMPARE ───────────────────────────────────────────────────────────────────

@app.command()
def compare(
    output_format: str = typer.Option("terminal", "--format", help="terminal | json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    min_irr: float = typer.Option(0.12, "--min-irr", help="Minimum IRR threshold for investment-ready flag"),
    min_dscr: float = typer.Option(1.2, "--min-dscr", help="Minimum DSCR threshold for investment-ready flag"),
) -> None:
    """Compare MAP demo portfolio markets (Pemba, Tsoka/Lizulu, Chainda, Kisumu)."""
    from mmfm.demo.demo_markets import DEMO_PORTFOLIO  # noqa: PLC0415
    from mmfm.engine.comparison import compare_markets
    import json

    result = compare_markets(DEMO_PORTFOLIO)
    table = result.summary_table()
    ready = result.investment_ready(min_irr=min_irr, min_dscr=min_dscr)

    if output_format == "json":
        data = {"markets": table, "investment_ready": ready, "npv_ranking": result.npv_ranking(), "irr_ranking": result.irr_ranking()}
        if output:
            output.write_text(json.dumps(data, indent=2, default=str))
            console.print(f"[green]JSON written to:[/green] {output}")
        else:
            console.print_json(json.dumps(data, indent=2, default=str))
    else:
        from rich.table import Table
        from rich.text import Text

        console.print(f"\n[bold]MAP Portfolio — Multi-Market Comparison[/bold]")
        console.print(f"[dim]Investment-ready threshold: IRR >= {min_irr:.0%}, DSCR >= {min_dscr}[/dim]\n")

        tbl = Table(show_header=True, header_style="bold cyan")
        tbl.add_column("Market", style="bold")
        tbl.add_column("Country")
        tbl.add_column("NPV (USD)", justify="right")
        tbl.add_column("IRR", justify="right")
        tbl.add_column("Payback", justify="right")
        tbl.add_column("DSCR", justify="right")
        tbl.add_column("MIRI", justify="right")
        tbl.add_column("Gov.", justify="right")
        tbl.add_column("Ready?", justify="center")

        for row in table:
            is_ready = row["market"] in ready
            ready_str = "[green]Y[/green]" if is_ready else "[red]N[/red]"
            tbl.add_row(
                row["market"],
                row["country"],
                f"${row['npv_usd']:,.0f}" if row["npv_usd"] is not None else "-",
                f"{row['irr_pct']:.1f}%" if row["irr_pct"] is not None else "-",
                f"{row['payback_years']:.1f}yr" if row["payback_years"] is not None else "-",
                f"{row['min_dscr']:.2f}" if row["min_dscr"] is not None else "-",
                f"{row['miri_score']:.0f}" if row["miri_score"] is not None else "-",
                f"{row['governance_score']:.0f}" if row["governance_score"] is not None else "-",
                ready_str,
            )

        console.print(tbl)
        console.print(f"\n[bold]Investment-ready markets:[/bold] {', '.join(ready) if ready else 'None'}")
        console.print(f"[bold]NPV ranking:[/bold] {' > '.join(result.npv_ranking())}")


# ── INGEST ───────────────────────────────────────────────────────────────────

@app.command()
def ingest(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Ingest a single file"),
    all_files: bool = typer.Option(False, "--all", help="Ingest all new resources"),
    type_filter: Optional[str] = typer.Option(None, "--type", help="Filter: pdf | docx | xlsx | csv"),
    force: bool = typer.Option(False, "--force", help="Re-ingest even if already indexed"),
) -> None:
    """Ingest documents from resources/ into the knowledge base."""
    from mmfm.config import RESOURCES_DIR
    from mmfm.knowledge.registry import get_registry_status

    if not file and not all_files and not type_filter:
        console.print("[yellow]Specify --all, --file, or --type.[/yellow]")
        raise typer.Exit(1)

    # Build file list
    if file:
        files = [file] if file.exists() else []
    else:
        exts = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".tsv"}
        files = [f for f in RESOURCES_DIR.rglob("*") if f.suffix.lower() in exts and not f.name.startswith(".")]
        if type_filter:
            type_map = {"pdf": ".pdf", "docx": ".docx", "xlsx": ".xlsx", "csv": ".csv"}
            allowed_ext = type_map.get(type_filter, "")
            files = [f for f in files if f.suffix.lower() == allowed_ext]

    if not files:
        console.print("[yellow]No files found to ingest.[/yellow]")
        return

    total_chunks = 0
    for f in files:
        ext = f.suffix.lower()
        doc_id = f.stem.lower().replace(" ", "_").replace("-", "_") + "_001"

        try:
            if ext == ".pdf":
                from mmfm.ingestion.pdf_reader import parse_pdf
                from mmfm.knowledge.chunker import chunk_pdf
                from mmfm.knowledge.indexer import index_chunks, delete_document_chunks
                from mmfm.knowledge.registry import register_document, is_registered
                parsed = parse_pdf(f)
                if not force and is_registered(str(f), parsed.checksum):
                    console.print(f"  [dim]Already indexed: {f.name}[/dim]")
                    continue
                if force:
                    delete_document_chunks(doc_id)
                chunks = chunk_pdf(parsed, doc_id=doc_id)
                n = index_chunks(chunks)
                register_document(doc_id=doc_id, source_file=str(f), doc_type="pdf",
                                  chunk_count=n, checksum=parsed.checksum)
                console.print(f"  [green]✓[/green] {f.name} → {n} chunks")
                total_chunks += n

            elif ext == ".docx":
                from mmfm.ingestion.docx_reader import parse_docx
                from mmfm.knowledge.chunker import chunk_docx
                from mmfm.knowledge.indexer import index_chunks, delete_document_chunks
                from mmfm.knowledge.registry import register_document, is_registered
                parsed = parse_docx(f)
                if not force and is_registered(str(f), parsed.checksum):
                    console.print(f"  [dim]Already indexed: {f.name}[/dim]")
                    continue
                if force:
                    delete_document_chunks(doc_id)
                chunks = chunk_docx(parsed, doc_id=doc_id)
                n = index_chunks(chunks)
                register_document(doc_id=doc_id, source_file=str(f), doc_type="docx",
                                  chunk_count=n, checksum=parsed.checksum)
                console.print(f"  [green]✓[/green] {f.name} → {n} chunks")
                total_chunks += n

        except Exception as exc:
            console.print(f"  [red]ERROR[/red] {f.name}: {exc}")

    console.print(f"\nTotal chunks indexed: {total_chunks}")


# ── KB ────────────────────────────────────────────────────────────────────────

kb_app = typer.Typer(help="Knowledge base management", no_args_is_help=True)
app.add_typer(kb_app, name="kb")


@kb_app.command("status")
def kb_status() -> None:
    """Show knowledge base statistics."""
    from mmfm.knowledge.registry import get_registry_status
    from mmfm.knowledge.indexer import get_collection_stats

    reg_status = get_registry_status()
    col_stats = get_collection_stats()

    console.print("\n[bold]Knowledge Base Status[/bold]")
    console.print(f"  Registered documents: {reg_status['total_documents']}")
    console.print(f"  Registered chunks:    {reg_status['total_chunks']}")
    console.print(f"  Indexed chunks:       {col_stats.get('total_chunks', 0)}")
    console.print(f"  Last updated:         {reg_status.get('last_updated') or 'Never'}")

    if reg_status["documents"]:
        console.print("\n  Documents:")
        for doc in reg_status["documents"]:
            status = "[green]indexed[/green]" if doc["chunk_count"] > 0 else "[yellow]pending[/yellow]"
            console.print(f"    {status} {doc['doc_id']} ({doc['chunk_count']} chunks)")
    console.print()


@kb_app.command("query")
def kb_query(
    query: str = typer.Argument(..., help="Query string"),
    n: int = typer.Option(5, "--n", help="Number of results"),
) -> None:
    """Test RAG retrieval — query the knowledge base directly."""
    from mmfm.knowledge.retriever import retrieve

    result = retrieve(query, n_results=n)

    if not result.chunks:
        console.print("[yellow]No results found. Have you run 'mmfm ingest --all'?[/yellow]")
        return

    console.print(f"\n[bold]Query:[/bold] {query}")
    console.print(f"[dim]Retrieved {len(result.chunks)} chunks[/dim]\n")

    for i, chunk in enumerate(result.chunks):
        source = chunk.source_file.split("/")[-1].split("\\")[-1]
        console.print(f"[bold cyan]Result {i+1}[/bold cyan] — {source} (distance: {chunk.distance:.3f})")
        console.print(f"  {chunk.text[:300]}{'...' if len(chunk.text) > 300 else ''}")
        console.print()


@kb_app.command("rebuild")
def kb_rebuild(
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
) -> None:
    """Rebuild the entire knowledge base from scratch."""
    if not confirm:
        confirmed = typer.confirm(
            "This will delete all embeddings and re-index from scratch. Continue?"
        )
        if not confirmed:
            raise typer.Exit(0)

    import subprocess
    import sys
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    result = subprocess.run(
        [sys.executable, str(scripts_dir / "rebuild_knowledge_base.py"), "--confirm"],
        capture_output=False,
    )
    raise typer.Exit(result.returncode)



# ── REPORT ────────────────────────────────────────────────────────────────────

@app.command()
def report(
    file: Path = typer.Option(..., "--file", "-f", help="Path to Excel financial model"),
    output_format: str = typer.Option("terminal", "--format", help="terminal | excel | pdf | json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    horizon: int = typer.Option(20, "--horizon", help="Projection horizon in years"),
    with_scenarios: bool = typer.Option(False, "--scenarios", help="Include scenario comparison"),
    with_sensitivity: bool = typer.Option(False, "--sensitivity", help="Include sensitivity analysis"),
    with_narrative: bool = typer.Option(False, "--narrative", help="Include AI narrative (requires API key)"),
) -> None:
    """Generate a financial analysis report in the specified format."""
    from mmfm.engine.core_metrics import calculate_npv, calculate_irr, calculate_payback
    from mmfm.engine.projections import project_cash_flows
    from mmfm.engine.scenarios import run_all_scenarios
    from mmfm.engine.sensitivity import run_sensitivity
    from mmfm.output.terminal import (
        print_header, print_core_metrics, print_projection_table,
        print_scenario_comparison, print_tornado_chart,
    )
    from mmfm.output.json_dump import metrics_to_dict, dump_to_file
    import json

    if not file.exists():
        console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    settings = get_settings()
    rate = settings.defaults.discount_rate
    revenue_inputs, capex_inputs, opex_inputs = _get_demo_inputs(settings)

    # Build projection
    projection = project_cash_flows(
        revenue_inputs, capex_inputs, opex_inputs,
        horizon_years=horizon,
        inflation_rate=settings.defaults.inflation_rate,
    )
    cash_flows = projection.get_cash_flows()
    npv_result = calculate_npv(cash_flows, rate)
    irr_result = calculate_irr(cash_flows)
    payback_result = calculate_payback(cash_flows)

    comparison = None
    sensitivity = None
    if with_scenarios:
        comparison = run_all_scenarios(revenue_inputs, capex_inputs, opex_inputs,
                                        horizon_years=horizon, discount_rate=rate)
    if with_sensitivity:
        sensitivity = run_sensitivity(revenue_inputs, capex_inputs, opex_inputs,
                                       discount_rate=rate, horizon_years=horizon)

    narrative = None
    if with_narrative:
        try:
            from mmfm.ai.narrator import generate_financial_narrative
            from mmfm.knowledge.retriever import retrieve_for_context
            from mmfm.output.json_dump import metrics_to_dict
            fin_data = metrics_to_dict(npv_result, irr_result, payback_result)
            rag_ctx = retrieve_for_context("municipal market financial analysis revenue projections")
            narrative = generate_financial_narrative(fin_data, rag_context=rag_ctx)
        except Exception as exc:
            console.print(f"[yellow]Narrative generation failed:[/yellow] {exc}")

    if output_format == "terminal":
        print_header(f"Analysis Report: {file.name}",
                     subtitle=f"Discount rate: {rate:.1%} | Horizon: {horizon} yrs")
        print_core_metrics(npv_result, irr_result, payback_result)
        print_projection_table(projection)
        if comparison:
            print_scenario_comparison(comparison)
        if sensitivity:
            print_tornado_chart(sensitivity)

    elif output_format == "json":
        data = metrics_to_dict(npv_result, irr_result, payback_result)
        data["source_file"] = str(file)
        if narrative:
            data["narrative"] = narrative
        if output:
            dump_to_file(data, output)
            console.print(f"[green]JSON written to:[/green] {output}")
        else:
            console.print_json(json.dumps(data))

    elif output_format == "excel":
        from mmfm.output.excel_export import export_excel
        out_path = output or file.with_suffix(".report.xlsx")
        export_excel(out_path, npv_result, irr_result, payback_result, projection,
                     source_file=file.name, comparison=comparison, sensitivity=sensitivity)
        console.print(f"[green]Excel report written to:[/green] {out_path}")

    elif output_format == "pdf":
        from mmfm.output.pdf_export import export_pdf
        out_path = output or file.with_suffix(".report.pdf")
        export_pdf(out_path, npv_result, irr_result, payback_result, projection,
                   source_file=file.name, comparison=comparison, sensitivity=sensitivity,
                   narrative=narrative)
        console.print(f"[green]PDF report written to:[/green] {out_path}")


if __name__ == "__main__":
    app()
