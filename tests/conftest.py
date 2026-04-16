"""Shared test fixtures for MMFM Analyzer tests."""

from __future__ import annotations

import pytest
import pandas as pd
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_10yr_cash_flows() -> list[float]:
    """10-year project: -100K investment, 15K/year returns."""
    return [-100_000, 15_000, 15_000, 15_000, 15_000, 15_000,
            15_000, 15_000, 15_000, 15_000, 15_000]


@pytest.fixture
def high_growth_cash_flows() -> list[float]:
    """High-growth market project."""
    return [-500_000, 20_000, 40_000, 80_000, 120_000, 160_000,
            180_000, 200_000, 200_000, 200_000, 200_000]


@pytest.fixture
def sample_revenue_df() -> pd.DataFrame:
    """Sample revenue projections DataFrame matching revenue_schema."""
    return pd.DataFrame({
        "year": [2025, 2026, 2027, 2028, 2029],
        "stall_rental_income": [50_000.0, 55_000.0, 60_500.0, 66_550.0, 73_205.0],
        "vendor_fees": [10_000.0, 11_000.0, 12_100.0, 13_310.0, 14_641.0],
        "market_levies": [5_000.0, 5_250.0, 5_512.5, 5_788.1, 6_077.5],
        "occupancy_rate": [0.60, 0.70, 0.75, 0.80, 0.82],
    })


@pytest.fixture
def sample_capex_df() -> pd.DataFrame:
    """Sample capex DataFrame matching capex_schema."""
    return pd.DataFrame({
        "item": ["Market structure", "Electrical systems", "Water & sanitation", "Paving & access"],
        "cost_estimate": [800_000.0, 150_000.0, 100_000.0, 80_000.0],
        "year": [2025, 2025, 2025, 2026],
        "funding_source": ["grant", "municipal_budget", "grant", "ppp"],
    })
