"""
Anomaly detection for financial model inputs and AI outputs.

Flags suspicious numbers using rule-based checks and optionally Claude.
Key rules:
- Solar PV CAPEX > 80% of annual existing revenue → flag (field data lesson)
- Values outside PLAUSIBLE_BOUNDS → flag
- Internal inconsistencies (negative revenue + positive margin, etc.)

All rule-based detection is deterministic — no AI required.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from mmfm.validation.bounds_checker import check_bounds, BoundsStatus


@dataclass
class Anomaly:
    metric: str
    value: float
    reason: str
    severity: str  # "high" | "medium" | "low"
    rule: str      # Which rule triggered this


@dataclass
class AnomalyReport:
    anomalies: list[Anomaly] = field(default_factory=list)
    overall_data_quality: str = "good"   # "good" | "acceptable" | "poor"

    @property
    def high_severity(self) -> list[Anomaly]:
        return [a for a in self.anomalies if a.severity == "high"]

    @property
    def has_anomalies(self) -> bool:
        return len(self.anomalies) > 0

    def add(self, metric: str, value: float, reason: str, severity: str, rule: str) -> None:
        self.anomalies.append(Anomaly(metric=metric, value=value, reason=reason,
                                      severity=severity, rule=rule))
        if severity == "high" and self.overall_data_quality == "good":
            self.overall_data_quality = "acceptable"
        if len(self.high_severity) >= 2:
            self.overall_data_quality = "poor"


def detect_anomalies(metrics: dict, annual_existing_revenue: Optional[float] = None) -> AnomalyReport:
    """
    Run all rule-based anomaly checks on a metrics dictionary.

    Args:
        metrics: Dict of metric_name -> value (from engine calculations)
        annual_existing_revenue: Current annual revenue (for Solar PV ratio check)

    Returns:
        AnomalyReport listing all detected anomalies
    """
    report = AnomalyReport()

    for metric_name, value in metrics.items():
        if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
            continue

        result = check_bounds(metric_name, value)
        if result.status == BoundsStatus.FAIL:
            report.add(
                metric=metric_name,
                value=value,
                reason=f"Value {value:.4f} is outside plausible bounds [{result.min_bound}, {result.max_bound}]",
                severity="high",
                rule="bounds_check",
            )
        elif result.status == BoundsStatus.WARNING:
            report.add(
                metric=metric_name,
                value=value,
                reason=f"Value {value:.4f} is near boundary [{result.min_bound}, {result.max_bound}]",
                severity="low",
                rule="bounds_warning",
            )

    # ── Solar PV CAPEX disproportion rule ──────────────────────────────────
    # Flag if Solar PV CAPEX > 80% of the market's annual existing revenue.
    # This near-inviable bundle requires TA support (field case: $1.07M solar vs $1.03M revenue).
    solar_capex = metrics.get("solar_pv_capex")
    if solar_capex is not None and annual_existing_revenue is not None:
        if annual_existing_revenue > 0:
            ratio = solar_capex / annual_existing_revenue
            if ratio > 0.80:
                report.add(
                    metric="solar_pv_capex",
                    value=solar_capex,
                    reason=(
                        f"Solar PV CAPEX ({solar_capex:,.0f}) is {ratio:.0%} of annual existing revenue "
                        f"({annual_existing_revenue:,.0f}). Ratio > 80% indicates a near-inviable bundle "
                        "without technical assistance (TA) support. "
                        "Reference: field case — $1.07M solar vs $1.03M annual revenue."
                    ),
                    severity="high",
                    rule="solar_pv_capex_disproportion",
                )

    # ── Internal consistency checks ────────────────────────────────────────
    npv = metrics.get("npv")
    irr = metrics.get("irr")

    # If NPV is positive but IRR is below discount rate — inconsistency
    discount_rate = metrics.get("discount_rate", 0.10)
    if npv is not None and irr is not None:
        if npv > 0 and irr is not None and irr < discount_rate:
            report.add(
                metric="irr",
                value=irr,
                reason=f"NPV is positive ({npv:,.0f}) but IRR ({irr:.1%}) is below discount rate ({discount_rate:.1%}). "
                       "This is mathematically inconsistent — verify cash flow inputs.",
                severity="high",
                rule="npv_irr_consistency",
            )

    # Operating margin > 0.95 is implausible for municipal markets
    op_margin = metrics.get("operating_margin")
    if op_margin is not None and not math.isnan(op_margin) and op_margin > 0.95:
        report.add(
            metric="operating_margin",
            value=op_margin,
            reason=f"Operating margin of {op_margin:.1%} is implausibly high for a municipal market. "
                   "Check for missing cost line items.",
            severity="medium",
            rule="operating_margin_ceiling",
        )

    return report
