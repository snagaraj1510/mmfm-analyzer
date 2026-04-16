"""Tests for schema validation logic."""

from __future__ import annotations

import pytest
import pandas as pd

from mmfm.ingestion.schema_validator import validate_sheets, ValidationResult


REVENUE_SCHEMA = {
    "name": "revenue_model",
    "version": "1.0",
    "required_sheets": [
        {
            "name": "Revenue Projections",
            "required_columns": [
                {"name": "year", "type": "integer", "min": 2024, "max": 2050},
                {"name": "stall_rental_income", "type": "float", "min": 0},
                {"name": "vendor_fees", "type": "float", "min": 0},
                {"name": "market_levies", "type": "float", "min": 0},
                {"name": "occupancy_rate", "type": "float", "min": 0.0, "max": 1.0},
            ],
            "optional_columns": [
                {"name": "other_income", "type": "float", "min": 0},
            ],
        }
    ],
}


class TestSchemaValidation:
    def test_valid_dataframe_passes(self, sample_revenue_df):
        sheets = {"Revenue Projections": sample_revenue_df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        assert result.passed
        assert result.errors == []

    def test_missing_required_sheet_fails(self, sample_revenue_df):
        sheets = {"Wrong Sheet Name": sample_revenue_df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        assert not result.passed
        assert any("Revenue Projections" in e.message for e in result.errors)

    def test_missing_required_column_fails(self):
        df = pd.DataFrame({
            "year": [2025, 2026],
            "stall_rental_income": [50_000.0, 55_000.0],
            # vendor_fees missing
            "market_levies": [5_000.0, 5_250.0],
            "occupancy_rate": [0.70, 0.75],
        })
        sheets = {"Revenue Projections": df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        assert not result.passed
        assert any("vendor_fees" in e.column for e in result.errors)

    def test_value_below_min_raises_warning(self):
        df = pd.DataFrame({
            "year": [2025],
            "stall_rental_income": [50_000.0],
            "vendor_fees": [10_000.0],
            "market_levies": [5_000.0],
            "occupancy_rate": [-0.1],  # Below 0.0 min
        })
        sheets = {"Revenue Projections": df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        # Warning, not error (bounds are warnings)
        assert any(w.column == "occupancy_rate" for w in result.warnings)

    def test_invalid_type_fails(self):
        df = pd.DataFrame({
            "year": ["not_a_year"],
            "stall_rental_income": [50_000.0],
            "vendor_fees": [10_000.0],
            "market_levies": [5_000.0],
            "occupancy_rate": [0.70],
        })
        sheets = {"Revenue Projections": df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        # "not_a_year" should still coerce — "not_a_year" as string to int fails
        # Actually float("not_a_year") will fail
        assert not result.passed

    def test_case_insensitive_sheet_matching(self, sample_revenue_df):
        """Sheet names should match case-insensitively."""
        sheets = {"revenue projections": sample_revenue_df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        assert result.passed

    def test_empty_dataframe_no_data_errors(self):
        df = pd.DataFrame(columns=["year", "stall_rental_income", "vendor_fees", "market_levies", "occupancy_rate"])
        sheets = {"Revenue Projections": df}
        result = validate_sheets(sheets, REVENUE_SCHEMA)
        assert result.passed  # No data rows = no value errors

    def test_allowed_values_enforced(self):
        capex_schema = {
            "name": "capex_model",
            "version": "1.0",
            "required_sheets": [
                {
                    "name": "Capital Expenditure",
                    "required_columns": [
                        {"name": "item", "type": "string"},
                        {"name": "cost_estimate", "type": "float", "min": 0},
                        {"name": "year", "type": "integer"},
                        {
                            "name": "funding_source",
                            "type": "string",
                            "allowed_values": ["municipal_budget", "grant", "ppp", "bond", "other"],
                        },
                    ],
                }
            ],
        }

        df = pd.DataFrame({
            "item": ["Structure"],
            "cost_estimate": [500_000.0],
            "year": [2025],
            "funding_source": ["invalid_source"],
        })
        sheets = {"Capital Expenditure": df}
        result = validate_sheets(sheets, capex_schema)
        assert not result.passed
        assert any("funding_source" in e.column for e in result.errors)
