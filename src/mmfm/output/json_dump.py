"""Machine-readable JSON output."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _clean_floats(obj: Any) -> Any:
    """Replace NaN/Inf with None for valid JSON."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_floats(v) for v in obj]
    return obj


def metrics_to_dict(npv, irr, payback, dscr=None, margin=None) -> dict:
    """Convert core metric results to a JSON-serializable dict."""
    out = {
        "npv": {
            "value": npv.value,
            "discount_rate": npv.discount_rate,
            "is_positive": npv.is_positive,
        },
        "irr": {
            "value": irr.value,
            "converged": irr.converged,
            "message": irr.message,
        },
        "payback": {
            "years": payback.years,
            "reached": payback.reached,
        },
    }
    if dscr:
        out["dscr"] = {
            "values": dscr.values,
            "years": dscr.years,
            "min_dscr": dscr.min_dscr,
            "min_dscr_year": dscr.min_dscr_year,
            "below_threshold": dscr.below_threshold,
        }
    if margin:
        out["operating_margin"] = {
            "values": margin.values,
            "years": margin.years,
            "average": margin.average,
            "trend": margin.trend,
        }
    return _clean_floats(out)


def dump_to_file(data: dict, output_path: Path | str) -> None:
    """Write data dict to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
