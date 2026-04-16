"""Tests for sensitivity and tornado analysis."""

from __future__ import annotations

import pytest

from mmfm.engine.projections import RevenueInputs, CapexInputs, OpexInputs
from mmfm.engine.sensitivity import (
    run_sensitivity,
    run_single_variable_sensitivity,
    SENSITIVITY_VARIABLES,
    SensitivityResult,
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


class TestSensitivityAnalysis:
    def test_runs_all_default_variables(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_sensitivity(revenue, capex, opex, horizon_years=10)
        assert len(result.variables) == len(SENSITIVITY_VARIABLES)

    def test_occupancy_positively_correlated_with_npv(self, base_inputs):
        """Higher occupancy should produce higher NPV."""
        revenue, capex, opex = base_inputs
        var = run_single_variable_sensitivity("occupancy_rate", revenue, capex, opex, horizon_years=10)
        # NPV at high occupancy > NPV at low occupancy
        assert var.npv_at_high > var.npv_at_low

    def test_capex_overrun_negatively_correlated_with_npv(self, base_inputs):
        """Higher capex overrun should reduce NPV."""
        revenue, capex, opex = base_inputs
        var = run_single_variable_sensitivity("capex_overrun_pct", revenue, capex, opex, horizon_years=10)
        assert var.npv_at_low > var.npv_at_high

    def test_discount_rate_negatively_correlated_with_npv(self, base_inputs):
        """Higher discount rate should reduce NPV (for projects with positive NPV)."""
        revenue, capex, opex = base_inputs
        var = run_single_variable_sensitivity("discount_rate", revenue, capex, opex, horizon_years=15)
        # At low discount rates NPV should be higher than at high discount rates
        assert var.npv_at_low > var.npv_at_high

    def test_tornado_order_by_swing(self, base_inputs):
        """Tornado order should be sorted by NPV swing descending."""
        revenue, capex, opex = base_inputs
        result = run_sensitivity(revenue, capex, opex, horizon_years=10)
        ordered = result.tornado_order()
        swings = [v.npv_swing for v in ordered]
        assert swings == sorted(swings, reverse=True)

    def test_base_npv_is_finite(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_sensitivity(revenue, capex, opex, horizon_years=10)
        import math
        assert math.isfinite(result.base_npv)

    def test_invalid_variable_name_raises(self, base_inputs):
        revenue, capex, opex = base_inputs
        with pytest.raises(ValueError, match="Unknown variable"):
            run_single_variable_sensitivity("nonexistent_var", revenue, capex, opex)

    def test_each_variable_has_multiple_points(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_sensitivity(revenue, capex, opex, horizon_years=10)
        for var in result.variables:
            assert len(var.points) >= 2, f"{var.variable_name} has fewer than 2 points"

    def test_npv_swing_is_positive(self, base_inputs):
        revenue, capex, opex = base_inputs
        result = run_sensitivity(revenue, capex, opex, horizon_years=10)
        for var in result.variables:
            assert var.npv_swing >= 0
