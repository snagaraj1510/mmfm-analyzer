"""Prompt templates for anomaly detection."""

ANOMALY_DETECTION_PROMPT = """\
You are a financial auditor reviewing a municipal market financial model for data anomalies.

## FINANCIAL METRICS
{metrics_json}

## KNOWN BOUNDS
{bounds_json}

## INSTRUCTIONS
Review the financial metrics and identify any values that appear:
1. Outside physically plausible ranges for East African municipal markets
2. Internally inconsistent (e.g., high occupancy + negative revenue)
3. Unusually high or low compared to benchmarks

## CONSTRAINTS
- Only flag genuine anomalies, not normal variation
- Cite the specific metric and value for each anomaly
- Do not invent metrics or values not present in the input

## OUTPUT FORMAT
Return a JSON object:
{{
  "anomalies": [
    {{
      "metric": "metric_name",
      "value": 0.0,
      "reason": "explanation",
      "severity": "high | medium | low"
    }}
  ],
  "overall_data_quality": "good | acceptable | poor",
  "review_required": true
}}
"""
