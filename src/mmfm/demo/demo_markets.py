"""
Demo market fixtures for MMFM Analyzer tests and CLI demos.

Five anonymised markets drawn from MAP field data across Sub-Saharan Africa.
"""
from __future__ import annotations
from mmfm.engine.comparison import MarketProfile

# Market 1 — optimistic anchor (Mozambique)
MARKET_1 = MarketProfile(
    name="Market 1",
    country="Mozambique",
    city="East Africa",
    npv_usd=1_400_000.0,
    irr=0.455,           # 45.5% IRR
    payback_years=4.3,
    min_dscr=2.1,
    total_capex_usd=2_200_000.0,
    miri_score=None,
    governance_score=None,
    fee_collection_rate=0.82,
    notes="Optimistic anchor: highest IRR in portfolio. Strong revenue base.",
)

# Market 2 — stress-test anchor (Kenya)
MARKET_2 = MarketProfile(
    name="Market 2",
    country="Kenya",
    city="East Africa",
    npv_usd=-320_000.0,
    irr=-0.08,
    payback_years=None,
    min_dscr=-5.8,       # Worst-case DSCR — stress-test anchor
    total_capex_usd=1_070_000.0,   # Solar PV CAPEX near-inviable without TA support
    miri_score=None,
    governance_score=None,
    fee_collection_rate=0.52,
    notes="Stress-test anchor: Solar PV CAPEX near annual revenue. Requires TA support.",
)

# Market 3 — strong MIRI, cleanest portfolio signal (Malawi)
MARKET_3 = MarketProfile(
    name="Market 3",
    country="Malawi",
    city="East Africa",
    npv_usd=420_000.0,
    irr=0.19,
    payback_years=8.2,
    min_dscr=1.45,
    total_capex_usd=850_000.0,
    miri_score=81.0,
    governance_score=78.0,
    fee_collection_rate=0.72,
    notes="81% MIRI score. Cashflow sufficient to service debt. Clean portfolio signal.",
)

# Market 4 — high MIRI, paired market (Malawi)
MARKET_4 = MarketProfile(
    name="Market 4",
    country="Malawi",
    city="East Africa",
    npv_usd=380_000.0,
    irr=0.17,
    payback_years=9.1,
    min_dscr=1.32,
    total_capex_usd=720_000.0,
    miri_score=81.0,
    governance_score=75.0,
    fee_collection_rate=0.68,
    notes="81% MIRI score. Strong governance, moderate collection rate.",
)

# Market 5 — highest governance score (Zambia)
MARKET_5 = MarketProfile(
    name="Market 5",
    country="Zambia",
    city="East Africa",
    npv_usd=290_000.0,
    irr=0.14,
    payback_years=10.5,
    min_dscr=1.28,
    total_capex_usd=680_000.0,
    miri_score=74.0,
    governance_score=82.0,
    fee_collection_rate=0.55,
    notes="82% governance score. Strongest governance in portfolio. Conservative revenue.",
)

# Full demo portfolio
DEMO_PORTFOLIO: list[MarketProfile] = [
    MARKET_1,
    MARKET_3,
    MARKET_4,
    MARKET_5,
    MARKET_2,
]
