"""
Configuration management for MMFM Analyzer.

API keys and secrets are read exclusively from environment variables.
Never hardcode credentials here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file if present (local development only; never commit .env)
load_dotenv()

# Project root (two levels up from this file: src/mmfm/config.py -> root)
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"
SCHEMAS_DIR = RESOURCES_DIR / "schemas"

# User config file location (outside project, never in repo)
USER_CONFIG_DIR = Path.home() / ".mmfm"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"


class AnthropicConfig(BaseModel):
    api_key: Optional[str] = Field(default=None, description="Read from ANTHROPIC_API_KEY env var")
    cost_confirmation_threshold: float = 0.10
    max_daily_spend: float = 5.00


class OllamaConfig(BaseModel):
    """Local Ollama server config (free, default backend)."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2"  # override via config or MMFM_OLLAMA_MODEL env var


class DefaultsConfig(BaseModel):
    currency: str = "USD"
    horizon_years: int = 20
    discount_rate: float = 0.10
    inflation_rate: float = 0.05
    monte_carlo_iterations: int = 10000
    scenario: str = "base"


class OutputConfig(BaseModel):
    format: str = "terminal"
    verbosity: str = "normal"
    include_provenance: bool = True
    include_confidence: bool = True


class ValidationConfig(BaseModel):
    strict_mode: bool = True
    cross_validate_ai: bool = True
    audit_logging: bool = True


class MarketConfig(BaseModel):
    """Market-specific constants derived from MAP source documents."""
    # FX rates (April 2026 reference rates from source data)
    fx_rate_kes_usd: float = 129.3           # KES per 1 USD
    fx_rate_tzs_usd: float = 2650.0          # TZS per 1 USD (approx)
    fx_rate_mzn_usd: float = 63.8            # MZN per 1 USD (approx)

    # Infrastructure CAPEX benchmarks (USD)
    solar_pv_capex_per_kw_usd: float = 1070.0        # USD/kW installed
    cold_storage_capex_per_m3_usd: float = 1527.78   # USD/m³

    # Operating cost benchmarks
    cold_storage_fee_usd_per_kg_per_day: float = 0.013  # USD/kg/day

    # Lead times (months) — from procurement data
    lead_time_roofing_months: int = 12       # Outlier: 12 months vs 3-6 for all others
    lead_time_standard_months_min: int = 3
    lead_time_standard_months_max: int = 6

    # Fee collection benchmarks (from Lusaka data)
    fee_collection_rate_lusaka_avg: float = 0.38      # Lusaka system average
    fee_collection_rate_worst_case: float = 0.10      # Mandevu worst case
    fee_collection_rate_best_case: float = 1.0

    # Willingness-to-pay (from Kisumu field data)
    incremental_wtp_usd_per_stall_per_month: float = 5.0   # Typical
    stall_monthly_rent_typical_usd: float = 32.5            # Midpoint of Kisumu 30-35


class Settings(BaseModel):
    # LLM backend: "ollama" (free, default) or "claude" (requires ANTHROPIC_API_KEY)
    # Override via MMFM_LLM_BACKEND env var or this config field
    llm_backend: str = "ollama"
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)


def _load_user_config() -> dict:
    """Load config from ~/.mmfm/config.yaml if it exists."""
    if USER_CONFIG_FILE.exists():
        with open(USER_CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def _resolve_env_vars(config: dict) -> dict:
    """Replace ${VAR_NAME} placeholders with environment variable values."""
    import re
    def resolve_value(val):
        if isinstance(val, str):
            return re.sub(
                r"\$\{(\w+)\}",
                lambda m: os.environ.get(m.group(1), m.group(0)),
                val,
            )
        if isinstance(val, dict):
            return {k: resolve_value(v) for k, v in val.items()}
        return val
    return resolve_value(config)


def get_settings() -> Settings:
    """Return the resolved application settings."""
    raw = _load_user_config()
    raw = _resolve_env_vars(raw)

    settings = Settings.model_validate(raw) if raw else Settings()

    # API key: env var always wins over config file
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        settings.anthropic.api_key = env_key

    # LLM backend: env var wins
    backend_env = os.environ.get("MMFM_LLM_BACKEND")
    if backend_env:
        settings.llm_backend = backend_env.lower()

    # Ollama model: env var wins
    ollama_model_env = os.environ.get("MMFM_OLLAMA_MODEL")
    if ollama_model_env:
        settings.ollama.model = ollama_model_env

    return settings


def save_setting(key: str, value: str) -> None:
    """
    Persist a single key=value into ~/.mmfm/config.yaml.

    The API key is stored in the user's home dir config, never in the project.
    """
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if USER_CONFIG_FILE.exists():
        with open(USER_CONFIG_FILE) as f:
            existing = yaml.safe_load(f) or {}

    # Support dot-notation keys like "anthropic.api_key"
    parts = key.split(".")
    node = existing
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value

    with open(USER_CONFIG_FILE, "w") as f:
        yaml.dump(existing, f, default_flow_style=False)
