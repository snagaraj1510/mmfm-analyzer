"""
Multi-year cash flow projection engine.

Generates year-by-year cash flow projections from revenue, capex, and opex models.
All calculations are deterministic. No AI involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RevenueInputs:
    """Inputs for revenue projection."""
    base_stall_rental_income: float        # Annual stall rental at 100% occupancy
    occupancy_rate: float                  # Initial occupancy (0-1)
    vendor_fees_annual: float              # Annual vendor fee income
    market_levies_annual: float            # Annual market levy income
    rental_escalation_rate: float          # Annual escalation rate for rentals
    fee_escalation_rate: float             # Annual escalation rate for fees
    occupancy_ramp_years: int = 3          # Years to reach target occupancy
    occupancy_target: float = 0.85        # Target occupancy after ramp
    other_income_annual: float = 0.0
    # Fee collection rate: fraction of billed revenue actually collected.
    # Source data: Lusaka system avg 0.38, Mandevu worst case 0.10, best case 1.0.
    fee_collection_rate: float = 1.0      # Default: full collection (conservative assumption)


@dataclass
class CapexInputs:
    """Inputs for capital expenditure."""
    total_capex: float                     # Total capital expenditure
    construction_schedule: dict[int, float]  # {year: fraction of capex}
    overrun_contingency: float = 0.10      # 10% default contingency
    grant_amount: float = 0.0             # Grant funding
    grant_disbursement_year: int = 0      # Year grant is received


@dataclass
class OpexInputs:
    """Inputs for operating expenditure."""
    base_opex: float                       # Annual operating costs at Year 1
    opex_escalation_rate: float            # Annual opex escalation
    debt_service_annual: float = 0.0       # Annual debt service (principal + interest)


@dataclass
class YearlyProjection:
    year: int
    revenue: float
    capex: float
    opex: float
    debt_service: float
    net_operating_income: float    # Revenue - Opex
    free_cash_flow: float          # NOI - Capex - Debt Service
    cumulative_cash_flow: float
    occupancy_rate: float
    operating_margin: float


@dataclass
class CashFlowProjection:
    years: list[YearlyProjection] = field(default_factory=list)
    horizon_years: int = 20
    base_currency: str = "USD"

    def get_cash_flows(self) -> list[float]:
        """Return list of free cash flows suitable for NPV/IRR calculations."""
        return [y.free_cash_flow for y in self.years]

    def get_noi(self) -> list[float]:
        return [y.net_operating_income for y in self.years]

    def get_revenues(self) -> list[float]:
        return [y.revenue for y in self.years]

    def get_opex(self) -> list[float]:
        return [y.opex for y in self.years]

    def get_debt_service(self) -> list[float]:
        return [y.debt_service for y in self.years]


def project_cash_flows(
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    horizon_years: int = 20,
    inflation_rate: float = 0.05,
    start_year: int = 2025,
    base_currency: str = "USD",
) -> CashFlowProjection:
    """
    Generate year-by-year cash flow projection.

    Year 0 is the construction / pre-operational year.
    Revenue begins in Year 1.

    Args:
        revenue: Revenue model inputs
        capex: Capital expenditure inputs
        opex: Operating expenditure inputs
        horizon_years: Number of projection years (including Year 0)
        inflation_rate: General inflation rate for escalation
        start_year: Calendar year corresponding to Year 0
        base_currency: Currency label for output

    Returns:
        CashFlowProjection with yearly detail
    """
    projection = CashFlowProjection(horizon_years=horizon_years, base_currency=base_currency)
    cumulative = 0.0

    total_capex_with_overrun = capex.total_capex * (1 + capex.overrun_contingency)

    for t in range(horizon_years + 1):
        cal_year = start_year + t

        # ── CAPEX ──────────────────────────────────────────────────────────
        capex_fraction = capex.construction_schedule.get(t, 0.0)
        year_capex = total_capex_with_overrun * capex_fraction

        # Grant offsets capex in disbursement year
        if t == capex.grant_disbursement_year and capex.grant_amount > 0:
            year_capex = max(0.0, year_capex - capex.grant_amount)

        # ── REVENUE (operational years only) ────────────────────────────
        if t == 0:
            year_revenue = 0.0
            year_occupancy = 0.0
        else:
            # Occupancy ramp-up
            if t <= revenue.occupancy_ramp_years:
                ramp_progress = t / revenue.occupancy_ramp_years
                year_occupancy = (
                    revenue.occupancy_rate
                    + ramp_progress * (revenue.occupancy_target - revenue.occupancy_rate)
                )
            else:
                year_occupancy = revenue.occupancy_target

            rental_factor = (1 + revenue.rental_escalation_rate) ** (t - 1)
            fee_factor = (1 + revenue.fee_escalation_rate) ** (t - 1)
            inflation_factor = (1 + inflation_rate) ** (t - 1)

            stall_rental = revenue.base_stall_rental_income * year_occupancy * rental_factor
            vendor_fees = revenue.vendor_fees_annual * fee_factor
            levies = revenue.market_levies_annual * inflation_factor
            other = revenue.other_income_annual * inflation_factor

            year_revenue = (stall_rental + vendor_fees + levies + other) * revenue.fee_collection_rate

        # ── OPEX ──────────────────────────────────────────────────────────
        if t == 0:
            year_opex = 0.0
            year_debt_service = 0.0
        else:
            opex_factor = (1 + opex.opex_escalation_rate) ** (t - 1)
            year_opex = opex.base_opex * opex_factor
            year_debt_service = opex.debt_service_annual

        # ── DERIVED METRICS ───────────────────────────────────────────────
        noi = year_revenue - year_opex
        fcf = noi - year_capex - year_debt_service
        cumulative += fcf
        op_margin = (noi / year_revenue) if year_revenue > 0 else 0.0

        projection.years.append(YearlyProjection(
            year=cal_year,
            revenue=year_revenue,
            capex=year_capex,
            opex=year_opex,
            debt_service=year_debt_service,
            net_operating_income=noi,
            free_cash_flow=fcf,
            cumulative_cash_flow=cumulative,
            occupancy_rate=year_occupancy,
            operating_margin=op_margin,
        ))

    return projection
