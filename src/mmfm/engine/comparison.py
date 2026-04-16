"""Multi-market comparison engine for MMFM Analyzer."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class MarketProfile:
    """
    Named market profile for multi-market comparison.

    Contains pre-computed financial metrics or inputs for a named market.
    Used for portfolio-level comparison across markets.
    """
    name: str                         # e.g. "Pemba Eduardo Mondlane"
    country: str                      # e.g. "Mozambique"
    city: str                         # e.g. "Pemba"
    npv_usd: Optional[float] = None
    irr: Optional[float] = None       # as decimal, e.g. 0.455 for 45.5%
    payback_years: Optional[float] = None
    min_dscr: Optional[float] = None
    total_capex_usd: Optional[float] = None
    miri_score: Optional[float] = None   # Market Investment Readiness Index (0-100)
    governance_score: Optional[float] = None  # 0-100
    fee_collection_rate: Optional[float] = None
    notes: str = ""

@dataclass
class MarketComparisonResult:
    """Results of a multi-market comparison."""
    markets: list[MarketProfile] = field(default_factory=list)

    def npv_ranking(self) -> list[str]:
        """Return market names sorted by NPV descending (None last)."""
        ranked = sorted(
            self.markets,
            key=lambda m: m.npv_usd if m.npv_usd is not None else float("-inf"),
            reverse=True,
        )
        return [m.name for m in ranked]

    def irr_ranking(self) -> list[str]:
        """Return market names sorted by IRR descending."""
        ranked = sorted(
            self.markets,
            key=lambda m: m.irr if m.irr is not None else float("-inf"),
            reverse=True,
        )
        return [m.name for m in ranked]

    def investment_ready(self, min_irr: float = 0.12, min_dscr: float = 1.2) -> list[str]:
        """Return names of markets meeting minimum investment thresholds."""
        return [
            m.name for m in self.markets
            if (m.irr is not None and m.irr >= min_irr)
            and (m.min_dscr is None or m.min_dscr >= min_dscr)
        ]

    def summary_table(self) -> list[dict]:
        rows = []
        for m in self.markets:
            rows.append({
                "market": m.name,
                "country": m.country,
                "npv_usd": m.npv_usd,
                "irr_pct": round(m.irr * 100, 1) if m.irr is not None else None,
                "payback_years": m.payback_years,
                "min_dscr": m.min_dscr,
                "miri_score": m.miri_score,
                "governance_score": m.governance_score,
                "fee_collection_rate": m.fee_collection_rate,
            })
        return rows

def compare_markets(markets: list[MarketProfile]) -> MarketComparisonResult:
    """Compare a list of market profiles."""
    return MarketComparisonResult(markets=list(markets))
