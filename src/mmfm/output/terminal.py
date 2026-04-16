"""
Rich terminal output for financial analysis results.
"""

from __future__ import annotations

import math
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from mmfm.engine.core_metrics import NPVResult, IRRResult, PaybackResult, DSCRResult, OperatingMarginResult
from mmfm.engine.projections import CashFlowProjection

console = Console()


def _fmt_currency(value: float, currency: str = "USD", compact: bool = False) -> str:
    """Format a currency value for display."""
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    if compact:
        if abs(value) >= 1_000_000:
            return f"{currency} {value / 1_000_000:.2f}M"
        if abs(value) >= 1_000:
            return f"{currency} {value / 1_000:.1f}K"
    return f"{currency} {value:,.2f}"


def _fmt_pct(value: float, decimal_places: int = 1) -> str:
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value * 100:.{decimal_places}f}%"


def _fmt_ratio(value: float, decimal_places: int = 2) -> str:
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value:.{decimal_places}f}x"


def _color_npv(value: float) -> str:
    if math.isnan(value):
        return "white"
    return "green" if value > 0 else "red"


def _color_dscr(value: float, threshold: float = 1.2) -> str:
    if math.isnan(value):
        return "white"
    if value >= threshold:
        return "green"
    if value >= 1.0:
        return "yellow"
    return "red"


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled header panel."""
    content = f"[bold]{title}[/bold]"
    if subtitle:
        content += f"\n[dim]{subtitle}[/dim]"
    console.print(Panel(content, style="blue", padding=(1, 4)))


def print_core_metrics(
    npv: NPVResult,
    irr: IRRResult,
    payback: PaybackResult,
    currency: str = "USD",
) -> None:
    """Print a summary table of core financial metrics."""
    table = Table(
        title="Core Financial Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="bold", width=25)
    table.add_column("Value", justify="right", width=20)
    table.add_column("Status", justify="center", width=12)

    # NPV
    npv_color = _color_npv(npv.value)
    npv_status = "POSITIVE" if npv.is_positive else "NEGATIVE"
    npv_status_color = "green" if npv.is_positive else "red"
    table.add_row(
        f"NPV (r={_fmt_pct(npv.discount_rate)})",
        Text(_fmt_currency(npv.value, currency, compact=True), style=npv_color),
        Text(npv_status, style=npv_status_color),
    )

    # IRR
    if irr.converged and irr.value is not None:
        irr_color = "green" if irr.value > npv.discount_rate else "yellow"
        irr_display = _fmt_pct(irr.value)
        irr_status = "ABOVE HURDLE" if irr.value > npv.discount_rate else "BELOW HURDLE"
        irr_status_color = "green" if irr.value > npv.discount_rate else "yellow"
    else:
        irr_display = "N/A"
        irr_color = "dim"
        irr_status = irr.message[:12]
        irr_status_color = "dim"

    table.add_row(
        "IRR",
        Text(irr_display, style=irr_color),
        Text(irr_status, style=irr_status_color),
    )

    # Payback
    if payback.reached and payback.years is not None:
        pb_display = f"{payback.years:.1f} yrs"
        pb_color = "green" if payback.years <= 10 else "yellow"
        pb_status = "REACHED"
        pb_status_color = pb_color
    else:
        pb_display = "Never"
        pb_color = "red"
        pb_status = "NOT REACHED"
        pb_status_color = "red"

    table.add_row(
        "Payback Period",
        Text(pb_display, style=pb_color),
        Text(pb_status, style=pb_status_color),
    )

    console.print(table)
    console.print()


def print_dscr_table(dscr: DSCRResult) -> None:
    """Print DSCR per year with color coding."""
    table = Table(
        title="Debt Service Coverage Ratio (DSCR)",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Year", justify="right", width=8)
    table.add_column("DSCR", justify="right", width=10)
    table.add_column("Status", justify="left", width=15)

    for year, val in zip(dscr.years, dscr.values):
        color = _color_dscr(val)
        if math.isnan(val):
            status = "No debt"
            val_str = "—"
        elif val < 1.0:
            status = "CRITICAL"
        elif val < 1.2:
            status = "AT RISK"
        else:
            status = "OK"
            val_str = _fmt_ratio(val)

        if not math.isnan(val):
            val_str = _fmt_ratio(val)

        table.add_row(str(year), Text(val_str, style=color), Text(status, style=color))

    console.print(f"  Min DSCR: {_fmt_ratio(dscr.min_dscr)} (Year {dscr.min_dscr_year})")
    if dscr.below_threshold:
        console.print(
            f"  [yellow]Warning: DSCR below 1.2x in years: {dscr.below_threshold}[/yellow]"
        )
    console.print(table)
    console.print()


def print_projection_table(projection: CashFlowProjection, max_rows: int = 25) -> None:
    """Print year-by-year cash flow projection."""
    currency = projection.base_currency
    table = Table(
        title="Cash Flow Projection",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Year", justify="right", width=6)
    table.add_column("Revenue", justify="right", width=15)
    table.add_column("Capex", justify="right", width=14)
    table.add_column("Opex", justify="right", width=14)
    table.add_column("NOI", justify="right", width=14)
    table.add_column("FCF", justify="right", width=14)
    table.add_column("Cumulative", justify="right", width=14)
    table.add_column("Occupancy", justify="right", width=10)

    for row in projection.years[:max_rows]:
        fcf_color = "green" if row.free_cash_flow >= 0 else "red"
        cum_color = "green" if row.cumulative_cash_flow >= 0 else "red"

        table.add_row(
            str(row.year),
            _fmt_currency(row.revenue, currency, compact=True),
            _fmt_currency(row.capex, currency, compact=True),
            _fmt_currency(row.opex, currency, compact=True),
            _fmt_currency(row.net_operating_income, currency, compact=True),
            Text(_fmt_currency(row.free_cash_flow, currency, compact=True), style=fcf_color),
            Text(_fmt_currency(row.cumulative_cash_flow, currency, compact=True), style=cum_color),
            _fmt_pct(row.occupancy_rate),
        )

    if len(projection.years) > max_rows:
        console.print(f"  [dim](Showing {max_rows} of {len(projection.years)} years)[/dim]")

    console.print(table)
    console.print()


def print_validation_result(result) -> None:
    """Print schema validation results."""
    if result.passed:
        console.print(f"[green]Schema validation PASSED:[/green] {result.schema_name}")
    else:
        console.print(f"[red]Schema validation FAILED:[/red] {result.schema_name}")

    for err in result.errors:
        loc = f" (row {err.row})" if err.row is not None else ""
        console.print(f"  [red]ERROR[/red] {err.sheet}/{err.column}{loc}: {err.message}")

    for warn in result.warnings:
        loc = f" (row {warn.row})" if warn.row is not None else ""
        console.print(f"  [yellow]WARN[/yellow]  {warn.sheet}/{warn.column}{loc}: {warn.message}")

    console.print()


def print_scenario_comparison(comparison, currency: str = "USD") -> None:
    """Print scenario comparison table."""
    table = Table(
        title="Scenario Comparison",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Scenario", width=14)
    table.add_column("NPV", justify="right", width=18)
    table.add_column("IRR", justify="right", width=10)
    table.add_column("Payback", justify="right", width=10)
    table.add_column("Min DSCR", justify="right", width=10)
    table.add_column("Avg Margin", justify="right", width=12)

    ranking = comparison.npv_ranking()
    for i, name in enumerate(ranking):
        result = comparison.results[name]
        color = "green" if i == 0 else ("red" if i == len(ranking) - 1 else "yellow")
        irr_str = _fmt_pct(result.irr.value) if result.irr.converged and result.irr.value is not None else "N/A"
        pb_str = f"{result.payback.years:.1f} yrs" if result.payback.reached and result.payback.years else "Never"
        dscr_str = _fmt_ratio(result.dscr.min_dscr)
        margin_str = _fmt_pct(result.operating_margin.average)
        table.add_row(
            Text(name.upper(), style=f"bold {color}"),
            Text(_fmt_currency(result.npv.value, currency, compact=True), style=color),
            Text(irr_str, style=color),
            Text(pb_str, style=color),
            Text(dscr_str, style=color),
            Text(margin_str, style=color),
        )
    console.print(table)
    console.print()


def print_tornado_chart(sensitivity, max_vars: int = 10) -> None:
    """Print a text-based tornado chart of NPV sensitivity."""
    ordered = sensitivity.tornado_order()[:max_vars]
    base_npv = sensitivity.base_npv

    table = Table(
        title=f"Tornado Chart — NPV Sensitivity (Base NPV: {_fmt_currency(base_npv, compact=True)})",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Variable", width=30)
    table.add_column("Low →", justify="right", width=16)
    table.add_column("← High", justify="right", width=16)
    table.add_column("Swing", justify="right", width=14)

    for var in ordered:
        swing_pct = (var.npv_swing / abs(base_npv) * 100) if base_npv != 0 else 0
        swing_color = "red" if swing_pct > 20 else ("yellow" if swing_pct > 10 else "green")
        table.add_row(
            var.label,
            _fmt_currency(var.npv_at_low, compact=True),
            _fmt_currency(var.npv_at_high, compact=True),
            Text(f"{swing_pct:.1f}%", style=swing_color),
        )
    console.print(table)
    console.print()


def print_monte_carlo_summary(mc) -> None:
    """Print Monte Carlo simulation summary."""
    table = Table(
        title=f"Monte Carlo Simulation — {mc.iterations:,} Iterations",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", width=35)
    table.add_column("Value", justify="right", width=18)

    rows = [
        ("NPV — P10 (pessimistic)", _fmt_currency(mc.npv_p10, compact=True)),
        ("NPV — P50 (median)", _fmt_currency(mc.npv_p50, compact=True)),
        ("NPV — P90 (optimistic)", _fmt_currency(mc.npv_p90, compact=True)),
        ("NPV — Mean", _fmt_currency(mc.npv_mean, compact=True)),
        ("Probability of Positive NPV", _fmt_pct(mc.prob_positive_npv)),
        (f"Probability DSCR < {mc.dscr_threshold:.1f}x", _fmt_pct(mc.prob_dscr_below_threshold)),
    ]
    if mc.irr_values:
        rows += [
            ("IRR — P10", _fmt_pct(mc.irr_p10)),
            ("IRR — P50", _fmt_pct(mc.irr_p50)),
            ("IRR — P90", _fmt_pct(mc.irr_p90)),
        ]

    for metric, value in rows:
        color = "white"
        if "Probability of Positive" in metric:
            color = "green" if mc.prob_positive_npv >= 0.70 else ("yellow" if mc.prob_positive_npv >= 0.50 else "red")
        table.add_row(metric, Text(value, style=color))

    console.print(table)

    if mc.input_npv_correlations:
        console.print("\n  [bold]Input-NPV Correlations:[/bold]")
        for var, corr in sorted(mc.input_npv_correlations.items(), key=lambda x: abs(x[1]), reverse=True):
            bar = "█" * int(abs(corr) * 20)
            direction = "+" if corr > 0 else "-"
            color = "green" if corr > 0 else "red"
            console.print(f"  {var:<30} [{color}]{direction}{bar} {corr:+.3f}[/{color}]")
    console.print()
