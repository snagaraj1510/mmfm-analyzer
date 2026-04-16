"""
Monte Carlo simulation for MMFM Analyzer.

Runs N iterations with randomized input assumptions to produce
probability distributions over NPV, IRR, and DSCR outcomes.
All computations are deterministic given a seed — no AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs, project_cash_flows
from mmfm.engine.core_metrics import calculate_npv, calculate_irr, calculate_dscr


@dataclass
class MonteCarloResult:
    """Results from a Monte Carlo simulation run."""
    iterations: int
    seed: Optional[int]

    # NPV distribution
    npv_values: list[float] = field(default_factory=list)
    npv_p10: float = 0.0
    npv_p50: float = 0.0
    npv_p90: float = 0.0
    npv_mean: float = 0.0
    npv_std: float = 0.0
    prob_positive_npv: float = 0.0

    # IRR distribution
    irr_values: list[float] = field(default_factory=list)
    irr_p10: float = 0.0
    irr_p50: float = 0.0
    irr_p90: float = 0.0

    # DSCR risk
    prob_dscr_below_threshold: float = 0.0
    dscr_threshold: float = 1.2

    # Input correlations with NPV (Pearson r)
    input_npv_correlations: dict[str, float] = field(default_factory=dict)


def run_monte_carlo(
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    iterations: int = 10_000,
    seed: Optional[int] = None,
    discount_rate: float = 0.10,
    inflation_rate: float = 0.05,
    horizon_years: int = 20,
    dscr_threshold: float = 1.2,
    distributions: Optional[dict] = None,
) -> MonteCarloResult:
    """
    Run Monte Carlo simulation over randomized assumptions.

    Default distributions:
    - occupancy_target:      Beta(alpha=7, beta=3)     → mean ~70%, skewed upward
    - capex_overrun_pct:     LogNormal(mean=0.1, sigma=0.3) → right-skewed overruns
    - inflation_rate:        Normal(mu=0.05, sigma=0.02)
    - rental_escalation_rate: Normal(mu=rental_esc, sigma=0.01)
    - opex_escalation_rate:  Normal(mu=opex_esc, sigma=0.01)

    Args:
        revenue: Base revenue inputs (used as distribution centers)
        capex: Base capex inputs
        opex: Base opex inputs
        iterations: Number of simulation runs
        seed: Random seed for reproducibility
        discount_rate: Fixed discount rate for all runs
        inflation_rate: Center of inflation distribution
        horizon_years: Projection horizon
        dscr_threshold: DSCR below which a run is flagged as "at risk"
        distributions: Override default distributions (variable -> (type, params))

    Returns:
        MonteCarloResult with distribution statistics
    """
    rng = np.random.default_rng(seed)

    npv_samples: list[float] = []
    irr_samples: list[float] = []
    dscr_below_count = 0

    # Track inputs for correlation analysis
    occ_samples: list[float] = []
    overrun_samples: list[float] = []
    infl_samples: list[float] = []

    for _ in range(iterations):
        # ── Sample inputs from distributions ──────────────────────────────
        # Occupancy: Beta(7, 3) → mean ~0.70, range (0,1)
        occ = float(np.clip(rng.beta(7, 3), 0.10, 0.99))

        # Capex overrun: LogNormal centered on base overrun
        base_overrun = max(capex.overrun_contingency, 0.01)
        overrun = float(np.clip(rng.lognormal(np.log(base_overrun), 0.3), 0.0, 1.0))

        # Inflation: Normal(mu, sigma)
        infl = float(np.clip(rng.normal(inflation_rate, 0.02), 0.01, 0.40))

        # Escalation rates: Normal around base values
        rent_esc = float(np.clip(rng.normal(revenue.rental_escalation_rate, 0.01), 0.0, 0.20))
        opex_esc = float(np.clip(rng.normal(opex.opex_escalation_rate, 0.01), 0.0, 0.20))

        occ_samples.append(occ)
        overrun_samples.append(overrun)
        infl_samples.append(infl)

        # ── Build inputs for this iteration ───────────────────────────────
        iter_revenue = RevenueInputs(
            base_stall_rental_income=revenue.base_stall_rental_income,
            occupancy_rate=occ * 0.85,          # initial occ = 85% of target
            vendor_fees_annual=revenue.vendor_fees_annual,
            market_levies_annual=revenue.market_levies_annual,
            rental_escalation_rate=rent_esc,
            fee_escalation_rate=rent_esc,
            occupancy_ramp_years=revenue.occupancy_ramp_years,
            occupancy_target=occ,
            other_income_annual=revenue.other_income_annual,
        )
        iter_capex = CapexInputs(
            total_capex=capex.total_capex,
            construction_schedule=capex.construction_schedule,
            overrun_contingency=overrun,
            grant_amount=capex.grant_amount,
            grant_disbursement_year=capex.grant_disbursement_year,
        )
        iter_opex = OpexInputs(
            base_opex=opex.base_opex,
            opex_escalation_rate=opex_esc,
            debt_service_annual=opex.debt_service_annual,
        )

        # ── Compute metrics ────────────────────────────────────────────────
        projection = project_cash_flows(
            iter_revenue, iter_capex, iter_opex,
            horizon_years=horizon_years,
            inflation_rate=infl,
        )
        cash_flows = projection.get_cash_flows()

        npv_res = calculate_npv(cash_flows, discount_rate)
        npv_samples.append(npv_res.value)

        irr_res = calculate_irr(cash_flows)
        if irr_res.converged and irr_res.value is not None:
            irr_samples.append(irr_res.value)

        # DSCR check
        noi = projection.get_noi()
        ds = projection.get_debt_service()
        if any(d > 0 for d in ds):
            dscr_res = calculate_dscr(noi, ds)
            if dscr_res.min_dscr < dscr_threshold:
                dscr_below_count += 1

    # ── Aggregate results ──────────────────────────────────────────────────
    npv_arr = np.array(npv_samples)
    result = MonteCarloResult(
        iterations=iterations,
        seed=seed,
        npv_values=npv_samples,
        npv_p10=float(np.percentile(npv_arr, 10)),
        npv_p50=float(np.percentile(npv_arr, 50)),
        npv_p90=float(np.percentile(npv_arr, 90)),
        npv_mean=float(np.mean(npv_arr)),
        npv_std=float(np.std(npv_arr)),
        prob_positive_npv=float(np.mean(npv_arr > 0)),
        dscr_threshold=dscr_threshold,
        prob_dscr_below_threshold=dscr_below_count / iterations,
    )

    if irr_samples:
        irr_arr = np.array(irr_samples)
        result.irr_values = irr_samples
        result.irr_p10 = float(np.percentile(irr_arr, 10))
        result.irr_p50 = float(np.percentile(irr_arr, 50))
        result.irr_p90 = float(np.percentile(irr_arr, 90))

    # Input-NPV correlations
    if len(occ_samples) == iterations:
        result.input_npv_correlations = {
            "occupancy_target": float(np.corrcoef(occ_samples, npv_samples)[0, 1]),
            "capex_overrun_pct": float(np.corrcoef(overrun_samples, npv_samples)[0, 1]),
            "inflation_rate": float(np.corrcoef(infl_samples, npv_samples)[0, 1]),
        }

    return result
