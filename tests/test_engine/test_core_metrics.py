"""
Golden-value tests for core financial metrics.

All expected values verified independently in Excel / by hand.
"""

from __future__ import annotations

import math
import pytest

from mmfm.engine.core_metrics import (
    calculate_npv,
    calculate_irr,
    calculate_payback,
    calculate_dscr,
    calculate_operating_margin,
)


# ────────────────────────────────────────────────────────────────────────────
# Golden-value test cases (verified in Excel)
# ────────────────────────────────────────────────────────────────────────────

GOLDEN_VALUES = [
    {
        "name": "simple_10yr_project",
        "cash_flows": [-100_000, 15_000, 15_000, 15_000, 15_000, 15_000,
                        15_000, 15_000, 15_000, 15_000, 15_000],
        "discount_rate": 0.10,
        "expected_npv": -7_831.49,   # numpy_financial.npv(0.10, cfs); cf[0] at t=0
        "expected_irr": 0.0814,      # numpy_financial.irr(cfs)
        "expected_payback": 6.67,    # 100K / 15K per year
    },
    {
        "name": "high_growth_market",
        "cash_flows": [-500_000, 20_000, 40_000, 80_000, 120_000, 160_000,
                        180_000, 200_000, 200_000, 200_000, 200_000],
        "discount_rate": 0.12,
        "expected_npv": 172_694.53,
        "expected_irr": 0.1768,
        "expected_payback": 5.44,
    },
    {
        "name": "positive_npv_low_rate",
        "cash_flows": [-200_000, 50_000, 55_000, 60_000, 65_000, 70_000],
        "discount_rate": 0.05,
        "expected_npv": 57_658.42,
        "expected_irr": 0.1430,
        "expected_payback": 3.54,
    },
]


@pytest.mark.parametrize("case", GOLDEN_VALUES, ids=lambda c: c["name"])
def test_npv_golden_values(case):
    result = calculate_npv(case["cash_flows"], case["discount_rate"])
    assert abs(result.value - case["expected_npv"]) < 1.0, (
        f"NPV mismatch for {case['name']}: "
        f"got {result.value:.2f}, expected {case['expected_npv']:.2f}"
    )


@pytest.mark.parametrize("case", GOLDEN_VALUES, ids=lambda c: c["name"])
def test_irr_golden_values(case):
    result = calculate_irr(case["cash_flows"])
    assert result.converged, f"IRR did not converge for {case['name']}: {result.message}"
    assert result.value is not None
    assert abs(result.value - case["expected_irr"]) < 0.001, (
        f"IRR mismatch for {case['name']}: "
        f"got {result.value:.4f}, expected {case['expected_irr']:.4f}"
    )


@pytest.mark.parametrize("case", GOLDEN_VALUES, ids=lambda c: c["name"])
def test_payback_golden_values(case):
    result = calculate_payback(case["cash_flows"])
    assert result.reached, f"Payback not reached for {case['name']}"
    assert result.years is not None
    assert abs(result.years - case["expected_payback"]) < 0.1, (
        f"Payback mismatch for {case['name']}: "
        f"got {result.years:.2f}, expected {case['expected_payback']:.2f}"
    )


# ────────────────────────────────────────────────────────────────────────────
# NPV unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestNPV:
    def test_positive_npv_high_returns(self):
        cfs = [-1000, 400, 400, 400, 400]
        result = calculate_npv(cfs, 0.10)
        assert result.is_positive

    def test_negative_npv_low_returns(self):
        cfs = [-1000, 100, 100, 100, 100]
        result = calculate_npv(cfs, 0.10)
        assert not result.is_positive

    def test_zero_discount_rate(self):
        cfs = [-1000, 500, 500, 500]
        result = calculate_npv(cfs, 0.0)
        assert abs(result.value - 500) < 0.01

    def test_empty_cash_flows_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            calculate_npv([], 0.10)

    def test_invalid_discount_rate_raises(self):
        with pytest.raises(ValueError, match="discount_rate must be"):
            calculate_npv([-1000, 500], -1.5)

    def test_single_outflow_no_returns(self):
        result = calculate_npv([-1000], 0.10)
        assert abs(result.value - (-1000)) < 0.01

    def test_npv_result_stores_inputs(self):
        cfs = [-1000, 500, 500]
        rate = 0.10
        result = calculate_npv(cfs, rate)
        assert result.cash_flows == cfs
        assert result.discount_rate == rate


# ────────────────────────────────────────────────────────────────────────────
# IRR unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestIRR:
    def test_irr_equals_discount_rate_at_zero_npv(self):
        """IRR is the discount rate that makes NPV = 0."""
        irr_result = calculate_irr([-100, 110])
        assert irr_result.converged
        # Check: NPV at IRR should be ~0
        npv_at_irr = calculate_npv([-100, 110], irr_result.value)
        assert abs(npv_at_irr.value) < 0.01

    def test_no_sign_change_returns_no_convergence(self):
        result = calculate_irr([100, 200, 300])  # All positive
        assert not result.converged

    def test_single_inflow(self):
        result = calculate_irr([-1000, 1000])
        assert result.converged
        assert abs(result.value - 0.0) < 0.0001  # 0% IRR on break-even

    def test_irr_high_return_project(self):
        result = calculate_irr([-100, 200])
        assert result.converged
        assert abs(result.value - 1.0) < 0.001  # 100% IRR


# ────────────────────────────────────────────────────────────────────────────
# Payback unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestPayback:
    def test_payback_never_reached(self):
        result = calculate_payback([-1000, 100, 100, 100])
        assert not result.reached
        assert result.years is None

    def test_payback_year_zero(self):
        """If first cash flow is already positive, payback = 0."""
        result = calculate_payback([1000, 500])
        assert result.reached
        assert result.years == 0.0

    def test_payback_linear_interpolation(self):
        """Payback should interpolate fractional years."""
        # -1000 + 600 + 600: cumulative [-1000, -400, 200]
        # Payback between year 1 and 2: 400/600 = 0.667 into year 2
        result = calculate_payback([-1000, 600, 600])
        assert result.reached
        # At year 1: cumulative = -400; year 2 CF = 600
        # fraction = 400/600 = 0.667, so payback = 1 + 0.667 = 1.667
        assert abs(result.years - 1.667) < 0.01

    def test_exact_payback_on_year_boundary(self):
        result = calculate_payback([-500, 500])
        assert result.reached
        assert abs(result.years - 1.0) < 0.01

    def test_empty_cash_flows_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            calculate_payback([])


# ────────────────────────────────────────────────────────────────────────────
# DSCR unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestDSCR:
    def test_dscr_above_threshold(self):
        noi = [150_000, 160_000, 170_000]
        ds = [100_000, 100_000, 100_000]
        result = calculate_dscr(noi, ds)
        assert all(v >= 1.5 for v in result.values)
        assert result.below_threshold == []

    def test_dscr_below_threshold_flagged(self):
        noi = [100_000, 110_000, 90_000]
        ds = [100_000, 100_000, 100_000]
        result = calculate_dscr(noi, ds, warning_threshold=1.2)
        # Year 1: 1.0, year 2: 1.1, year 3: 0.9 — all below 1.2
        assert len(result.below_threshold) == 3

    def test_dscr_zero_debt_service(self):
        noi = [100_000, 100_000]
        ds = [0.0, 0.0]
        result = calculate_dscr(noi, ds)
        assert all(math.isnan(v) for v in result.values)

    def test_dscr_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            calculate_dscr([100_000], [100_000, 100_000])

    def test_dscr_min_year_identified(self):
        noi = [180_000, 120_000, 200_000]
        ds = [100_000, 100_000, 100_000]
        result = calculate_dscr(noi, ds, years=[2025, 2026, 2027])
        assert result.min_dscr_year == 2026
        assert abs(result.min_dscr - 1.2) < 0.001


# ────────────────────────────────────────────────────────────────────────────
# Operating Margin unit tests
# ────────────────────────────────────────────────────────────────────────────

class TestOperatingMargin:
    def test_margin_calculation(self):
        revenues = [100_000, 120_000]
        opex = [60_000, 70_000]
        result = calculate_operating_margin(revenues, opex)
        assert abs(result.values[0] - 0.40) < 0.001
        assert abs(result.values[1] - 0.4167) < 0.001

    def test_zero_revenue_gives_nan(self):
        result = calculate_operating_margin([0.0, 100_000], [50_000, 60_000])
        assert math.isnan(result.values[0])
        assert not math.isnan(result.values[1])

    def test_improving_trend(self):
        revenues = [100_000] * 6
        opex = [70_000, 65_000, 60_000, 55_000, 50_000, 45_000]  # Declining opex
        result = calculate_operating_margin(revenues, opex)
        assert result.trend == "improving"

    def test_declining_trend(self):
        revenues = [100_000] * 6
        opex = [40_000, 50_000, 60_000, 70_000, 75_000, 80_000]  # Rising opex
        result = calculate_operating_margin(revenues, opex)
        assert result.trend == "declining"

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            calculate_operating_margin([100_000], [60_000, 70_000])
