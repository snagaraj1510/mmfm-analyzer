"""
PDF report generation for MMFM Analyzer.

Generates a formatted PDF report using matplotlib for charts
and reportlab/matplotlib for PDF rendering.
Falls back to a text-based summary if reportlab is not installed.
"""

from __future__ import annotations

import io
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_pdf import PdfPages

from mmfm.engine.core_metrics import NPVResult, IRRResult, PaybackResult
from mmfm.engine.projections import CashFlowProjection
from mmfm.engine.scenarios import ScenarioComparison
from mmfm.engine.sensitivity import SensitivityResult


def _fmt_currency(value: float, compact: bool = True) -> str:
    if math.isnan(value) or math.isinf(value):
        return "N/A"
    if compact:
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:.1f}M"
        if abs(value) >= 1_000:
            return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _fmt_pct(value: float) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return "N/A"
    return f"{value * 100:.1f}%"


def _add_title_page(pdf: PdfPages, title: str, subtitle: str, source_file: str) -> None:
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.axis("off")
    fig.patch.set_facecolor("#1F4E79")

    ax.text(0.5, 0.65, title, transform=ax.transAxes,
            fontsize=28, fontweight="bold", color="white",
            ha="center", va="center")
    ax.text(0.5, 0.52, subtitle, transform=ax.transAxes,
            fontsize=14, color="#AED6F1",
            ha="center", va="center")
    ax.text(0.5, 0.40, f"Source: {source_file}", transform=ax.transAxes,
            fontsize=10, color="#85C1E9",
            ha="center", va="center")
    ax.text(0.5, 0.30, f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            transform=ax.transAxes, fontsize=10, color="#85C1E9",
            ha="center", va="center")

    pdf.savefig(fig, facecolor=fig.get_facecolor())
    plt.close(fig)


def _add_metrics_page(
    pdf: PdfPages,
    npv: NPVResult,
    irr: IRRResult,
    payback: PaybackResult,
    currency: str = "USD",
) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 4))
    fig.suptitle("Core Financial Metrics", fontsize=16, fontweight="bold", y=1.02)

    metrics = [
        ("NPV", _fmt_currency(npv.value), "green" if npv.is_positive else "red"),
        ("IRR", _fmt_pct(irr.value) if irr.converged and irr.value else "N/A", "steelblue"),
        ("Payback", f"{payback.years:.1f} yrs" if payback.reached and payback.years else "N/A", "steelblue"),
    ]

    for ax, (label, value, color) in zip(axes, metrics):
        ax.axis("off")
        circle = plt.Circle((0.5, 0.55), 0.35, color=color, alpha=0.15, transform=ax.transAxes)
        ax.add_patch(circle)
        ax.text(0.5, 0.58, value, transform=ax.transAxes,
                fontsize=20, fontweight="bold", color=color,
                ha="center", va="center")
        ax.text(0.5, 0.20, label, transform=ax.transAxes,
                fontsize=12, color="gray",
                ha="center", va="center")

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _add_cash_flow_chart(pdf: PdfPages, projection: CashFlowProjection) -> None:
    years = [y.year for y in projection.years]
    revenues = [y.revenue / 1e3 for y in projection.years]
    opex = [y.opex / 1e3 for y in projection.years]
    fcf = [y.free_cash_flow / 1e3 for y in projection.years]
    cumulative = [y.cumulative_cash_flow / 1e3 for y in projection.years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7))
    fig.suptitle("Cash Flow Projection", fontsize=16, fontweight="bold")

    # Revenue vs Opex bar chart
    x = range(len(years))
    width = 0.35
    ax1.bar([i - width/2 for i in x], revenues, width, label="Revenue", color="steelblue", alpha=0.8)
    ax1.bar([i + width/2 for i in x], opex, width, label="Opex", color="salmon", alpha=0.8)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("USD (000s)")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels([str(y) for y in years], rotation=45, fontsize=7)
    ax1.legend()
    ax1.grid(axis="y", alpha=0.3)

    # Cumulative FCF line chart
    colors = ["green" if v >= 0 else "red" for v in cumulative]
    ax2.plot(years, cumulative, color="steelblue", linewidth=2, marker="o", markersize=3)
    ax2.fill_between(years, cumulative,
                     where=[v >= 0 for v in cumulative], alpha=0.2, color="green", label="Positive")
    ax2.fill_between(years, cumulative,
                     where=[v < 0 for v in cumulative], alpha=0.2, color="red", label="Negative")
    ax2.axhline(y=0, color="black", linestyle="--", linewidth=0.8)
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Cumulative FCF (USD 000s)")
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _add_scenario_chart(pdf: PdfPages, comparison: ScenarioComparison) -> None:
    names = list(comparison.results.keys())
    npvs = [comparison.results[n].npv.value / 1e3 for n in names]
    irrs = [
        comparison.results[n].irr.value * 100
        if comparison.results[n].irr.converged and comparison.results[n].irr.value
        else 0
        for n in names
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("Scenario Comparison", fontsize=16, fontweight="bold")

    colors_map = {"base": "steelblue", "optimistic": "green", "pessimistic": "red"}
    bar_colors = [colors_map.get(n, "steelblue") for n in names]

    ax1.bar(names, npvs, color=bar_colors, alpha=0.8)
    ax1.axhline(y=0, color="black", linestyle="--", linewidth=0.8)
    ax1.set_title("NPV (USD 000s)")
    ax1.set_ylabel("USD (000s)")
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(names, irrs, color=bar_colors, alpha=0.8)
    ax2.set_title("IRR (%)")
    ax2.set_ylabel("IRR (%)")
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _add_tornado_chart(pdf: PdfPages, sensitivity: SensitivityResult) -> None:
    ordered = sensitivity.tornado_order()[:8]
    base_npv = sensitivity.base_npv

    labels = [v.label for v in ordered]
    lows = [(v.npv_at_low - base_npv) / 1e3 for v in ordered]
    highs = [(v.npv_at_high - base_npv) / 1e3 for v in ordered]

    fig, ax = plt.subplots(figsize=(11, 5))
    fig.suptitle(f"Tornado Chart — NPV Sensitivity (Base NPV: {_fmt_currency(base_npv)})",
                 fontsize=14, fontweight="bold")

    y_pos = range(len(labels))
    ax.barh(list(y_pos), lows, color="salmon", alpha=0.8, label="Low scenario")
    ax.barh(list(y_pos), highs, color="steelblue", alpha=0.8, label="High scenario")
    ax.axvline(x=0, color="black", linestyle="--", linewidth=0.8)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels[::-1] if False else labels)
    ax.set_xlabel("NPV Change from Base (USD 000s)")
    ax.legend()
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def export_pdf(
    output_path: Path | str,
    npv: NPVResult,
    irr: IRRResult,
    payback: PaybackResult,
    projection: CashFlowProjection,
    source_file: str = "",
    comparison: Optional[ScenarioComparison] = None,
    sensitivity: Optional[SensitivityResult] = None,
    narrative: Optional[dict] = None,
) -> None:
    """
    Export analysis results to a formatted PDF report.

    Args:
        output_path: Where to save the .pdf file
        npv, irr, payback: Core metric results
        projection: Cash flow projection
        source_file: Source model filename
        comparison: Optional scenario comparison
        sensitivity: Optional sensitivity results
        narrative: Optional AI narrative dict
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    title = "Municipal Market Financial Analysis"
    subtitle = f"NPV: {_fmt_currency(npv.value)}  |  IRR: {_fmt_pct(irr.value) if irr.converged and irr.value else 'N/A'}  |  Payback: {f'{payback.years:.1f} yrs' if payback.reached and payback.years else 'N/A'}"

    with PdfPages(str(path)) as pdf:
        _add_title_page(pdf, title, subtitle, source_file or "N/A")
        _add_metrics_page(pdf, npv, irr, payback, currency=projection.base_currency)
        _add_cash_flow_chart(pdf, projection)

        if comparison:
            _add_scenario_chart(pdf, comparison)
        if sensitivity:
            _add_tornado_chart(pdf, sensitivity)

        # Narrative page (text only)
        if narrative:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis("off")
            summary = narrative.get("executive_summary", "")[:1200]
            ax.text(0.05, 0.95, "Executive Summary", transform=ax.transAxes,
                    fontsize=14, fontweight="bold", va="top")
            ax.text(0.05, 0.88, summary, transform=ax.transAxes,
                    fontsize=9, va="top", wrap=True,
                    bbox=dict(boxstyle="round", facecolor="lightblue", alpha=0.1))

            risks = narrative.get("key_risks", [])
            if risks:
                risk_text = "\n".join(f"• {r}" for r in risks[:3])
                ax.text(0.05, 0.40, "Key Risks", transform=ax.transAxes,
                        fontsize=12, fontweight="bold", va="top")
                ax.text(0.05, 0.34, risk_text, transform=ax.transAxes,
                        fontsize=9, va="top")

            rec = narrative.get("recommendation", "")
            conf = narrative.get("confidence_level", "")
            if rec:
                ax.text(0.05, 0.15, f"Recommendation: {rec.upper()}  |  Confidence: {conf.upper()}",
                        transform=ax.transAxes, fontsize=11, fontweight="bold",
                        color="green" if "proceed" in rec else "red", va="top")

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        # Metadata
        d = pdf.infodict()
        d["Title"] = title
        d["Author"] = "MMFM Analyzer"
        d["Subject"] = "Municipal Market Financial Analysis"
