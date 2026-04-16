"""Tests for Monte Carlo simulation."""

from __future__ import annotations

import pytest

from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
from mmfm.engine.monte_carlo import run_monte_carlo


@pytest.fixture
def base_inputs():
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


class TestMonteCarlo:
    def test_basic_run_completes(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=100, seed=42, horizon_years=10)
        assert result.iterations == 100
        assert len(result.npv_values) == 100

    def test_seeded_run_is_reproducible(self, base_inputs):
        revenue, capex, opex = base_inputs
        r1 = run_monte_carlo(revenue, capex, opex, iterations=50, seed=42, horizon_years=10)
        r2 = run_monte_carlo(revenue, capex, opex, iterations=50, seed=42, horizon_years=10)
        assert r1.npv_p50 == r2.npv_p50
        assert r1.npv_p10 == r2.npv_p10

    def test_different_seeds_produce_different_results(self, base_inputs):
        revenue, capex, opex = base_inputs
        r1 = run_monte_carlo(revenue, capex, opex, iterations=200, seed=1, horizon_years=10)
        r2 = run_monte_carlo(revenue, capex, opex, iterations=200, seed=99, horizon_years=10)
        assert r1.npv_p50 != r2.npv_p50

    def test_p10_less_than_p50_less_than_p90(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=500, seed=42, horizon_years=10)
        assert result.npv_p10 < result.npv_p50 < result.npv_p90

    def test_prob_positive_npv_between_0_and_1(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=100, seed=42, horizon_years=10)
        assert 0.0 <= result.prob_positive_npv <= 1.0

    def test_prob_dscr_between_0_and_1(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=100, seed=42, horizon_years=10)
        assert 0.0 <= result.prob_dscr_below_threshold <= 1.0

    def test_input_correlations_present(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=200, seed=42, horizon_years=10)
        assert "occupancy_target" in result.input_npv_correlations
        assert "capex_overrun_pct" in result.input_npv_correlations

    def test_occupancy_positively_correlated_with_npv(self, base_inputs):
        """Higher occupancy should correlate with higher NPV."""
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=500, seed=42, horizon_years=10)
        occ_corr = result.input_npv_correlations.get("occupancy_target", 0)
        assert occ_corr > 0, f"Expected positive occupancy-NPV correlation, got {occ_corr}"

    def test_capex_overrun_negatively_correlated_with_npv(self, base_inputs):
        """Higher capex overrun should correlate with lower NPV."""
        revenue, capex, opex = base_inputs
        result = run_monte_carlo(revenue, capex, opex, iterations=500, seed=42, horizon_years=10)
        overrun_corr = result.input_npv_correlations.get("capex_overrun_pct", 0)
        assert overrun_corr < 0, f"Expected negative overrun-NPV correlation, got {overrun_corr}"
