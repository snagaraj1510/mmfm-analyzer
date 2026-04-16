"""
Hallucination-detection tests for the AI narrative layer.

All LLM calls are mocked. These tests verify that:
1. generate_financial_narrative() returns the correct keys
2. _extract_json() correctly extracts JSON from various wrappings
3. generate_financial_narrative() handles JSON-decode errors gracefully
4. compare_scenarios() falls back gracefully on bad LLM output
5. The narrator does not call the LLM at all when not expected to
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from mmfm.ai.narrator import (
    _extract_json,
    generate_financial_narrative,
    compare_scenarios,
)


class TestExtractJson:
    def test_plain_json(self):
        raw = '{"key": "value"}'
        assert _extract_json(raw) == '{"key": "value"}'

    def test_markdown_json_fence(self):
        raw = '```json\n{"key": "value"}\n```'
        result = _extract_json(raw)
        assert json.loads(result) == {"key": "value"}

    def test_markdown_plain_fence(self):
        raw = '```\n{"key": "value"}\n```'
        result = _extract_json(raw)
        assert json.loads(result) == {"key": "value"}

    def test_json_embedded_in_prose(self):
        raw = 'Here is the result: {"score": 42} — end.'
        result = _extract_json(raw)
        assert json.loads(result) == {"score": 42}

    def test_no_json_returns_original(self):
        raw = "No JSON here at all"
        assert _extract_json(raw) == "No JSON here at all"


class TestGenerateFinancialNarrative:
    """All tests mock the LLM backend — no API key required."""

    def _mock_backend(self, response_dict: dict):
        """Return a context manager that patches get_backend with a mock returning JSON."""
        mock_backend = MagicMock()
        mock_backend.complete.return_value = json.dumps(response_dict)
        mock_get = MagicMock(return_value=mock_backend)
        return patch("mmfm.ai.narrator.get_backend", mock_get)

    def test_returns_required_keys(self):
        fake_response = {
            "executive_summary": "The market shows strong NPV.",
            "key_risks": ["collection risk", "overrun risk"],
            "recommendation": "proceed",
            "confidence_level": "high",
            "data_gaps": [],
            "anomalies_flagged": [],
        }
        with self._mock_backend(fake_response):
            result = generate_financial_narrative({"npv": 500000, "irr": 0.18})

        for key in ["executive_summary", "key_risks", "recommendation", "confidence_level"]:
            assert key in result, f"Missing required key: {key}"

    def test_missing_keys_filled_with_placeholder(self):
        """LLM returns partial JSON — missing keys should get placeholder values."""
        partial = {"executive_summary": "Short summary."}
        with self._mock_backend(partial):
            result = generate_financial_narrative({"npv": 100000})

        assert result["key_risks"] == "[missing: key_risks]"
        assert result["recommendation"] == "[missing: recommendation]"
        assert result["confidence_level"] == "[missing: confidence_level]"

    def test_data_gaps_defaults_to_empty_list(self):
        fake_response = {
            "executive_summary": "X", "key_risks": [], "recommendation": "proceed",
            "confidence_level": "medium",
        }
        with self._mock_backend(fake_response):
            result = generate_financial_narrative({})

        assert result["data_gaps"] == []
        assert result["anomalies_flagged"] == []

    def test_invalid_json_raises_runtime_error(self):
        mock_backend = MagicMock()
        mock_backend.complete.return_value = "This is not JSON at all."
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            with pytest.raises(RuntimeError, match="invalid JSON"):
                generate_financial_narrative({"npv": 100})

    def test_llm_called_once(self):
        """generate_financial_narrative makes exactly one LLM call."""
        fake_response = {
            "executive_summary": "ok", "key_risks": [], "recommendation": "proceed",
            "confidence_level": "low",
        }
        mock_backend = MagicMock()
        mock_backend.complete.return_value = json.dumps(fake_response)
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            generate_financial_narrative({"npv": 0})

        mock_backend.complete.assert_called_once()

    def test_rag_context_included_in_prompt(self):
        """RAG context must be passed through to the LLM prompt."""
        fake_response = {
            "executive_summary": "ok", "key_risks": [], "recommendation": "proceed",
            "confidence_level": "medium",
        }
        mock_backend = MagicMock()
        mock_backend.complete.return_value = json.dumps(fake_response)
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            generate_financial_narrative({}, rag_context="Kisumu revenue context")

        prompt_arg = mock_backend.complete.call_args[1].get("prompt") or mock_backend.complete.call_args[0][0]
        assert "Kisumu revenue context" in prompt_arg

    def test_no_rag_context_uses_fallback(self):
        """When rag_context is empty, prompt includes the no-context fallback text."""
        fake_response = {
            "executive_summary": "ok", "key_risks": [], "recommendation": "proceed",
            "confidence_level": "low",
        }
        mock_backend = MagicMock()
        mock_backend.complete.return_value = json.dumps(fake_response)
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            generate_financial_narrative({}, rag_context="")

        prompt_arg = mock_backend.complete.call_args[1].get("prompt") or mock_backend.complete.call_args[0][0]
        assert "No reference documents available" in prompt_arg


class TestCompareScenarios:
    def test_returns_comparison_narrative(self):
        fake_response = {
            "comparison_narrative": "Optimistic outperforms.",
            "key_drivers": ["occupancy"],
            "most_likely_scenario": "base",
            "scenario_ranking": ["optimistic", "base", "pessimistic"],
        }
        mock_backend = MagicMock()
        mock_backend.complete.return_value = json.dumps(fake_response)
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            result = compare_scenarios({"base": {"npv": 100}, "optimistic": {"npv": 400}})

        assert result["comparison_narrative"] == "Optimistic outperforms."
        assert result["most_likely_scenario"] == "base"

    def test_bad_json_falls_back_gracefully(self):
        """compare_scenarios should not raise on bad JSON — returns raw text."""
        mock_backend = MagicMock()
        mock_backend.complete.return_value = "Not valid JSON, sorry."
        with patch("mmfm.ai.narrator.get_backend", return_value=mock_backend):
            result = compare_scenarios({"base": {}})

        assert "comparison_narrative" in result
        assert result["most_likely_scenario"] == "base"
