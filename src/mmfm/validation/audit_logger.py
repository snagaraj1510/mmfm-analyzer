"""
Full computation audit trail for MMFM outputs.

Logs every calculation step so outputs can be fully traced.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AuditLogger:
    """
    Records every computation step and AI interaction.

    Audit entries include:
    - Timestamp
    - Operation type (calculation, ai_call, validation, ingestion)
    - Input values
    - Output values
    - Source attribution
    """

    def __init__(self, log_file: Optional[Path] = None):
        self._entries: list[dict] = []
        self._log_file = log_file

    def log(
        self,
        operation: str,
        inputs: dict,
        output,
        source: str = "",
        notes: str = "",
    ) -> None:
        """Log a computation step."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "inputs": inputs,
            "output": output,
            "source": source,
            "notes": notes,
        }
        self._entries.append(entry)

        if self._log_file:
            with open(self._log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def log_calculation(self, metric: str, formula: str, inputs: dict, result: float) -> None:
        self.log(
            operation="calculation",
            inputs={"metric": metric, "formula": formula, **inputs},
            output=result,
            source="engine",
        )

    def log_ai_call(self, task: str, model: str, prompt_tokens: int, completion_tokens: int,
                    cost_usd: float) -> None:
        self.log(
            operation="ai_call",
            inputs={"task": task, "model": model, "prompt_tokens": prompt_tokens},
            output={"completion_tokens": completion_tokens, "cost_usd": cost_usd},
            source=model,
        )

    def log_validation(self, metric: str, value: float, status: str, message: str) -> None:
        self.log(
            operation="validation",
            inputs={"metric": metric, "value": value},
            output={"status": status, "message": message},
            source="validator",
        )

    def export(self) -> list[dict]:
        """Return the full audit log."""
        return list(self._entries)

    def export_json(self, output_path: Path) -> None:
        """Write the full audit log to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self._entries, f, indent=2, default=str)

    def summary(self) -> dict:
        """Return a summary of audit log entries by operation type."""
        by_op: dict[str, int] = {}
        for entry in self._entries:
            op = entry.get("operation", "unknown")
            by_op[op] = by_op.get(op, 0) + 1
        return {"total_entries": len(self._entries), "by_operation": by_op}
