"""
Demo market fixtures for MMFM Analyzer tests and CLI demos.

All values are derived from MAP source documents:
- ICLEI Africa Financial Model (Pemba Eduardo Mondlane)
- Lusaka Market Report (Chainda, Mandevu)
- Lilongwe Report (Tsoka, Lizulu)
- Kisumu Income Statement (stress-test anchor)
"""
from __future__ import annotations
from mmfm.engine.comparison import MarketProfile

# Pemba Eduardo Mondlane — optimistic anchor
# Source: ICLEI Financial Model, Mozambique
PEMBA_EDUARDO_MONDLANE = MarketProfile(
    name="Pemba Eduardo Mondlane",
    country="Mozambique",
    city="Pemba",
    npv_usd=1_400_000.0,
    irr=0.455,           # 45.5% IRR
    payback_years=4.3,
    min_dscr=2.1,
    total_capex_usd=2_200_000.0,
    miri_score=None,
    governance_score=None,
    fee_collection_rate=0.82,
    notes="Optimistic anchor: highest IRR in MAP portfolio. Strong fish market revenue base.",
)

# Kisumu Municipal Market — stress-test anchor
# Source: Kisumu income statement (Kenya)
KISUMU_MUNICIPAL = MarketProfile(
    name="Kisumu Municipal Market",
    country="Kenya",
    city="Kisumu",
    npv_usd=-320_000.0,
    irr=-0.08,
    payback_years=None,
    min_dscr=-5.8,       # Worst-case DSCR — stress-test anchor
    total_capex_usd=1_070_000.0,   # Solar PV CAPEX near-inviable without TA support
    miri_score=None,
    governance_score=None,
    fee_collection_rate=0.52,
    notes="Stress-test anchor: Solar PV CAPEX ~= existing annual revenue. Requires TA support.",
)

# Tsoka Market, Lilongwe — strong MIRI, cleanest portfolio signal
# Source: Lilongwe Market Report
TSOKA_LILONGWE = MarketProfile(
    name="Tsoka Market",
    country="Malawi",
    city="Lilongwe",
    npv_usd=420_000.0,
    irr=0.19,
    payback_years=8.2,
    min_dscr=1.45,
    total_capex_usd=850_000.0,
    miri_score=81.0,     # 81% MIRI score
    governance_score=78.0,
    fee_collection_rate=0.72,
    notes="81% MIRI score. Cashflow sufficient to service debt. Clean portfolio signal.",
)

# Lizulu Market, Lilongwe — paired with Tsoka, also high MIRI
LIZULU_LILONGWE = MarketProfile(
    name="Lizulu Market",
    country="Malawi",
    city="Lilongwe",
    npv_usd=380_000.0,
    irr=0.17,
    payback_years=9.1,
    min_dscr=1.32,
    total_capex_usd=720_000.0,
    miri_score=81.0,     # 81% MIRI score (paired with Tsoka)
    governance_score=75.0,
    fee_collection_rate=0.68,
    notes="81% MIRI (Tsoka/Lizulu paired). Strong governance, moderate collection rate.",
)

# Chainda Market, Lusaka — highest governance score
# Source: Lusaka Market Report
CHAINDA_LUSAKA = MarketProfile(
    name="Chainda Market",
    country="Zambia",
    city="Lusaka",
    npv_usd=290_000.0,
    irr=0.14,
    payback_years=10.5,
    min_dscr=1.28,
    total_capex_usd=680_000.0,
    miri_score=74.0,
    governance_score=82.0,   # 82% governance score
    fee_collection_rate=0.55,
    notes="82% governance score. Strongest governance in Lusaka portfolio. Conservative revenue.",
)

# Full demo portfolio
DEMO_PORTFOLIO: list[MarketProfile] = [
    PEMBA_EDUARDO_MONDLANE,
    TSOKA_LILONGWE,
    LIZULU_LILONGWE,
    CHAINDA_LUSAKA,
    KISUMU_MUNICIPAL,
]
