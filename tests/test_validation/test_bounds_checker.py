"""Tests for bounds checker."""

from __future__ import annotations

import math
import pytest

from mmfm.validation.bounds_checker import check_bounds, check_all_bounds, BoundsStatus


class TestBoundsChecker:
    def test_npv_within_bounds_passes(self):
        result = check_bounds("npv", 500_000)
        assert result.status == BoundsStatus.PASS

    def test_npv_exceeds_max_fails(self):
        result = check_bounds("npv", 2e9)  # Above 1e9 max
        assert result.status == BoundsStatus.FAIL

    def test_irr_negative_fails(self):
        result = check_bounds("irr", -0.60)  # Below -50% min
        assert result.status == BoundsStatus.FAIL

    def test_occupancy_rate_valid_passes(self):
        result = check_bounds("occupancy_rate", 0.70)
        assert result.status == BoundsStatus.PASS

    def test_occupancy_rate_zero_fails(self):
        result = check_bounds("occupancy_rate", 0.05)  # Below min 0.10
        assert result.status == BoundsStatus.FAIL

    def test_fee_collection_rate_lusaka_avg_passes(self):
        """Lusaka average of 0.38 should be within bounds."""
        result = check_bounds("fee_collection_rate", 0.38)
        assert result.status == BoundsStatus.PASS

    def test_fee_collection_rate_floor_passes(self):
        """Worst case of 0.10 should be at the boundary."""
        result = check_bounds("fee_collection_rate", 0.10)
        # At exactly the min bound — should pass or warning
        assert result.status in (BoundsStatus.PASS, BoundsStatus.WARNING)

    def test_nan_value_fails(self):
        result = check_bounds("npv", float("nan"))
        assert result.status == BoundsStatus.FAIL

    def test_unknown_metric_passes(self):
        """Metrics without bounds defined should pass by default."""
        result = check_bounds("unknown_metric_xyz", 42.0)
        assert result.status == BoundsStatus.PASS

    def test_check_all_bounds_returns_dict(self):
        metrics = {"npv": 100_000, "irr": 0.15, "occupancy_rate": 0.70}
        results = check_all_bounds(metrics)
        assert "npv" in results
        assert "irr" in results
        assert "occupancy_rate" in results
        assert all(r.status == BoundsStatus.PASS for r in results.values())

    def test_solar_pv_anomaly_bounds(self):
        """Solar PV CAPEX within normal bounds should not fail bounds check."""
        result = check_bounds("capex_total_usd", 1_070_000)
        assert result.status in (BoundsStatus.PASS, BoundsStatus.WARNING)
