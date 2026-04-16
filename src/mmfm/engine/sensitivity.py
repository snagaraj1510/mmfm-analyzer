"""
Sensitivity and tornado analysis for MMFM Analyzer.

Tests each input variable independently across a range of values
to measure its impact on NPV. Results are suitable for tornado chart display.
All computations are deterministic — no AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from mmfm.engine.projections import (
    RevenueInputs,
    CapexInputs,
    OpexInputs,
    project_cash_flows,
)
from mmfm.engine.core_metrics import calculate_npv


# ── Sensitivity variable definitions ────────────────────────────────────────

SENSITIVITY_VARIABLES = [
    {"name": "occupancy_rate",                  "range": (0.30, 0.95), "step": 0.05,  "label": "Occupancy Rate"},
    {"name": "rental_escalation_rate",          "range": (0.00, 0.12), "step": 0.01,  "label": "Rental Escalation Rate"},
    {"name": "capex_overrun_pct",               "range": (0.00, 0.50), "step": 0.05,  "label": "Capex Overrun %"},
    {"name": "discount_rate",                   "range": (0.05, 0.20), "step": 0.01,  "label": "Discount Rate"},
    {"name": "inflation_rate",                  "range": (0.02, 0.15), "step": 0.01,  "label": "Inflation Rate"},
    {"name": "grant_disbursement_delay_years",  "range": (0, 3),       "step": 1,     "label": "Grant Delay (years)"},
    {"name": "opex_escalation_rate",            "range": (0.02, 0.12), "step": 0.01,  "label": "Opex Escalation Rate"},
]


@dataclass
class SensitivityPoint:
    variable_value: float
    npv: float


@dataclass
class VariableSensitivity:
    """NPV results for a single variable swept across its range."""
    variable_name: str
    label: str
    base_value: float
    base_npv: float
    points: list[SensitivityPoint] = field(default_factory=list)

    @property
    def npv_values(self) -> list[float]:
        return [p.npv for p in self.points]

    @property
    def variable_values(self) -> list[float]:
        return [p.variable_value for p in self.points]

    @property
    def npv_swing(self) -> float:
        """Total NPV swing = max - min NPV across the variable's range."""
        vals = self.npv_values
        if not vals:
            return 0.0
        return max(vals) - min(vals)

    @property
    def npv_at_low(self) -> float:
        """NPV at the lowest variable value."""
        return self.points[0].npv if self.points else self.base_npv

    @property
    def npv_at_high(self) -> float:
        """NPV at the highest variable value."""
        return self.points[-1].npv if self.points else self.base_npv


@dataclass
class SensitivityResult:
    """Full sensitivity analysis across all variables."""
    base_npv: float
    discount_rate: float
    variables: list[VariableSensitivity] = field(default_factory=list)

    def tornado_order(self) -> list[VariableSensitivity]:
        """Return variables sorted by NPV swing descending (tornado chart order)."""
        return sorted(self.variables, key=lambda v: v.npv_swing, reverse=True)


def _compute_npv_for_params(
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    discount_rate: float,
    inflation_rate: float,
    horizon_years: int,
    overrides: dict,
) -> float:
    """Apply overrides to inputs and return NPV."""
    # Build modified inputs
    rev = RevenueInputs(
        base_stall_rental_income=revenue.base_stall_rental_income,
        occupancy_rate=overrides.get("occupancy_rate", revenue.occupancy_rate),
        vendor_fees_annual=revenue.vendor_fees_annual,
        market_levies_annual=revenue.market_levies_annual,
        rental_escalation_rate=overrides.get("rental_escalation_rate", revenue.rental_escalation_rate),
        fee_escalation_rate=revenue.fee_escalation_rate,
        occupancy_ramp_years=revenue.occupancy_ramp_years,
        occupancy_target=overrides.get("occupancy_target", revenue.occupancy_target),
        other_income_annual=revenue.other_income_annual,
    )
    cap = CapexInputs(
        total_capex=capex.total_capex,
        construction_schedule=capex.construction_schedule,
        overrun_contingency=overrides.get("capex_overrun_pct", capex.overrun_contingency),
        grant_amount=capex.grant_amount,
        grant_disbursement_year=capex.grant_disbursement_year + int(overrides.get("grant_disbursement_delay_years", 0)),
    )
    op = OpexInputs(
        base_opex=opex.base_opex,
        opex_escalation_rate=overrides.get("opex_escalation_rate", opex.opex_escalation_rate),
        debt_service_annual=opex.debt_service_annual,
    )
    eff_discount = overrides.get("discount_rate", discount_rate)
    eff_inflation = overrides.get("inflation_rate", inflation_rate)

    projection = project_cash_flows(rev, cap, op, horizon_years=horizon_years, inflation_rate=eff_inflation)
    result = calculate_npv(projection.get_cash_flows(), eff_discount)
    return result.value


def run_sensitivity(
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    discount_rate: float = 0.10,
    inflation_rate: float = 0.05,
    horizon_years: int = 20,
    variables: Optional[list[dict]] = None,
) -> SensitivityResult:
    """
    Run sensitivity analysis on each variable independently.

    For each variable, sweeps its value across its defined range while
    holding all other variables at their base values.

    Args:
        revenue: Base revenue inputs
        capex: Base capex inputs
        opex: Base opex inputs
        discount_rate: Base discount rate
        inflation_rate: Base inflation rate
        horizon_years: Projection horizon
        variables: Variable specs (defaults to SENSITIVITY_VARIABLES)

    Returns:
        SensitivityResult with per-variable NPV curves
    """
    if variables is None:
        variables = SENSITIVITY_VARIABLES

    # Compute base NPV
    base_npv = _compute_npv_for_params(
        revenue, capex, opex, discount_rate, inflation_rate, horizon_years, {}
    )

    result = SensitivityResult(base_npv=base_npv, discount_rate=discount_rate)

    # Base values for each variable
    base_values = {
        "occupancy_rate": revenue.occupancy_rate,
        "rental_escalation_rate": revenue.rental_escalation_rate,
        "capex_overrun_pct": capex.overrun_contingency,
        "discount_rate": discount_rate,
        "inflation_rate": inflation_rate,
        "grant_disbursement_delay_years": 0,
        "opex_escalation_rate": opex.opex_escalation_rate,
    }

    for var_spec in variables:
        var_name = var_spec["name"]
        low, high = var_spec["range"]
        step = var_spec["step"]
        label = var_spec.get("label", var_name)
        base_val = base_values.get(var_name, (low + high) / 2)

        values = list(np.arange(low, high + step / 2, step))

        var_sens = VariableSensitivity(
            variable_name=var_name,
            label=label,
            base_value=base_val,
            base_npv=base_npv,
        )

        for val in values:
            npv = _compute_npv_for_params(
                revenue, capex, opex, discount_rate, inflation_rate, horizon_years,
                {var_name: float(val)},
            )
            var_sens.points.append(SensitivityPoint(variable_value=float(val), npv=npv))

        result.variables.append(var_sens)

    return result


def run_single_variable_sensitivity(
    variable_name: str,
    revenue: RevenueInputs,
    capex: CapexInputs,
    opex: OpexInputs,
    discount_rate: float = 0.10,
    inflation_rate: float = 0.05,
    horizon_years: int = 20,
) -> VariableSensitivity:
    """Run sensitivity on a single named variable."""
    var_spec = next((v for v in SENSITIVITY_VARIABLES if v["name"] == variable_name), None)
    if var_spec is None:
        raise ValueError(
            f"Unknown variable: '{variable_name}'. "
            f"Valid variables: {[v['name'] for v in SENSITIVITY_VARIABLES]}"
        )
    full_result = run_sensitivity(
        revenue, capex, opex, discount_rate, inflation_rate, horizon_years,
        variables=[var_spec],
    )
    return full_result.variables[0]
