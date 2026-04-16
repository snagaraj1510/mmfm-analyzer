"""Tests for the scenario engine."""

from __future__ import annotations

import pytest

from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
from mmfm.engine.scenarios import (
    run_scenario,
    run_all_scenarios,
    BASE_SCENARIO,
    OPTIMISTIC_SCENARIO,
    PESSIMISTIC_SCENARIO,
    BUILT_IN_SCENARIOS,
    ScenarioComparison,
)


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


class TestScenarioEngine:
    def test_base_scenario_runs(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=10)
        assert result.npv is not None
        assert result.irr is not None
        assert result.projection is not None

    def test_optimistic_npv_greater_than_base(self, base_inputs):
        revenue, capex, opex = base_inputs
        base = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=15)
        optimistic = run_scenario(OPTIMISTIC_SCENARIO, revenue, capex, opex, horizon_years=15)
        assert optimistic.npv.value > base.npv.value

    def test_pessimistic_npv_less_than_base(self, base_inputs):
        revenue, capex, opex = base_inputs
        base = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=15)
        pessimistic = run_scenario(PESSIMISTIC_SCENARIO, revenue, capex, opex, horizon_years=15)
        assert pessimistic.npv.value < base.npv.value

    def test_scenario_ranking_consistent(self, base_inputs):
        """Optimistic > Base > Pessimistic by NPV."""
        revenue, capex, opex = base_inputs
        opt = run_scenario(OPTIMISTIC_SCENARIO, revenue, capex, opex, horizon_years=15)
        base = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=15)
        pess = run_scenario(PESSIMISTIC_SCENARIO, revenue, capex, opex, horizon_years=15)
        assert opt.npv.value > base.npv.value > pess.npv.value

    def test_run_all_scenarios_returns_three(self, base_inputs):
        revenue, capex, opex = base_inputs
        comparison = run_all_scenarios(revenue, capex, opex, horizon_years=10)
        assert len(comparison.results) == 3
        assert "base" in comparison.results
        assert "optimistic" in comparison.results
        assert "pessimistic" in comparison.results

    def test_npv_ranking_order(self, base_inputs):
        revenue, capex, opex = base_inputs
        comparison = run_all_scenarios(revenue, capex, opex, horizon_years=15)
        ranking = comparison.npv_ranking()
        # First should be optimistic, last should be pessimistic
        assert ranking[0] == "optimistic"
        assert ranking[-1] == "pessimistic"

    def test_grant_delay_reduces_npv(self, base_inputs):
        """Delaying grant disbursement should reduce NPV vs base."""
        revenue, capex, opex = base_inputs
        base = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=15)
        pessimistic = run_scenario(PESSIMISTIC_SCENARIO, revenue, capex, opex, horizon_years=15)
        # Pessimistic has 1-year grant delay — should hurt NPV
        assert pessimistic.npv.value < base.npv.value

    def test_projection_horizon_respected(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_scenario(BASE_SCENARIO, revenue, capex, opex, horizon_years=10)
        assert len(result.projection.years) == 11  # Year 0 + 10 operational years

    def test_summary_table_has_all_scenarios(self, base_inputs):
        revenue, capex, opex = base_inputs
        comparison = run_all_scenarios(revenue, capex, opex, horizon_years=10)
        table = comparison.summary_table()
        assert len(table) == 3
        scenario_names = {row["scenario"] for row in table}
        assert scenario_names == {"base", "optimistic", "pessimistic"}
