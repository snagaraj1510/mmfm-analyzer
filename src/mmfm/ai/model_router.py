"""
Claude model routing logic.

Routes tasks to the appropriate Claude model based on complexity
and cost optimization. Haiku for classification, Sonnet for narrative,
Opus for final synthesis.

API keys are read from environment — never hardcoded here.
"""

from __future__ import annotations

from typing import Literal, Optional

TaskType = Literal[
    "schema_detection", "column_classification", "unit_extraction",
    "language_detection", "simple_summarization", "label_generation",
    "format_validation",
    "financial_narrative", "anomaly_explanation", "scenario_comparison",
    "risk_assessment", "rag_synthesis", "report_section_draft",
    "sensitivity_interpretation", "recommendation_draft",
    "full_report_synthesis", "cross_model_validation", "complex_anomaly_triage",
    "methodology_review", "multi_market_comparison", "final_recommendation",
]

MODEL_ROUTING: dict[str, dict] = {
    "haiku": {
        "model": "claude-haiku-4-5-20251001",
        "tasks": [
            "schema_detection", "column_classification", "unit_extraction",
            "language_detection", "simple_summarization", "label_generation",
            "format_validation",
        ],
        "max_tokens": 1024,
        "temperature": 0.0,
        "estimated_cost_per_call": "$0.001-0.005",
    },
    "sonnet": {
        "model": "claude-sonnet-4-20250514",
        "tasks": [
            "financial_narrative", "anomaly_explanation", "scenario_comparison",
            "risk_assessment", "rag_synthesis", "report_section_draft",
            "sensitivity_interpretation", "recommendation_draft",
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
        "estimated_cost_per_call": "$0.01-0.05",
    },
    "opus": {
        "model": "claude-opus-4-20250514",
        "tasks": [
            "full_report_synthesis", "cross_model_validation", "complex_anomaly_triage",
            "methodology_review", "multi_market_comparison", "final_recommendation",
        ],
        "max_tokens": 8192,
        "temperature": 0.1,
        "estimated_cost_per_call": "$0.05-0.30",
    },
}

TOKEN_BUDGETS: dict[str, dict] = {
    "ingestion_classification": {
        "model": "haiku", "input_budget": 2000, "output_budget": 500, "batch_eligible": True,
    },
    "narrative_generation": {
        "model": "sonnet", "input_budget": 6000, "output_budget": 2000, "batch_eligible": False,
    },
    "full_report": {
        "model": "opus", "input_budget": 12000, "output_budget": 4000, "batch_eligible": False,
    },
}

# Approximate cost per 1M tokens (input/output) in USD
COST_PER_1M_TOKENS = {
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
    "claude-sonnet-4-20250514":   {"input": 3.00,  "output": 15.00},
    "claude-opus-4-20250514":     {"input": 15.00, "output": 75.00},
}


def get_model_for_task(task: TaskType) -> str:
    """Return the model ID for a given task type."""
    for tier, config in MODEL_ROUTING.items():
        if task in config["tasks"]:
            return config["model"]
    # Default to Sonnet for unknown tasks
    return MODEL_ROUTING["sonnet"]["model"]


def get_config_for_task(task: TaskType) -> dict:
    """Return the full model config (model id, max_tokens, temperature) for a task."""
    for tier, config in MODEL_ROUTING.items():
        if task in config["tasks"]:
            return {
                "model": config["model"],
                "max_tokens": config["max_tokens"],
                "temperature": config["temperature"],
            }
    return {
        "model": MODEL_ROUTING["sonnet"]["model"],
        "max_tokens": MODEL_ROUTING["sonnet"]["max_tokens"],
        "temperature": MODEL_ROUTING["sonnet"]["temperature"],
    }


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int = 500) -> float:
    """Estimate API call cost in USD."""
    costs = COST_PER_1M_TOKENS.get(model_id, COST_PER_1M_TOKENS["claude-sonnet-4-20250514"])
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1_000_000
