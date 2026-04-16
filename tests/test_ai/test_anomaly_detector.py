"""Tests for anomaly detector — including Solar PV disproportion rule."""

from __future__ import annotations

import pytest

from mmfm.ai.anomaly_detector import detect_anomalies, AnomalyReport


class TestAnomalyDetector:
    def test_clean_metrics_no_anomalies(self):
        metrics = {"npv": 100_000, "irr": 0.15, "occupancy_rate": 0.70, "dscr": 1.5}
        report = detect_anomalies(metrics)
        assert report.overall_data_quality in ("good", "acceptable")

    def test_out_of_bounds_npv_flagged(self):
        metrics = {"npv": 2e10}  # Way above 1e9 max
        report = detect_anomalies(metrics)
        npv_anomalies = [a for a in report.anomalies if a.metric == "npv"]
        assert len(npv_anomalies) >= 1

    def test_solar_pv_disproportion_flagged(self):
        """Solar PV CAPEX > 80% of annual revenue should be flagged (Kisumu lesson)."""
        metrics = {"solar_pv_capex": 1_070_000}
        annual_existing_revenue = 1_030_000  # Kisumu reference case
        report = detect_anomalies(metrics, annual_existing_revenue=annual_existing_revenue)
        solar_anomalies = [a for a in report.anomalies if a.metric == "solar_pv_capex"]
        assert len(solar_anomalies) == 1
        assert solar_anomalies[0].severity == "high"
        assert "80%" in solar_anomalies[0].reason

    def test_solar_pv_within_ratio_not_flagged(self):
        """Solar PV CAPEX <= 80% of revenue should not trigger the rule."""
        metrics = {"solar_pv_capex": 400_000}
        annual_existing_revenue = 1_000_000  # 40% ratio — fine
        report = detect_anomalies(metrics, annual_existing_revenue=annual_existing_revenue)
        solar_anomalies = [a for a in report.anomalies if a.metric == "solar_pv_capex"]
        assert len(solar_anomalies) == 0

    def test_npv_irr_inconsistency_flagged(self):
        """Positive NPV but IRR below discount rate is inconsistent."""
        metrics = {"npv": 50_000, "irr": 0.05, "discount_rate": 0.10}
        report = detect_anomalies(metrics)
        irr_anomalies = [a for a in report.anomalies if a.rule == "npv_irr_consistency"]
        assert len(irr_anomalies) >= 1

    def test_operating_margin_ceiling(self):
        """Operating margin > 95% is implausibly high."""
        metrics = {"operating_margin": 0.98}
        report = detect_anomalies(metrics)
        margin_anomalies = [a for a in report.anomalies if a.rule == "operating_margin_ceiling"]
        assert len(margin_anomalies) >= 1

    def test_anomaly_report_quality_degrades(self):
        metrics = {
            "npv": 2e10,  # Out of bounds
            "occupancy_rate": 0.01,  # Out of bounds
        }
        report = detect_anomalies(metrics)
        assert report.overall_data_quality in ("acceptable", "poor")
