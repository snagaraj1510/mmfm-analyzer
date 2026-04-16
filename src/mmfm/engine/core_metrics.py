"""
Core financial metrics.

All calculations are deterministic Python. No AI is used here.
These are the source-of-truth computations — AI narrative must not
contradict these outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
import numpy_financial as npf


@dataclass
class NPVResult:
    value: float
    discount_rate: float
    cash_flows: list[float]
    is_positive: bool


@dataclass
class IRRResult:
    value: Optional[float]
    converged: bool
    cash_flows: list[float]
    message: str


@dataclass
class PaybackResult:
    years: Optional[float]
    reached: bool
    cumulative_cash_flows: list[float]


@dataclass
class DSCRResult:
    """Debt Service Coverage Ratio per year."""
    values: list[float]          # DSCR per year
    years: list[int]
    min_dscr: float
    min_dscr_year: int
    below_threshold: list[int]   # Years where DSCR < threshold


@dataclass
class OperatingMarginResult:
    values: list[float]
    years: list[int]
    average: float
    trend: str                   # "improving" | "declining" | "stable"


def calculate_npv(cash_flows: list[float], discount_rate: float) -> NPVResult:
    """
    Calculate Net Present Value.

    Args:
        cash_flows: List of cash flows starting from year 0 (negative = outflow)
        discount_rate: Annual discount rate as a decimal (e.g., 0.10 for 10%)

    Returns:
        NPVResult with value and metadata

    Raises:
        ValueError: If discount_rate <= -1 (undefined) or cash_flows is empty
    """
    if not cash_flows:
        raise ValueError("cash_flows cannot be empty")
    if discount_rate <= -1:
        raise ValueError(f"discount_rate must be > -1, got {discount_rate}")

    # numpy_financial.npv: first element is period 0 (initial investment)
    value = float(npf.npv(discount_rate, cash_flows))

    return NPVResult(
        value=value,
        discount_rate=discount_rate,
        cash_flows=list(cash_flows),
        is_positive=value > 0,
    )


def calculate_irr(cash_flows: list[float]) -> IRRResult:
    """
    Calculate Internal Rate of Return.

    Args:
        cash_flows: List of cash flows starting from year 0

    Returns:
        IRRResult. If IRR does not converge, converged=False and value=None.
    """
    if not cash_flows:
        raise ValueError("cash_flows cannot be empty")

    # IRR requires at least one sign change
    signs = [1 if cf >= 0 else -1 for cf in cash_flows]
    sign_changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i - 1])

    if sign_changes == 0:
        return IRRResult(
            value=None,
            converged=False,
            cash_flows=list(cash_flows),
            message="No sign change in cash flows — IRR undefined",
        )

    try:
        raw_irr = npf.irr(cash_flows)
        if math.isnan(raw_irr) or math.isinf(raw_irr):
            return IRRResult(
                value=None,
                converged=False,
                cash_flows=list(cash_flows),
                message="IRR did not converge",
            )
        return IRRResult(
            value=float(raw_irr),
            converged=True,
            cash_flows=list(cash_flows),
            message="OK",
        )
    except Exception as exc:
        return IRRResult(
            value=None,
            converged=False,
            cash_flows=list(cash_flows),
            message=str(exc),
        )


def calculate_payback(cash_flows: list[float]) -> PaybackResult:
    """
    Calculate payback period using linear interpolation.

    Args:
        cash_flows: List of cash flows from year 0 onward

    Returns:
        PaybackResult with years (fractional) and whether payback was reached
    """
    if not cash_flows:
        raise ValueError("cash_flows cannot be empty")

    cumulative = []
    running = 0.0
    for cf in cash_flows:
        running += cf
        cumulative.append(running)

    # Check if payback is ever reached
    if cumulative[-1] < 0:
        return PaybackResult(years=None, reached=False, cumulative_cash_flows=cumulative)

    # Find the year where cumulative turns non-negative
    for i, cum in enumerate(cumulative):
        if cum >= 0:
            if i == 0:
                return PaybackResult(years=0.0, reached=True, cumulative_cash_flows=cumulative)
            # Linear interpolation between year i-1 and year i
            prev_cum = cumulative[i - 1]
            this_cf = cash_flows[i]
            if this_cf == 0:
                payback = float(i)
            else:
                fraction = abs(prev_cum) / abs(this_cf)
                payback = (i - 1) + fraction
            return PaybackResult(years=payback, reached=True, cumulative_cash_flows=cumulative)

    return PaybackResult(years=None, reached=False, cumulative_cash_flows=cumulative)


def calculate_dscr(
    net_operating_incomes: list[float],
    debt_services: list[float],
    years: Optional[list[int]] = None,
    warning_threshold: float = 1.2,
) -> DSCRResult:
    """
    Calculate Debt Service Coverage Ratio per year.

    DSCR = Net Operating Income / Total Debt Service

    Args:
        net_operating_incomes: NOI per year
        debt_services: Total debt service per year (must be positive)
        years: Year labels (defaults to 1, 2, 3, ...)
        warning_threshold: Flag years below this DSCR (default 1.2)

    Returns:
        DSCRResult with per-year values and minimum
    """
    if len(net_operating_incomes) != len(debt_services):
        raise ValueError("net_operating_incomes and debt_services must have the same length")

    n = len(net_operating_incomes)
    if years is None:
        years = list(range(1, n + 1))

    dscr_values = []
    for noi, ds in zip(net_operating_incomes, debt_services):
        if ds == 0:
            # No debt service: DSCR is effectively infinite; represent as NaN
            dscr_values.append(float("nan"))
        else:
            dscr_values.append(noi / ds)

    valid_dscr = [v for v in dscr_values if not math.isnan(v)]

    if not valid_dscr:
        min_dscr = float("nan")
        min_year = years[0] if years else 1
    else:
        min_dscr = min(valid_dscr)
        min_idx = dscr_values.index(min_dscr)
        min_year = years[min_idx]

    below = [years[i] for i, v in enumerate(dscr_values) if not math.isnan(v) and v < warning_threshold]

    return DSCRResult(
        values=dscr_values,
        years=list(years),
        min_dscr=min_dscr,
        min_dscr_year=min_year,
        below_threshold=below,
    )


def calculate_operating_margin(
    revenues: list[float],
    opex: list[float],
    years: Optional[list[int]] = None,
) -> OperatingMarginResult:
    """
    Calculate operating margin per year.

    Operating Margin = (Revenue - Opex) / Revenue

    Args:
        revenues: Revenue per year
        opex: Operating expenditure per year
        years: Year labels (defaults to 1, 2, 3, ...)

    Returns:
        OperatingMarginResult with per-year values and trend
    """
    if len(revenues) != len(opex):
        raise ValueError("revenues and opex must have the same length")

    n = len(revenues)
    if years is None:
        years = list(range(1, n + 1))

    margins = []
    for rev, op in zip(revenues, opex):
        if rev == 0:
            margins.append(float("nan"))
        else:
            margins.append((rev - op) / rev)

    valid = [m for m in margins if not math.isnan(m)]
    average = float(np.mean(valid)) if valid else float("nan")

    # Determine trend from first half vs second half
    trend = "stable"
    if len(valid) >= 4:
        mid = len(valid) // 2
        first_half_avg = float(np.mean(valid[:mid]))
        second_half_avg = float(np.mean(valid[mid:]))
        delta = second_half_avg - first_half_avg
        if delta > 0.02:
            trend = "improving"
        elif delta < -0.02:
            trend = "declining"

    return OperatingMarginResult(
        values=margins,
        years=list(years),
        average=average,
        trend=trend,
    )
