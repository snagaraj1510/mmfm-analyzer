"""
Scenario engine for MMFM Analyzer.

Defines built-in scenarios (base, optimistic, pessimistic) and runs
financial projections under each scenario, returning comparable results.
All computations are deterministic — no AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from mmfm.engine.projections import (
    RevenueInputs,
    CapexInputs,
    OpexInputs,
    CashFlowProjection,
    project_cash_flows,
)
from mmfm.engine.core_metrics import (
    calculate_npv,
    calculate_irr,
    calculate_payback,
    calculate_dscr,
    calculate_operating_margin,
    NPVResult,
    IRRResult,
    PaybackResult,
    DSCRResult,
    OperatingMarginResult,
)


@dataclass
class ScenarioParams:
    """Parameters that vary across scenarios."""
    name: str
    occupancy_rate: float               # Initial occupancy (0-1)
    occupancy_target: float             # Target occupancy after ramp
    rental_escalation_rate: float       # Annual rental escalation
    fee_escalation_rate: float          # Annual fee escalation
    capex_overrun_pct: float            # e.g. 0.10 = 10% overrun
    grant_disbursement_delay_years: int # Delay in grant receipt (0 = on schedule)
    # Fee collection rate calibrated from MAP field data:
    #   pessimistic: 0.38 (system average), floor: 0.10 (worst case)
    #   base: ~0.65 (below-average collection), optimistic: ~0.85 (well-managed market)
    fee_collection_rate: float = 1.0   # Fraction of billed revenue collected
    description: str = ""


# ── Built-in scenarios ──────────────────────────────────────────────────────

BASE_SCENARIO = ScenarioParams(
    name="base",
    occupancy_rate=0.60,
    occupancy_target=0.70,
    rental_escalation_rate=0.06,    # CPI + 1%
    fee_escalation_rate=0.06,
    capex_overrun_pct=0.10,
    grant_disbursement_delay_years=0,
    fee_collection_rate=0.65,       # Below-average collection, realistic for developing market
    description="Base case: moderate assumptions, 10% capex contingency",
)

OPTIMISTIC_SCENARIO = ScenarioParams(
    name="optimistic",
    occupancy_rate=0.70,
    occupancy_target=0.85,
    rental_escalation_rate=0.08,    # CPI + 3%
    fee_escalation_rate=0.08,
    capex_overrun_pct=0.00,
    grant_disbursement_delay_years=0,
    fee_collection_rate=0.85,       # Well-managed market
    description="Optimistic: high occupancy, on-budget construction, early grant",
)

PESSIMISTIC_SCENARIO = ScenarioParams(
    name="pessimistic",
    occupancy_rate=0.40,
    occupancy_target=0.50,
    rental_escalation_rate=0.05,    # CPI only
    fee_escalation_rate=0.05,
    capex_overrun_pct=0.25,
    grant_disbursement_delay_years=1,
    fee_collection_rate=0.38,       # Lusaka system average — on-the-ground reality
    description="Pessimistic: low occupancy, 25% overrun, 1-year grant delay",
)

BUILT_IN_SCENARIOS: dict[str, ScenarioParams] = {
    "base": BASE_SCENARIO,
    "optimistic": OPTIMISTIC_SCENARIO,
    "pessimistic": PESSIMISTIC_SCENARIO,
}


@dataclass
class ScenarioResult:
    """Full financial results for a single scenario."""
    scenario: ScenarioParams
    projection: CashFlowProjection
    npv: NPVResult
    irr: IRRResult
    payback: PaybackResult
    dscr: DSCRResult
    operating_margin: OperatingMarginResult


@dataclass
class ScenarioComparison:
    """Side-by-side comparison of multiple scenario results."""
    results: dict[str, ScenarioResult] = field(default_factory=dict)

    def npv_ranking(self) -> list[str]:
        """Return scenario names sorted by NPV descending."""
        return sorted(
            self.results.keys(),
            key=lambda s: self.results[s].npv.value,
            reverse=True,
        )

    def summary_table(self) -> list[dict]:
        """Return list of dicts suitable for tabular display."""
        rows = []
        for name, result in self.results.items():
            rows.append({
                "scenario": name,
                "npv": result.npv.value,
                "irr": result.irr.value,
                "payback_years": result.payback.years,
                "min_dscr": result.dscr.min_dscr,
                "avg_operating_margin": result.operating_margin.average,
            })
        return rows


def load_custom_scenario(yaml_path: Path | str) -> ScenarioParams:
    """
    Load a custom scenario from a YAML file.

    Expected YAML format:
    ```yaml
    name: my_scenario
    occupancy_rate: 0.65
    occupancy_target: 0.75
    rental_escalation_rate: 0.07
    fee_escalation_rate: 0.07
    capex_overrun_pct: 0.15
    grant_disbursement_delay_years: 0
    description: "My custom scenario"
    ```
    """
    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Custom scenario file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return ScenarioParams(**data)


def run_scenario(
    params: ScenarioParams,
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    horizon_years: int = 20,
    discount_rate: float = 0.10,
    inflation_rate: float = 0.05,
    start_year: int = 2025,
    base_currency: str = "USD",
) -> ScenarioResult:
    """
    Run a single scenario and return full financial results.

    The scenario params override the base revenue/capex assumptions.
    """
    # Apply scenario overrides to inputs
    scenario_revenue = RevenueInputs(
        base_stall_rental_income=revenue.base_stall_rental_income,
        occupancy_rate=params.occupancy_rate,
        vendor_fees_annual=revenue.vendor_fees_annual,
        market_levies_annual=revenue.market_levies_annual,
        rental_escalation_rate=params.rental_escalation_rate,
        fee_escalation_rate=params.fee_escalation_rate,
        occupancy_ramp_years=revenue.occupancy_ramp_years,
        occupancy_target=params.occupancy_target,
        other_income_annual=revenue.other_income_annual,
        fee_collection_rate=params.fee_collection_rate,
    )

    scenario_capex = CapexInputs(
        total_capex=capex.total_capex,
        construction_schedule=capex.construction_schedule,
        overrun_contingency=params.capex_overrun_pct,
        grant_amount=capex.grant_amount,
        grant_disbursement_year=capex.grant_disbursement_year + params.grant_disbursement_delay_years,
    )

    projection = project_cash_flows(
        revenue=scenario_revenue,
        capex=scenario_capex,
        opex=opex,
        horizon_years=horizon_years,
        inflation_rate=inflation_rate,
        start_year=start_year,
        base_currency=base_currency,
    )

    cash_flows = projection.get_cash_flows()
    revenues = projection.get_revenues()
    opex_list = projection.get_opex()
    noi_list = projection.get_noi()
    debt_service_list = projection.get_debt_service()
    years = [y.year for y in projection.years]

    npv_result = calculate_npv(cash_flows, discount_rate)
    irr_result = calculate_irr(cash_flows)
    payback_result = calculate_payback(cash_flows)
    dscr_result = calculate_dscr(noi_list, debt_service_list, years=years)
    margin_result = calculate_operating_margin(revenues, opex_list, years=years)

    return ScenarioResult(
        scenario=params,
        projection=projection,
        npv=npv_result,
        irr=irr_result,
        payback=payback_result,
        dscr=dscr_result,
        operating_margin=margin_result,
    )


def run_all_scenarios(
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    custom_params: Optional[ScenarioParams] = None,
    **kwargs,
) -> ScenarioComparison:
    """
    Run base, optimistic, and pessimistic scenarios (plus optional custom).

    Returns a ScenarioComparison with all results.
    """
    comparison = ScenarioComparison()

    scenarios_to_run = dict(BUILT_IN_SCENARIOS)
    if custom_params:
        scenarios_to_run[custom_params.name] = custom_params

    for name, params in scenarios_to_run.items():
        comparison.results[name] = run_scenario(params, revenue, capex, opex, **kwargs)

    return comparison
