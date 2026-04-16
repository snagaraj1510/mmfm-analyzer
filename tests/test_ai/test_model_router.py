"""Tests for model routing logic."""

from __future__ import annotations

import pytest

from mmfm.ai.model_router import get_model_for_task, get_config_for_task, estimate_cost


class TestModelRouter:
    def test_haiku_tasks_route_to_haiku(self):
        model = get_model_for_task("schema_detection")
        assert "haiku" in model.lower()

    def test_sonnet_tasks_route_to_sonnet(self):
        model = get_model_for_task("financial_narrative")
        assert "sonnet" in model.lower()

    def test_opus_tasks_route_to_opus(self):
        model = get_model_for_task("full_report_synthesis")
        assert "opus" in model.lower()

    def test_unknown_task_defaults_to_sonnet(self):
        model = get_model_for_task("some_unknown_task")  # type: ignore
        assert "sonnet" in model.lower()

    def test_config_has_required_keys(self):
        config = get_config_for_task("financial_narrative")
        assert "model" in config
        assert "max_tokens" in config
        assert "temperature" in config

    def test_haiku_temperature_is_zero(self):
        config = get_config_for_task("schema_detection")
        assert config["temperature"] == 0.0

    def test_cost_estimate_is_positive(self):
        cost = estimate_cost("claude-sonnet-4-20250514", input_tokens=1000, output_tokens=500)
        assert cost > 0

    def test_haiku_cheaper_than_opus(self):
        haiku_cost = estimate_cost("claude-haiku-4-5-20251001", 1000, 500)
        opus_cost = estimate_cost("claude-opus-4-20250514", 1000, 500)
        assert haiku_cost < opus_cost
