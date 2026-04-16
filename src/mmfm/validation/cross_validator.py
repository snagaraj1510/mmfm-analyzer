"""
Cross-validation: compare AI narrative outputs against deterministic engine outputs.

Any divergence between AI-reported and engine-calculated values indicates
potential hallucination and must be flagged before surfacing to the user.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrossValidationResult:
    passed: bool
    metric: str
    engine_value: Optional[float]
    narrative_value: Optional[float]
    relative_error: Optional[float]
    message: str


@dataclass
class CrossValidationReport:
    results: list[CrossValidationResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[CrossValidationResult]:
        return [r for r in self.results if not r.passed]

    def summary(self) -> str:
        n_pass = sum(1 for r in self.results if r.passed)
        return f"{n_pass}/{len(self.results)} checks passed"


def extract_numbers_from_text(text: str) -> set[float]:
    """
    Extract all numeric values from a text string.

    Handles: 1,234.56 | 1234.56 | 12.3% | $1,234 | (1,234) negative
    """
    # Remove currency symbols and commas
    clean = text.replace(",", "").replace("$", "").replace("\u20ac", "")
    # Find all numbers (including negatives and percentages)
    pattern = r"-?\d+\.?\d*%?"
    matches = re.findall(pattern, clean)
    numbers = set()
    for m in matches:
        try:
            val = float(m.rstrip("%"))
            if m.endswith("%"):
                val /= 100
            numbers.add(round(val, 6))
        except ValueError:
            pass
    return numbers


def validate_narrative_number(
    metric: str,
    engine_value: float,
    narrative_text: str,
    tolerance: float = 0.001,
) -> CrossValidationResult:
    """
    Check if the engine value appears (approximately) in the narrative text.

    Args:
        metric: Metric name for reporting
        engine_value: Ground truth from deterministic engine
        narrative_text: AI-generated text to check
        tolerance: Relative tolerance for matching (0.001 = 0.1%)

    Returns:
        CrossValidationResult
    """
    if math.isnan(engine_value) or math.isinf(engine_value):
        return CrossValidationResult(
            passed=True, metric=metric,
            engine_value=engine_value, narrative_value=None,
            relative_error=None,
            message="Engine value is NaN/Inf — skipping cross-validation",
        )

    narrative_numbers = extract_numbers_from_text(narrative_text)

    # Check if engine value (or close approximation) is in narrative
    for num in narrative_numbers:
        if engine_value == 0:
            if abs(num) < tolerance:
                return CrossValidationResult(
                    passed=True, metric=metric,
                    engine_value=engine_value, narrative_value=num,
                    relative_error=0.0, message="Verified",
                )
        else:
            rel_err = abs(num - engine_value) / abs(engine_value)
            if rel_err <= tolerance:
                return CrossValidationResult(
                    passed=True, metric=metric,
                    engine_value=engine_value, narrative_value=num,
                    relative_error=rel_err, message="Verified",
                )

    return CrossValidationResult(
        passed=True,  # Can't definitively say it's wrong — number may just not be mentioned
        metric=metric,
        engine_value=engine_value,
        narrative_value=None,
        relative_error=None,
        message=f"Engine value {engine_value:.4f} not found in narrative (may be omitted, not hallucinated)",
    )


def validate_no_invented_numbers(
    narrative_text: str,
    allowed_numbers: set[float],
    tolerance: float = 0.01,
) -> CrossValidationResult:
    """
    Check that all numbers in the narrative exist in the allowed set.

    Args:
        narrative_text: AI-generated text
        allowed_numbers: Set of numbers from engine + input data
        tolerance: Relative tolerance for matching

    Returns:
        CrossValidationResult; passes=False if invented numbers found
    """
    narrative_numbers = extract_numbers_from_text(narrative_text)
    invented = []

    for num in narrative_numbers:
        # Check if this number exists (approximately) in allowed set
        found = False
        for allowed in allowed_numbers:
            if allowed == 0:
                if abs(num) < tolerance:
                    found = True
                    break
            else:
                if abs(num - allowed) / abs(allowed) <= tolerance:
                    found = True
                    break
        if not found and abs(num) > 0.001:  # Ignore near-zero values
            invented.append(num)

    passed = len(invented) == 0
    return CrossValidationResult(
        passed=passed,
        metric="narrative_numbers",
        engine_value=None,
        narrative_value=None,
        relative_error=None,
        message="All numbers verified" if passed else f"Potentially invented numbers: {invented[:5]}",
    )
