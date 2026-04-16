"""
Multi-year cash flow projection engine.

Generates year-by-year cash flow projections from revenue, capex, and opex models.
All calculations are deterministic. No AI involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DebtStructure:
    """
    Structured debt inputs for auto-calculating annual debt service.
    Supports a senior + concessional tranche common in development finance.
    """
    senior_debt_amount: float = 0.0
    senior_rate: float = 0.10
    senior_tenor_years: int = 8
    subordinate_debt_amount: float = 0.0
    subordinate_rate: float = 0.065
    subordinate_tenor_years: int = 10


def calculate_debt_service(debt: DebtStructure) -> float:
    """
    Calculate combined annual debt service using annuity formula.
    Returns 0.0 if both amounts are zero.
    """
    def _annuity(principal: float, rate: float, n: int) -> float:
        if principal <= 0 or n <= 0:
            return 0.0
        if rate == 0:
            return principal / n
        return principal * rate * (1 + rate) ** n / ((1 + rate) ** n - 1)

    return (
        _annuity(debt.senior_debt_amount, debt.senior_rate, debt.senior_tenor_years)
        + _annuity(debt.subordinate_debt_amount, debt.subordinate_rate, debt.subordinate_tenor_years)
    )


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

    # ── Revenue model ─────────────────────────────────────────────────────────
    # "simple"         : existing behaviour (base_stall_rental_income × occupancy)
    # "facility_types" : lock-up / stall / pitch with per-type utilisation + collection
    # "produce"        : commission on wholesale produce throughput
    # "combined"       : facility_types + produce
    revenue_model: str = "simple"

    # ── Facility type breakdown ───────────────────────────────────────────────
    lockup_count: int = 0
    lockup_utilization: float = 0.88
    lockup_collection_rate: float = 0.46      # industry benchmark
    lockup_monthly_rent_usd: float = 25.0

    stall_count: int = 0
    stall_utilization: float = 0.56
    stall_collection_rate: float = 0.21       # industry benchmark
    stall_monthly_rent_usd: float = 5.0

    pitch_count: int = 0
    pitch_utilization: float = 0.49
    pitch_collection_rate: float = 0.23       # industry benchmark
    pitch_monthly_rent_usd: float = 3.0

    # ── Produce / wholesale ───────────────────────────────────────────────────
    produce_throughput_tonnes: float = 0.0
    produce_price_usd_per_tonne: float = 380.0
    commission_rate: float = 0.05
    food_waste_factor: float = 0.20
    produce_price_escalation: float = 0.08


@dataclass
class CapexInputs:
    """Inputs for capital expenditure."""
    total_capex: float                     # Total capital expenditure
    construction_schedule: dict[int, float]  # {year: fraction of capex}
    overrun_contingency: float = 0.10      # 10% default contingency
    grant_amount: float = 0.0             # Grant funding
    grant_disbursement_year: int = 0      # Year grant is received

    # ── Cold storage module ───────────────────────────────────────────────────
    cold_storage_units: int = 0
    cold_storage_cost_per_m3: float = 1527.78   # industry benchmark
    cold_storage_m3_per_unit: float = 18.0
    cold_storage_lead_time_months: int = 6

    # ── Solar PV module ───────────────────────────────────────────────────────
    solar_pv_kw: float = 0.0
    solar_pv_cost_per_kw: float = 1070.0        # industry benchmark
    solar_pv_lead_time_months: int = 3


@dataclass
class OpexInputs:
    """Inputs for operating expenditure."""
    base_opex: float                       # Annual operating costs at Year 1
    opex_escalation_rate: float            # Annual opex escalation
    debt_service_annual: float = 0.0       # Annual debt service (principal + interest)

    # ── OpEx model ────────────────────────────────────────────────────────────
    # "fixed"       : base_opex × escalation (existing behaviour)
    # "pct_revenue" : opex = % of revenue (scales with market size)
    opex_model: str = "fixed"
    cost_escalation_rate: float = 0.05   # separate from fee escalation

    # ── % of revenue breakdown (used when opex_model == "pct_revenue") ────────
    personnel_pct: float = 0.33
    operations_pct: float = 0.22
    rm_pct: float = 0.06
    finance_admin_pct: float = 0.07

    # ── Technology O&M ────────────────────────────────────────────────────────
    cold_storage_utilization: float = 0.55
    cold_storage_om_per_tonne: float = 93.0    # USD/tonne/year
    solar_pv_om_per_kw: float = 53.50          # USD/kW/year


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

        # Technology modules deploy in Year 1 (lead times < 12 months)
        if t == 1:
            year_capex += (
                capex.cold_storage_units * capex.cold_storage_m3_per_unit * capex.cold_storage_cost_per_m3
                + capex.solar_pv_kw * capex.solar_pv_cost_per_kw
            )

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

            if revenue.revenue_model == "facility_types":
                lockup_rev = (revenue.lockup_count * revenue.lockup_utilization
                              * revenue.lockup_collection_rate
                              * revenue.lockup_monthly_rent_usd * 12 * rental_factor)
                stall_rev = (revenue.stall_count * revenue.stall_utilization
                             * revenue.stall_collection_rate
                             * revenue.stall_monthly_rent_usd * 12 * rental_factor)
                pitch_rev = (revenue.pitch_count * revenue.pitch_utilization
                             * revenue.pitch_collection_rate
                             * revenue.pitch_monthly_rent_usd * 12 * rental_factor)
                year_revenue = lockup_rev + stall_rev + pitch_rev

            elif revenue.revenue_model == "produce":
                price_factor = (1 + revenue.produce_price_escalation) ** (t - 1)
                effective_throughput = revenue.produce_throughput_tonnes * (1 - revenue.food_waste_factor)
                year_revenue = (effective_throughput * revenue.produce_price_usd_per_tonne
                                * price_factor * revenue.commission_rate)

            elif revenue.revenue_model == "combined":
                lockup_rev = (revenue.lockup_count * revenue.lockup_utilization
                              * revenue.lockup_collection_rate
                              * revenue.lockup_monthly_rent_usd * 12 * rental_factor)
                stall_rev = (revenue.stall_count * revenue.stall_utilization
                             * revenue.stall_collection_rate
                             * revenue.stall_monthly_rent_usd * 12 * rental_factor)
                pitch_rev = (revenue.pitch_count * revenue.pitch_utilization
                             * revenue.pitch_collection_rate
                             * revenue.pitch_monthly_rent_usd * 12 * rental_factor)
                price_factor = (1 + revenue.produce_price_escalation) ** (t - 1)
                effective_throughput = revenue.produce_throughput_tonnes * (1 - revenue.food_waste_factor)
                produce_rev = (effective_throughput * revenue.produce_price_usd_per_tonne
                               * price_factor * revenue.commission_rate)
                year_revenue = lockup_rev + stall_rev + pitch_rev + produce_rev

            else:  # "simple" — unchanged existing behaviour
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
            esc_rate = opex.cost_escalation_rate
            opex_factor = (1 + esc_rate) ** (t - 1)

            if opex.opex_model == "pct_revenue" and year_revenue > 0:
                total_pct = (opex.personnel_pct + opex.operations_pct
                             + opex.rm_pct + opex.finance_admin_pct)
                year_opex = year_revenue * total_pct
            else:
                year_opex = opex.base_opex * opex_factor

            # Technology O&M
            if capex.cold_storage_units > 0:
                stored_tonnes = (capex.cold_storage_units * capex.cold_storage_m3_per_unit
                                 * 0.1667 * opex.cold_storage_utilization * 365 / 1000)
                year_opex += stored_tonnes * opex.cold_storage_om_per_tonne * opex_factor
            if capex.solar_pv_kw > 0:
                year_opex += capex.solar_pv_kw * opex.solar_pv_om_per_kw * opex_factor

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
