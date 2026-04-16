"""
Source attribution and provenance tracking.

Every number surfaced in output must have a traceable source:
- Excel cell reference
- Document chunk ID
- Engine formula
- AI-generated (flagged for review)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


SourceType = Literal["cell", "formula", "document", "calculated", "ai_generated"]


@dataclass
class ProvenanceRecord:
    value: float
    source_type: SourceType
    source_ref: str              # e.g., "model.xlsx!Revenue!B14" or "pemba_report.pdf:chunk_23"
    calculation_chain: list[str] = field(default_factory=list)
    confidence: float = 1.0      # 0.0 to 1.0
    verified: bool = False


@dataclass
class VerificationResult:
    metric: str
    engine_value: Optional[float]
    ai_value: Optional[float]
    match: bool
    tolerance: float
    message: str


class ProvenanceTracker:
    """
    Maintains a ledger of every number used and generated.

    AI outputs with source_type="ai_generated" are always flagged
    for human review unless cross-validated against engine output.
    """

    def __init__(self):
        self._ledger: dict[str, ProvenanceRecord] = {}

    def register(self, metric: str, value: float, provenance: ProvenanceRecord) -> None:
        """Log the provenance of a value."""
        self._ledger[metric] = provenance

    def register_cell(self, metric: str, value: float, file: str, sheet: str, cell: str) -> None:
        """Register a value sourced from an Excel cell."""
        self.register(metric, value, ProvenanceRecord(
            value=value,
            source_type="cell",
            source_ref=f"{file}!{sheet}!{cell}",
            confidence=1.0,
            verified=True,
        ))

    def register_calculated(self, metric: str, value: float, formula: str, inputs: list[str]) -> None:
        """Register a value computed by the engine."""
        self.register(metric, value, ProvenanceRecord(
            value=value,
            source_type="calculated",
            source_ref=f"engine:{formula}",
            calculation_chain=inputs,
            confidence=1.0,
            verified=True,
        ))

    def register_ai(self, metric: str, value: float, source_chunk: str) -> None:
        """Register an AI-generated value (unverified until cross-validated)."""
        self.register(metric, value, ProvenanceRecord(
            value=value,
            source_type="ai_generated",
            source_ref=f"claude:{source_chunk}",
            confidence=0.5,
            verified=False,
        ))

    def verify(self, metric: str, engine_value: float, tolerance: float = 0.0001) -> VerificationResult:
        """Cross-check a registered value against the engine value."""
        record = self._ledger.get(metric)
        if record is None:
            return VerificationResult(
                metric=metric, engine_value=engine_value, ai_value=None,
                match=False, tolerance=tolerance,
                message=f"No record found for metric '{metric}'",
            )

        ai_value = record.value
        if engine_value == 0:
            match = abs(ai_value) < tolerance
        else:
            match = abs(ai_value - engine_value) / abs(engine_value) < tolerance

        if match:
            record.verified = True
            record.confidence = 1.0

        return VerificationResult(
            metric=metric,
            engine_value=engine_value,
            ai_value=ai_value,
            match=match,
            tolerance=tolerance,
            message="Verified" if match else f"MISMATCH: engine={engine_value}, ai={ai_value}",
        )

    def get_unverified(self) -> dict[str, ProvenanceRecord]:
        """Return all AI-generated values that have not been verified."""
        return {
            k: v for k, v in self._ledger.items()
            if v.source_type == "ai_generated" and not v.verified
        }

    def audit_report(self) -> dict:
        """Generate full audit trail of all values and their sources."""
        return {
            metric: {
                "value": rec.value,
                "source_type": rec.source_type,
                "source_ref": rec.source_ref,
                "calculation_chain": rec.calculation_chain,
                "confidence": rec.confidence,
                "verified": rec.verified,
            }
            for metric, rec in self._ledger.items()
        }
