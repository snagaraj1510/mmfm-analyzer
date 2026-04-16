# MMFM Analyzer

**Municipal Market Financial Model Analyzer** — ICLEI Africa / MBA MAP Capstone

> A CLI + web dashboard for scenario analysis, sensitivity testing, Monte Carlo simulation, and AI-powered narrative generation on municipal market revitalization investments across East Africa.

Built as the analytical engine for a MAP capstone project with ICLEI Africa, evaluating investment readiness across market sites in Sub-Saharan Africa. Training data comes from Kenya, Tanzania, Malawi, Zambia, and Mozambique.

---

## Live Dashboard

```bash
streamlit run src/mmfm/app.py
```

Opens at `http://localhost:8501` — five tabs covering the full analysis pipeline.

---

## Demo Portfolio

Five MAP markets pre-loaded, grounded in ICLEI Africa source data.

```bash
mmfm compare          # Terminal table
mmfm compare --format json
```

---

## Features

- **Financial engine** — NPV, IRR, payback, DSCR, operating margins (deterministic Python, no AI)
- **Scenario analysis** — Base / optimistic / pessimistic with source-calibrated fee collection rates (Lusaka avg: 38%)
- **Sensitivity + tornado** — Sweep 7 variables, ranked by NPV impact
- **Monte Carlo** — 10K iterations, P10/P50/P90 distribution, probability of positive NPV
- **AI narrative** — Executive summaries via Ollama (free, local) or Claude API (optional)
- **Anti-hallucination validation** — Bounds checking, cross-validation against engine outputs, audit logging
- **Multi-market comparison** — Portfolio-level ranking across East Africa markets
- **Export** — PDF reports, Excel workbooks, JSON

---

## Setup

### 1. Install

```bash
git clone https://github.com/snagaraj1510/mmfm-analyzer
cd mmfm-analyzer
pip install -e ".[dev]"
```

### 2. Run the dashboard

```bash
streamlit run src/mmfm/app.py
```

### 3. Configure AI backend (optional)

**Ollama — free, runs locally (recommended for getting started):**
```bash
# Install from https://ollama.com
ollama pull llama3.2
ollama serve
# That's it — Ollama is the default backend
```

**Claude API — optional, higher quality:**
```bash
export ANTHROPIC_API_KEY=sk-ant-...
export MMFM_LLM_BACKEND=claude
```

---

## CLI Reference

```bash
# Analyze a market model
mmfm analyze --file resources/models/market.xlsx

# Compare the MAP demo portfolio
mmfm compare

# Run all scenarios
mmfm report --file market.xlsx --format terminal --scenarios

# Sensitivity tornado chart
mmfm sensitivity --file market.xlsx --tornado

# Monte Carlo simulation
mmfm simulate --file market.xlsx --iterations 10000

# Generate PDF report with AI narrative
mmfm report --file market.xlsx --format pdf --narrative --output report.pdf

# Ingest a PDF/DOCX into the knowledge base
mmfm ingest --file resources/reports/iclei_framework.pdf

# Validate model + export audit log
mmfm validate --file market.xlsx --audit

# Show current config
mmfm config show
```

---

## Architecture

```
mmfm-analyzer/
├── src/mmfm/
│   ├── app.py              # Streamlit dashboard
│   ├── cli.py              # Typer CLI (mmfm command)
│   ├── config.py           # Settings, env var resolution
│   ├── engine/             # Financial calculations (deterministic)
│   │   ├── core_metrics.py     # NPV, IRR, DSCR, payback
│   │   ├── projections.py      # Multi-year cash flow projection
│   │   ├── scenarios.py        # Base / optimistic / pessimistic
│   │   ├── sensitivity.py      # Tornado analysis
│   │   ├── monte_carlo.py      # Monte Carlo simulation
│   │   └── comparison.py       # Multi-market comparison
│   ├── ai/                 # AI narrative layer
│   │   ├── backends.py         # Ollama + Claude backend abstraction
│   │   ├── narrator.py         # Narrative generation
│   │   ├── model_router.py     # Haiku / Sonnet / Opus task routing
│   │   └── anomaly_detector.py # Flag suspicious numbers
│   ├── validation/         # Anti-hallucination framework
│   │   ├── bounds_checker.py   # Plausible range validation
│   │   ├── cross_validator.py  # AI output vs engine output
│   │   ├── audit_logger.py     # Full computation audit trail
│   │   └── provenance.py       # Source attribution
│   ├── ingestion/          # Data ingestion (Excel, PDF, DOCX, CSV)
│   ├── knowledge/          # ChromaDB vector store + RAG
│   ├── output/             # PDF, Excel, JSON, terminal
│   └── demo/               # Pre-loaded MAP market fixtures
├── tests/                  # 187 tests
└── resources/              # Drop zone for your market models
```

**Design principle:** Deterministic first, AI second. All financial calculations are pure Python. AI is used only for narrative and anomaly detection — never for computation. If the engine says NPV = X and the AI says Y, the engine wins.

---

## Test Suite

```bash
pytest                    # Run all 187 tests
pytest tests/test_engine  # Financial engine only
pytest tests/test_ai      # AI layer (mocked — no API key required)
pytest -k "hallucination" # Anti-hallucination tests
```

---

## Data Sources

All market-specific constants are derived from MAP source documents:
- ICLEI Africa Financial Model (Pemba Eduardo Mondlane data)
- ReMark Final Report
- Lusaka Municipal Markets Report (fee collection benchmarks)
- Lilongwe Markets Report (Tsoka/Lizulu MIRI scores)
- Kisumu Income Statement (Solar PV CAPEX stress-test data)

---

## About

Built by **Shreyas** — Michigan Ross MBA 2026, MAP capstone with ICLEI Africa.

This tool demonstrates production-grade financial modeling + AI tooling for the type of infrastructure investment analysis relevant to municipal governments and development finance institutions across sub-Saharan Africa.
