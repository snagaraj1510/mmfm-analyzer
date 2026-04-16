"""Tests for lead-time schema validation rules."""

from __future__ import annotations

import pytest
import pandas as pd

from mmfm.ingestion.schema_validator import validate_sheets, ValidationResult


CAPEX_SCHEMA_WITH_RULES = {
    "name": "capex_model",
    "version": "1.1",
    "required_sheets": [
        {
            "name": "Capital Expenditure",
            "required_columns": [
                {"name": "item", "type": "string"},
                {"name": "cost_estimate", "type": "float", "min": 0},
                {"name": "year", "type": "integer"},
                {"name": "funding_source", "type": "string",
                 "allowed_values": ["municipal_budget", "grant", "ppp", "bond", "other"]},
            ],
            "optional_columns": [
                {"name": "lead_time_months", "type": "integer", "min": 1, "max": 36},
            ],
        }
    ],
    "lead_time_rules": [
        {
            "item_pattern": "roof",
            "min_lead_time_months": 6,
            "warning_message": "Roofing items typically require 12-month lead time. Value < 6 months is likely underestimated.",
            "typical_lead_time_months": 12,
        }
    ],
}


class TestLeadTimeValidation:
    def test_roofing_below_6_months_warns(self):
        df = pd.DataFrame({
            "item": ["Roofing structure", "Electrical systems"],
            "cost_estimate": [300_000.0, 100_000.0],
            "year": [2025, 2025],
            "funding_source": ["grant", "municipal_budget"],
            "lead_time_months": [3, 3],  # 3 months for roofing — below 6 minimum
        })
        result = validate_sheets({"Capital Expenditure": df}, CAPEX_SCHEMA_WITH_RULES)
        # Should warn about roofing lead time
        roofing_warnings = [w for w in result.warnings if "lead_time" in w.column]
        assert len(roofing_warnings) >= 1
        assert "roof" in roofing_warnings[0].message.lower() or "Roofing" in roofing_warnings[0].message

    def test_roofing_at_12_months_passes(self):
        df = pd.DataFrame({
            "item": ["Roofing structure"],
            "cost_estimate": [300_000.0],
            "year": [2025],
            "funding_source": ["grant"],
            "lead_time_months": [12],  # Correct 12-month lead time
        })
        result = validate_sheets({"Capital Expenditure": df}, CAPEX_SCHEMA_WITH_RULES)
        roofing_warnings = [w for w in result.warnings if "lead_time" in w.column.lower()]
        assert len(roofing_warnings) == 0

    def test_non_roofing_short_lead_time_no_warn(self):
        df = pd.DataFrame({
            "item": ["Electrical systems"],
            "cost_estimate": [100_000.0],
            "year": [2025],
            "funding_source": ["municipal_budget"],
            "lead_time_months": [3],  # 3 months is fine for electrical
        })
        result = validate_sheets({"Capital Expenditure": df}, CAPEX_SCHEMA_WITH_RULES)
        roofing_warnings = [w for w in result.warnings if "lead_time" in w.column.lower()]
        assert len(roofing_warnings) == 0

    def test_no_lead_time_column_skips_rule(self):
        """If lead_time_months column is absent, skip lead-time rules gracefully."""
        df = pd.DataFrame({
            "item": ["Roofing structure"],
            "cost_estimate": [300_000.0],
            "year": [2025],
            "funding_source": ["grant"],
            # No lead_time_months column
        })
        result = validate_sheets({"Capital Expenditure": df}, CAPEX_SCHEMA_WITH_RULES)
        # Should not crash; no lead-time warnings since column is absent
        assert isinstance(result, ValidationResult)
