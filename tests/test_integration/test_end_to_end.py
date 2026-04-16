"""
End-to-end integration tests.

These tests exercise full pipeline flows using demo inputs and mocked LLM calls.
No real Excel files or API keys are required.
"""
from __future__ import annotations

import json
import pytest
from typer.testing import CliRunner

from mmfm.cli import app
from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
from mmfm.engine.scenarios import run_all_scenarios
from mmfm.engine.core_metrics import calculate_npv, calculate_irr, calculate_payback


runner = CliRunner()


@pytest.fixture
def demo_inputs():
    revenue = RevenueInputs(
        base_stall_rental_income=200_000,
        occupancy_rate=0.60,
        vendor_fees_annual=30_000,
        market_levies_annual=15_000,
        rental_escalation_rate=0.06,
        fee_escalation_rate=0.06,
        occupancy_ramp_years=3,
        occupancy_target=0.70,
        fee_collection_rate=0.70,
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


class TestFullPipeline:
    def test_scenario_engine_produces_consistent_ranking(self, demo_inputs):
        """Base, optimistic, pessimistic must be consistently orderable by NPV."""
        revenue, capex, opex = demo_inputs
        comparison = run_all_scenarios(revenue, capex, opex, discount_rate=0.10)
        ranking = comparison.npv_ranking()
        assert set(ranking) == {"base", "optimistic", "pessimistic"}
        # Optimistic must outperform pessimistic
        assert ranking.index("optimistic") < ranking.index("pessimistic")

    def test_fee_collection_rate_affects_npv(self, demo_inputs):
        """Lower fee_collection_rate should produce lower NPV."""
        from mmfm.engine.projections import project_cash_flows
        revenue, capex, opex = demo_inputs

        high_collection = RevenueInputs(
            **{**revenue.__dict__, "fee_collection_rate": 0.90}
        )
        low_collection = RevenueInputs(
            **{**revenue.__dict__, "fee_collection_rate": 0.38}
        )

        proj_high = project_cash_flows(high_collection, capex, opex)
        proj_low = project_cash_flows(low_collection, capex, opex)

        npv_high = calculate_npv(proj_high.get_cash_flows(), 0.10)
        npv_low = calculate_npv(proj_low.get_cash_flows(), 0.10)

        assert npv_high.value > npv_low.value

    def test_pessimistic_scenario_has_lower_npv_than_base(self, demo_inputs):
        """Pessimistic scenario (fee_collection_rate=0.38) < base (0.65)."""
        revenue, capex, opex = demo_inputs
        comparison = run_all_scenarios(revenue, capex, opex, discount_rate=0.10)
        assert comparison.results["pessimistic"].npv.value < comparison.results["base"].npv.value

    def test_multi_market_compare_command(self):
        """mmfm compare --format json should return valid JSON with expected markets."""
        result = runner.invoke(app, ["compare", "--format", "json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "markets" in data
        assert "investment_ready" in data
        names = [m["market"] for m in data["markets"]]
        assert "Pemba Eduardo Mondlane" in names
        assert "Kisumu Municipal Market" in names

    def test_compare_pemba_is_investment_ready(self):
        """Pemba should be investment-ready (IRR 45.5% >> 12% threshold)."""
        result = runner.invoke(app, ["compare", "--format", "json"])
        data = json.loads(result.output)
        assert "Pemba Eduardo Mondlane" in data["investment_ready"]

    def test_compare_kisumu_not_investment_ready(self):
        """Kisumu stress-test market should NOT be investment-ready."""
        result = runner.invoke(app, ["compare", "--format", "json"])
        data = json.loads(result.output)
        assert "Kisumu Municipal Market" not in data["investment_ready"]

    def test_compare_npv_ranking_pemba_first(self):
        """Pemba has the highest NPV in the demo portfolio."""
        result = runner.invoke(app, ["compare", "--format", "json"])
        data = json.loads(result.output)
        assert data["npv_ranking"][0] == "Pemba Eduardo Mondlane"

    def test_compare_npv_ranking_kisumu_last(self):
        """Kisumu has negative NPV and should rank last."""
        result = runner.invoke(app, ["compare", "--format", "json"])
        data = json.loads(result.output)
        assert data["npv_ranking"][-1] == "Kisumu Municipal Market"
