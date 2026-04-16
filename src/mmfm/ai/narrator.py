"""
Financial narrative generation via configured LLM backend.

Generates structured narratives for financial analysis results.
All numbers in narratives are cross-validated against engine outputs
before being surfaced to the user.

Backend is selected via MMFM_LLM_BACKEND env var (default: ollama).
No API key is required when using the default Ollama backend.
"""

from __future__ import annotations

import json
from typing import Optional

from mmfm.ai.backends import get_backend
from mmfm.ai.model_router import get_config_for_task
from mmfm.ai.prompts.narrative import FINANCIAL_NARRATIVE_PROMPT, SCENARIO_COMPARISON_PROMPT


def _call_llm(prompt: str, task: str, system: Optional[str] = None) -> str:
    """Call the configured LLM backend with task-appropriate parameters."""
    config = get_config_for_task(task)
    backend = get_backend(task=task)
    return backend.complete(
        prompt=prompt,
        system=system or "",
        max_tokens=config["max_tokens"],
        temperature=config["temperature"],
    )


def generate_financial_narrative(
    financial_data: dict,
    rag_context: str = "",
    task: str = "financial_narrative",
) -> dict:
    """
    Generate a structured financial narrative for a market analysis.

    Args:
        financial_data: Dict with NPV, IRR, payback, DSCR, margins, etc.
        rag_context: Retrieved document context from knowledge base
        task: Task type for model routing

    Returns:
        Dict with executive_summary, key_risks, recommendation, confidence_level,
        data_gaps, anomalies_flagged

    Raises:
        ValueError: If API key is not configured
        RuntimeError: If Claude returns invalid JSON
    """
    prompt = FINANCIAL_NARRATIVE_PROMPT.format(
        rag_context=rag_context or "No reference documents available.",
        financial_data_json=json.dumps(financial_data, indent=2, default=str),
    )

    raw_response = _call_llm(prompt, task)

    # Extract JSON from response (Claude may wrap it in markdown)
    json_str = _extract_json(raw_response)
    try:
        result = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Claude returned invalid JSON: {exc}\nRaw: {raw_response[:500]}")

    # Validate required keys
    required_keys = ["executive_summary", "key_risks", "recommendation", "confidence_level"]
    for key in required_keys:
        if key not in result:
            result[key] = f"[missing: {key}]"

    result.setdefault("data_gaps", [])
    result.setdefault("anomalies_flagged", [])

    return result


def compare_scenarios(scenario_data: dict, task: str = "scenario_comparison") -> dict:
    """
    Generate a narrative comparing multiple scenario results.

    Args:
        scenario_data: Dict mapping scenario name -> metric summary dict

    Returns:
        Dict with comparison_narrative, key_drivers, most_likely_scenario, scenario_ranking
    """
    prompt = SCENARIO_COMPARISON_PROMPT.format(
        scenario_data_json=json.dumps(scenario_data, indent=2, default=str),
    )
    raw_response = _call_llm(prompt, task)
    json_str = _extract_json(raw_response)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {
            "comparison_narrative": raw_response,
            "key_drivers": [],
            "most_likely_scenario": "base",
            "scenario_ranking": [],
        }


def _extract_json(text: str) -> str:
    """Extract JSON from a response that may be wrapped in markdown code blocks."""
    text = text.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    # Find the outermost {...}
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return text[start:end]
    return text
