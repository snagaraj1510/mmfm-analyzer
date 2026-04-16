"""
LLM backend abstraction.

Supports two backends selectable at runtime — no restart required:

  OllamaBackend (default, free)
    Calls a local Ollama server.
    Setup: https://ollama.com  →  ollama pull llama3.2
    Config: MMFM_LLM_BACKEND=ollama  (or omit — this is the default)
            MMFM_OLLAMA_MODEL=llama3.2   (or any model you've pulled)

  ClaudeBackend (optional, paid)
    Calls the Anthropic API.
    Config: MMFM_LLM_BACKEND=claude
            ANTHROPIC_API_KEY=<key>

Backend selection priority:
  1. MMFM_LLM_BACKEND environment variable
  2. llm_backend field in ~/.mmfm/config.yaml
  3. Default: "ollama"
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMBackend(Protocol):
    """Minimal interface every backend must implement."""

    def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        """Return the model's text response to *prompt*."""
        ...


class OllamaBackend:
    """
    Calls a locally running Ollama server.

    No API key required — completely free.
    Model must be pulled first: ``ollama pull llama3.2``
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return result["message"]["content"]
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}.\n"
                "Is Ollama running? Start it with: ollama serve\n"
                f"If Ollama is not installed: https://ollama.com\n"
                f"Then pull a model: ollama pull {self.model}\n"
                f"Underlying error: {exc}"
            ) from exc
        except KeyError:
            raise RuntimeError(
                f"Unexpected response format from Ollama. "
                f"Ensure you are running Ollama >= 0.1.25 and model '{self.model}' is available."
            )


class ClaudeBackend:
    """
    Calls the Anthropic Claude API.

    Requires ``anthropic`` package and a valid ANTHROPIC_API_KEY.
    model_id is set at construction time from the model router.
    """

    def __init__(self, api_key: str, model_id: str = "claude-sonnet-4-6") -> None:
        self.api_key = api_key
        self.model_id = model_id

    def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.1,
    ) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for the Claude backend. "
                "Install it: pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs: dict = {
            "model": self.model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        response = client.messages.create(**kwargs)
        return response.content[0].text


def is_ollama_reachable(base_url: str = "http://localhost:11434") -> bool:
    """
    Return True if an Ollama server is reachable at *base_url*.

    Uses a short timeout so the UI does not hang when running in a
    cloud environment (Streamlit Cloud, Docker, etc.) where localhost
    has no Ollama process.
    """
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_backend(task: str = "") -> LLMBackend:
    """
    Return the appropriate LLM backend for the current configuration.

    When backend=claude the model_id is resolved via the task router so
    simple tasks use Haiku and complex tasks use Opus (cost tiering).
    When backend=ollama the same local model handles all tasks.

    Args:
        task: Optional task type string (used for Claude model routing).

    Returns:
        A configured LLMBackend instance ready for use.
    """
    # Import here to avoid circular imports at module level
    from mmfm.config import get_settings

    settings = get_settings()
    backend_name = settings.llm_backend.lower()

    if backend_name == "claude":
        api_key = settings.anthropic.api_key
        if not api_key:
            raise ValueError(
                "llm_backend is set to 'claude' but ANTHROPIC_API_KEY is not configured.\n"
                "Options:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-...\n"
                "  mmfm config set --key anthropic.api_key --value sk-ant-...\n"
                "Or switch to the free backend: export MMFM_LLM_BACKEND=ollama"
            )
        # Use task-based model routing when using Claude
        model_id = _resolve_claude_model(task)
        return ClaudeBackend(api_key=api_key, model_id=model_id)

    # Default: Ollama — but fall back to Claude if Ollama is unreachable
    # and an API key is available (e.g. running on Streamlit Cloud).
    ollama_url = settings.ollama.base_url
    if not is_ollama_reachable(ollama_url):
        api_key = settings.anthropic.api_key
        if api_key:
            model_id = _resolve_claude_model(task)
            return ClaudeBackend(api_key=api_key, model_id=model_id)
        raise RuntimeError(
            f"Cannot reach Ollama at {ollama_url}.\n"
            "If running locally: start Ollama with `ollama serve` then `ollama pull llama3.2`.\n"
            "If running on a hosted/cloud deployment: Ollama is not available — "
            "set ANTHROPIC_API_KEY to use the Claude backend instead."
        )
    return OllamaBackend(
        base_url=ollama_url,
        model=settings.ollama.model,
    )


def _resolve_claude_model(task: str) -> str:
    """Return the Claude model ID for a given task (Haiku/Sonnet/Opus tiering)."""
    if not task:
        return "claude-sonnet-4-6"
    try:
        from mmfm.ai.model_router import get_model_for_task
        return get_model_for_task(task)  # type: ignore[arg-type]
    except Exception:
        return "claude-sonnet-4-6"
