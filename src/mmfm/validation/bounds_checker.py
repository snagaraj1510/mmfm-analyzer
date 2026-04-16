"""
Numerical boundary validation for MMFM outputs.

Every number in AI-generated output is checked against plausible ranges.
Ranges are grounded in MAP source data (East Africa municipal markets).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BoundsStatus(Enum):
    PASS = "PASS"
    WARNING = "WARNING"   # Within 10% of a boundary
    FAIL = "FAIL"         # Outside bounds — likely error or hallucination


@dataclass
class BoundsResult:
    metric_name: str
    value: float
    status: BoundsStatus
    min_bound: Optional[float]
    max_bound: Optional[float]
    message: str


# ── Plausible bounds grounded in MAP source data ─────────────────────────────
PLAUSIBLE_BOUNDS: dict[str, dict] = {
    # Core financial metrics
    "npv":              {"min": -1e9,   "max": 1e9,    "unit": "currency"},
    "irr":              {"min": -0.50,  "max": 2.0,    "unit": "ratio"},
    "payback_years":    {"min": 0.5,    "max": 50,     "unit": "years"},
    "dscr":             {"min": 0.0,    "max": 10.0,   "unit": "ratio"},
    "operating_margin": {"min": -1.0,   "max": 0.95,   "unit": "ratio"},

    # Market-specific — East Africa municipal markets
    "occupancy_rate":           {"min": 0.10, "max": 0.99,       "unit": "ratio"},
    "annual_revenue_usd":       {"min": 1000, "max": 50_000_000, "unit": "USD"},
    "stall_monthly_rent_usd":   {"min": 1,    "max": 5000,       "unit": "USD",
                                 "typical_min": 30, "typical_max": 35,
                                 "notes": "Field data: $30-35/month typical"},
    "vendor_count":             {"min": 10,   "max": 10000,      "unit": "count"},
    "capex_total_usd":          {"min": 10000, "max": 500_000_000, "unit": "USD"},
    "construction_months":      {"min": 1,    "max": 120,        "unit": "months"},

    # Fee collection — grounded in MAP field data
    "fee_collection_rate":      {"min": 0.10, "max": 1.0, "unit": "ratio",
                                 "typical": 0.38,
                                 "notes": "Field data: system avg 0.38; worst case 0.10"},

    # Willingness-to-pay — MAP field data
    "incremental_wtp_usd_per_stall_per_month": {
        "min": 0, "max": 50, "unit": "USD/stall/month",
        "typical": 5,
        "notes": "Field data: ~$5/stall/month typical incremental WTP",
    },

    # Macroeconomic — Kenya, Tanzania, Mozambique
    "inflation_rate":       {"min": 0.0,  "max": 0.40, "unit": "ratio"},
    "discount_rate":        {"min": 0.01, "max": 0.30, "unit": "ratio"},
    "fx_rate_kes_usd":      {"min": 50,   "max": 300,  "unit": "KES/USD",
                             "typical": 129.3, "notes": "April 2026 reference rate"},
    "fx_rate_tzs_usd":      {"min": 1000, "max": 5000, "unit": "TZS/USD"},
}


def check_bounds(metric_name: str, value: float) -> BoundsResult:
    """
    Check a metric value against its plausible bounds.

    Returns:
        BoundsResult with PASS, WARNING (near boundary), or FAIL (outside bounds)
    """
    if math.isnan(value) or math.isinf(value):
        return BoundsResult(
            metric_name=metric_name, value=value,
            status=BoundsStatus.FAIL,
            min_bound=None, max_bound=None,
            message=f"Value is NaN or Inf — invalid",
        )

    spec = PLAUSIBLE_BOUNDS.get(metric_name)
    if spec is None:
        return BoundsResult(
            metric_name=metric_name, value=value,
            status=BoundsStatus.PASS,
            min_bound=None, max_bound=None,
            message="No bounds defined for this metric",
        )

    min_b = spec.get("min")
    max_b = spec.get("max")

    # Check hard bounds
    if min_b is not None and value < min_b:
        return BoundsResult(
            metric_name=metric_name, value=value,
            status=BoundsStatus.FAIL,
            min_bound=min_b, max_bound=max_b,
            message=f"{value:.4f} < min bound {min_b}",
        )
    if max_b is not None and value > max_b:
        return BoundsResult(
            metric_name=metric_name, value=value,
            status=BoundsStatus.FAIL,
            min_bound=min_b, max_bound=max_b,
            message=f"{value:.4f} > max bound {max_b}",
        )

    # Check warning zone (within 10% of boundary)
    range_size = (max_b - min_b) if (min_b is not None and max_b is not None) else None
    if range_size and range_size > 0:
        warning_margin = range_size * 0.10
        if min_b is not None and value < min_b + warning_margin:
            return BoundsResult(
                metric_name=metric_name, value=value,
                status=BoundsStatus.WARNING,
                min_bound=min_b, max_bound=max_b,
                message=f"{value:.4f} is within 10% of min bound {min_b}",
            )
        if max_b is not None and value > max_b - warning_margin:
            return BoundsResult(
                metric_name=metric_name, value=value,
                status=BoundsStatus.WARNING,
                min_bound=min_b, max_bound=max_b,
                message=f"{value:.4f} is within 10% of max bound {max_b}",
            )

    return BoundsResult(
        metric_name=metric_name, value=value,
        status=BoundsStatus.PASS,
        min_bound=min_b, max_bound=max_b,
        message="Within plausible bounds",
    )


def check_all_bounds(metrics: dict) -> dict[str, BoundsResult]:
    """Check bounds for all metrics in a dict. Returns dict of results."""
    return {name: check_bounds(name, float(value))
            for name, value in metrics.items()
            if isinstance(value, (int, float))}
