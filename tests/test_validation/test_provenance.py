"""Tests for provenance tracker."""

from __future__ import annotations

import pytest

from mmfm.validation.provenance import ProvenanceTracker, ProvenanceRecord


class TestProvenanceTracker:
    def test_register_and_retrieve_cell(self):
        tracker = ProvenanceTracker()
        tracker.register_cell("revenue_year1", 500_000, "model.xlsx", "Revenue", "B5")
        unverified = tracker.get_unverified()
        assert "revenue_year1" not in unverified  # Cell-sourced values are pre-verified

    def test_ai_generated_marked_unverified(self):
        tracker = ProvenanceTracker()
        tracker.register_ai("npv", 123_456, "chunk_005")
        unverified = tracker.get_unverified()
        assert "npv" in unverified

    def test_verify_matching_value_passes(self):
        tracker = ProvenanceTracker()
        tracker.register_ai("npv", 100_000, "chunk_001")
        result = tracker.verify("npv", engine_value=100_000, tolerance=0.0001)
        assert result.match is True

    def test_verify_mismatched_value_fails(self):
        tracker = ProvenanceTracker()
        tracker.register_ai("npv", 50_000, "chunk_001")
        result = tracker.verify("npv", engine_value=100_000, tolerance=0.0001)
        assert result.match is False

    def test_verify_nonexistent_metric(self):
        tracker = ProvenanceTracker()
        result = tracker.verify("npv", engine_value=100_000)
        assert result.match is False
        assert "No record" in result.message

    def test_audit_report_contains_all_entries(self):
        tracker = ProvenanceTracker()
        tracker.register_cell("revenue", 100_000, "model.xlsx", "Revenue", "B5")
        tracker.register_calculated("npv", 50_000, "npv(r, cfs)", ["revenue"])
        tracker.register_ai("summary_npv", 50_000, "chunk_001")
        report = tracker.audit_report()
        assert "revenue" in report
        assert "npv" in report
        assert "summary_npv" in report

    def test_verified_ai_removed_from_unverified(self):
        tracker = ProvenanceTracker()
        tracker.register_ai("npv", 100_000, "chunk_001")
        tracker.verify("npv", engine_value=100_000, tolerance=0.0001)
        unverified = tracker.get_unverified()
        assert "npv" not in unverified
