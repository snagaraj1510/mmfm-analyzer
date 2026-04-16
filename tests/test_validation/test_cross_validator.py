"""Tests for cross-validator."""

from __future__ import annotations

import pytest

from mmfm.validation.cross_validator import (
    extract_numbers_from_text,
    validate_narrative_number,
    validate_no_invented_numbers,
)


class TestExtractNumbers:
    def test_extracts_plain_numbers(self):
        nums = extract_numbers_from_text("NPV is 123456.78")
        assert 123456.78 in nums

    def test_extracts_currency_values(self):
        nums = extract_numbers_from_text("Revenue of $1,234,567")
        assert 1234567.0 in nums

    def test_extracts_percentages(self):
        nums = extract_numbers_from_text("IRR of 17.5%")
        assert 0.175 in nums

    def test_extracts_negative_numbers(self):
        nums = extract_numbers_from_text("NPV is -500,000")
        assert -500000.0 in nums


class TestCrossValidator:
    def test_engine_value_found_in_narrative(self):
        narrative = "The project NPV is $172,695 at a 12% discount rate."
        result = validate_narrative_number("npv", 172695.0, narrative, tolerance=0.001)
        assert result.passed

    def test_narrative_number_check_passes_for_absent_value(self):
        """If engine value isn't mentioned, it passes (not hallucinated, just omitted)."""
        narrative = "The project shows strong returns."
        result = validate_narrative_number("npv", 172695.0, narrative)
        assert result.passed  # Can't flag as wrong if not mentioned

    def test_no_invented_numbers_passes(self):
        narrative = "The NPV is 100000 and IRR is 0.15."
        allowed = {100000.0, 0.15, 0.10}
        result = validate_no_invented_numbers(narrative, allowed)
        assert result.passed

    def test_invented_numbers_detected(self):
        narrative = "The NPV is 999999 which represents strong returns."
        allowed = {100000.0, 0.15}  # 999999 is not in allowed
        result = validate_no_invented_numbers(narrative, allowed, tolerance=0.01)
        assert not result.passed
