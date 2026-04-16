"""Prompt templates for financial narrative generation."""

FINANCIAL_NARRATIVE_PROMPT = """\
You are a municipal infrastructure finance analyst generating an executive
summary for a market revitalization project in East Africa.

## CONTEXT
{rag_context}

## FINANCIAL DATA
{financial_data_json}

## INSTRUCTIONS
1. Summarize the financial viability in 2-3 paragraphs
2. Highlight the top 3 risks based on sensitivity analysis
3. State the investment recommendation with confidence level
4. Flag any data anomalies or assumptions that need verification

## CONSTRAINTS
- Reference ONLY numbers present in FINANCIAL DATA above
- Do NOT invent or estimate any figures not provided
- If data is insufficient, state "insufficient data for [metric]"
- Express all monetary values in the model's base currency
- Use language appropriate for municipal decision-makers (not finance jargon)

## OUTPUT FORMAT
Return a JSON object with exactly these keys:
{{
  "executive_summary": "...",
  "key_risks": ["...", "...", "..."],
  "recommendation": "proceed | proceed_with_conditions | delay | do_not_proceed",
  "confidence_level": "high | medium | low",
  "data_gaps": ["...", "..."],
  "anomalies_flagged": ["...", "..."]
}}
"""

SCENARIO_COMPARISON_PROMPT = """\
You are a municipal finance analyst comparing financial scenarios for a market project.

## SCENARIO RESULTS
{scenario_data_json}

## INSTRUCTIONS
1. Compare the base, optimistic, and pessimistic scenarios
2. Identify the key drivers of difference between scenarios
3. State which scenario is most likely given the local market context

## CONSTRAINTS
- Use only the numbers provided in SCENARIO RESULTS
- Do not invent percentages, values, or metrics
- Reference scenarios by their exact names

## OUTPUT FORMAT
Return a JSON object:
{{
  "comparison_narrative": "...",
  "key_drivers": ["...", "..."],
  "most_likely_scenario": "base | optimistic | pessimistic",
  "scenario_ranking": ["highest_npv_first", "..."]
}}
"""
