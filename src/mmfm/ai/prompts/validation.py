"""Prompt templates for AI output validation."""

VALIDATION_PROMPT = """\
You are a financial model validator. Review the AI-generated narrative below
and verify that every number cited matches the provided source data.

## AI NARRATIVE
{narrative_text}

## SOURCE DATA (ground truth)
{source_data_json}

## INSTRUCTIONS
For each number mentioned in the narrative:
1. Locate it in the source data
2. Flag any number that does not appear in source data (potential hallucination)
3. Flag any directional claim (e.g., "revenue is increasing") that contradicts source data

## OUTPUT FORMAT
Return a JSON object:
{{
  "numbers_verified": [{{"value": 0.0, "found_in_source": true}}],
  "hallucinated_numbers": [0.0],
  "directional_errors": ["description of error"],
  "validation_passed": true
}}
"""
