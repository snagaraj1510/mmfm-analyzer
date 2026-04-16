"""
Tests for the LLM backend abstraction.

OllamaBackend and ClaudeBackend are tested with mocks — no live servers required.
get_backend() selection logic is tested via environment variable overrides.
"""

from __future__ import annotations

import json
import os
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from mmfm.ai.backends import ClaudeBackend, LLMBackend, OllamaBackend, get_backend


# ────────────────────────────────────────────────────────────────────────────
# OllamaBackend
# ────────────────────────────────────────────────────────────────────────────

class TestOllamaBackend:
    def _make_response(self, content: str) -> BytesIO:
        payload = {"message": {"role": "assistant", "content": content}}
        return BytesIO(json.dumps(payload).encode("utf-8"))

    def test_complete_returns_text(self):
        backend = OllamaBackend(base_url="http://localhost:11434", model="llama3.2")
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(
            {"message": {"role": "assistant", "content": "Hello from Ollama"}}
        ).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = backend.complete("Say hello", system="Be brief.")
        assert result == "Hello from Ollama"

    def test_includes_system_message(self):
        """System message should appear in the messages list."""
        backend = OllamaBackend()
        captured_payload: dict = {}

        def fake_urlopen(req, timeout=None):
            import json as _json
            captured_payload.update(_json.loads(req.data.decode("utf-8")))
            mock = MagicMock()
            mock.__enter__ = lambda s: s
            mock.__exit__ = MagicMock(return_value=False)
            mock.read.return_value = _json.dumps(
                {"message": {"content": "ok"}}
            ).encode("utf-8")
            return mock

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            backend.complete("user prompt", system="be concise")

        roles = [m["role"] for m in captured_payload["messages"]]
        assert roles[0] == "system"
        assert roles[-1] == "user"

    def test_connection_error_raises_runtime_error(self):
        import urllib.error
        backend = OllamaBackend(base_url="http://localhost:11434")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            with pytest.raises(RuntimeError, match="Cannot reach Ollama"):
                backend.complete("test")

    def test_bad_response_format_raises(self):
        backend = OllamaBackend()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = b'{"unexpected": "keys"}'

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="Unexpected response format"):
                backend.complete("test")

    def test_satisfies_protocol(self):
        backend = OllamaBackend()
        assert isinstance(backend, LLMBackend)


# ────────────────────────────────────────────────────────────────────────────
# ClaudeBackend
# ────────────────────────────────────────────────────────────────────────────

class TestClaudeBackend:
    def test_complete_returns_text(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Claude says hello")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            backend = ClaudeBackend(api_key="sk-test", model_id="claude-haiku-4-5-20251001")
            result = backend.complete("Hello", max_tokens=512, temperature=0.0)

        assert result == "Claude says hello"

    def test_system_message_passed_as_kwarg(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="response")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            backend = ClaudeBackend(api_key="sk-test")
            backend.complete("prompt", system="You are an analyst.")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs.get("system") == "You are an analyst."

    def test_no_system_message_omits_kwarg(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            backend = ClaudeBackend(api_key="sk-test")
            backend.complete("prompt")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" not in call_kwargs

    def test_missing_anthropic_package_raises(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            backend = ClaudeBackend(api_key="sk-test")
            with pytest.raises(ImportError, match="anthropic"):
                backend.complete("hello")

    def test_satisfies_protocol(self):
        backend = ClaudeBackend(api_key="sk-test")
        assert isinstance(backend, LLMBackend)


# ────────────────────────────────────────────────────────────────────────────
# get_backend() selection logic
# ────────────────────────────────────────────────────────────────────────────

class TestGetBackend:
    def test_default_is_ollama(self, monkeypatch):
        monkeypatch.delenv("MMFM_LLM_BACKEND", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        # Patch get_settings to return default (ollama)
        from mmfm.config import Settings
        with patch("mmfm.config.get_settings", return_value=Settings()):
            backend = get_backend()
        assert isinstance(backend, OllamaBackend)

    def test_env_var_selects_ollama(self, monkeypatch):
        monkeypatch.setenv("MMFM_LLM_BACKEND", "ollama")
        from mmfm.config import Settings
        with patch("mmfm.config.get_settings", return_value=Settings(llm_backend="ollama")):
            backend = get_backend()
        assert isinstance(backend, OllamaBackend)

    def test_env_var_selects_claude(self, monkeypatch):
        monkeypatch.setenv("MMFM_LLM_BACKEND", "claude")
        from mmfm.config import Settings, AnthropicConfig
        settings = Settings(
            llm_backend="claude",
            anthropic=AnthropicConfig(api_key="sk-test-key"),
        )
        with patch("mmfm.config.get_settings", return_value=settings):
            backend = get_backend()
        assert isinstance(backend, ClaudeBackend)
        assert backend.api_key == "sk-test-key"

    def test_claude_without_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("MMFM_LLM_BACKEND", "claude")
        from mmfm.config import Settings, AnthropicConfig
        settings = Settings(llm_backend="claude", anthropic=AnthropicConfig(api_key=None))
        with patch("mmfm.config.get_settings", return_value=settings):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                get_backend()

    def test_ollama_uses_config_url_and_model(self, monkeypatch):
        monkeypatch.delenv("MMFM_LLM_BACKEND", raising=False)
        from mmfm.config import Settings, OllamaConfig
        settings = Settings(
            llm_backend="ollama",
            ollama=OllamaConfig(base_url="http://192.168.1.5:11434", model="mistral"),
        )
        with patch("mmfm.config.get_settings", return_value=settings):
            backend = get_backend()
        assert isinstance(backend, OllamaBackend)
        assert backend.base_url == "http://192.168.1.5:11434"
        assert backend.model == "mistral"

    def test_task_passed_to_claude_model_resolver(self, monkeypatch):
        """When backend=claude, task determines the model tier."""
        from mmfm.config import Settings, AnthropicConfig
        settings = Settings(
            llm_backend="claude",
            anthropic=AnthropicConfig(api_key="sk-key"),
        )
        with patch("mmfm.config.get_settings", return_value=settings):
            backend = get_backend(task="full_report_synthesis")
        assert isinstance(backend, ClaudeBackend)
        # full_report_synthesis → opus tier
        assert "opus" in backend.model_id
