# 📘 QuantaAlpha User Guide

This comprehensive guide covers everything beyond the basics — from project architecture to advanced experiment tuning. For installation, environment setup, and first-run instructions, please refer to the main [README](../README.md).

---

## 📋 Table of Contents

- [🏗️ Project Structure](#️-project-structure)
- [🖥️ Web Dashboard](#️-web-dashboard)
- [🔬 Experiment Configuration & Reproduction](#-experiment-configuration--reproduction)
- [⏱️ Resource Estimation](#️-resource-estimation)

---

## 🏗️ Project Structure

```
QuantaAlpha/
├── configs/                     # Centralized configuration
│   ├── .env.example             #   Environment template
│   ├── experiment.yaml          #   Main experiment parameters
│   └── backtest.yaml            #   Independent backtest parameters
├── quantaalpha/                 # Core Python package
│   ├── pipeline/                #   Main experiment workflow
│   │   ├── factor_mining.py     #     Entry point for factor mining
│   │   ├── loop.py              #     Main experiment loop
│   │   ├── planning.py          #     Diversified direction planning
│   │   └── evolution/           #     Mutation & crossover logic
│   ├── factors/                 #   Factor definition & evaluation
│   │   ├── coder/               #     Factor code generation & parsing
│   │   ├── runner.py            #     Factor backtest runner
│   │   ├── library.py           #     Factor library management
│   │   └── proposal.py          #     Hypothesis proposal
│   ├── backtest/                #   Independent backtest module
│   │   ├── run_backtest.py      #     Backtest entry point
│   │   ├── runner.py            #     Backtest runner (Qlib)
│   │   └── factor_loader.py     #     Factor loading & preprocessing
│   ├── llm/                     #   LLM API client & config
│   ├── core/                    #   Core abstractions & utilities
│   └── cli.py                   #   CLI entry point
├── frontend-v2/                 # Web dashboard (React + TypeScript)
│   ├── src/                     #   Frontend source code
│   ├── backend/                 #   FastAPI backend for frontend
│   └── start.sh                 #   One-click start script
├── run.sh                       # Main experiment launch script
├── pyproject.toml               # Package definition
└── requirements.txt             # Python dependencies
```

**Key directories at a glance:**

| Directory | Role |
| :--- | :--- |
| `configs/` | All YAML configs and `.env` template — the single source of truth for experiment parameters |
| `quantaalpha/pipeline/` | Orchestrates the full mining loop: planning → hypothesis → coding → backtest → evolution |
| `quantaalpha/factors/` | Factor lifecycle — from code generation and AST parsing to library storage |
| `quantaalpha/backtest/` | Standalone post-mining backtest on the out-of-sample test set |
| `quantaalpha/llm/` | Unified LLM client that wraps OpenAI-compatible APIs |
| `frontend-v2/` | React + FastAPI web dashboard for visual experiment control |

---

## 🖥️ Web UI

The README shows the one-click start (`bash start.sh`). Below are **manual start** instructions and a deeper look at each feature.

### Manual Start

Use this when you need to debug or run frontend/backend independently:

```bash
# Terminal 1: Start the backend
conda activate quantaalpha
cd frontend-v2
pip install fastapi uvicorn websockets python-multipart python-dotenv
python backend/app.py

# Terminal 2: Start the frontend
cd frontend-v2
npm install
npm run dev
```

Visit `http://localhost:3000` to access the dashboard.

### Dashboard Features

| Tab | What It Does |
| :--- | :--- |
| **⛏️ Factor Mining** | Start experiments with natural language input; progress, logs, and metrics stream in real-time via WebSocket |
| **📚 Factor Library** | Browse, search, and filter all discovered factors with quality classifications (High / Medium / Low) |
| **📈 Independent Backtest** | Select a factor library JSON, choose Custom or Combined mode, and run full-period backtests with visual results |
| **⚙️ Settings** | Configure LLM API keys, data paths, and experiment parameters directly from the UI |

---

## 🔬 Experiment Configuration & Reproduction

All experiment behavior is controlled by `configs/experiment.yaml`. Below is a reference configuration with annotations:

```yaml
planning:
  num_directions: 2          # Number of parallel exploration directions

execution:
  max_loops: 3               # Iterations per direction

evolution:
  max_rounds: 5              # Total evolution rounds
  mutation_enabled: true     # Enable mutation phase
  crossover_enabled: true    # Enable crossover phase

hypothesis:
  factors_per_hypothesis: 3  # Factors generated per hypothesis

quality_gate:
  consistency_enabled: false     # LLM verifies hypothesis-description-formula-expression alignment
  complexity_enabled: true       # Limits expression length and over-parameterization
  redundancy_enabled: true       # Prevents high correlation with existing factors
  consistency_strict_mode: false # Strict mode rejects inconsistent factors
  max_correction_attempts: 3    # Max LLM correction retries
```

### Time Periods

| Period | Range | Purpose |
| :--- | :--- | :--- |
| **Training Set** | 2016-01-01 ~ 2020-12-31 | Model training |
| **Validation Set** | 2021-01-01 ~ 2021-12-31 | Preliminary backtest during mining |
| **Test Set** | 2022-01-01 ~ 2025-12-26 | Independent backtest (out-of-sample) |

### Base Factors

During the main experiment, newly mined factors are combined with **4 base factors** for preliminary backtest evaluation on the validation set:

| Name | Expression | Description |
| :--- | :--- | :--- |
| OPEN_RET | `($close-$open)/$open` | Intraday open-to-close return |
| VOL_RATIO | `$volume/Mean($volume, 20)` | Volume ratio vs 20-day average |
| RANGE_RET | `($high-$low)/Ref($close, 1)` | Daily range relative to prior close |
| CLOSE_RET | `$close/Ref($close, 1)-1` | Daily close-to-close return |

### Output

| Artifact | Location | Description |
| :--- | :--- | :--- |
| Factor Library | `all_factors_library*.json` | All discovered factors with backtest metrics |
| Logs | `log/` | Detailed execution traces for each run |
| Cache | `DATA_RESULTS_DIR` (set in `.env`) | Intermediate data and backtest results |

---

## ⏱️ Resource Estimation

Token and time consumption scales approximately with `num_directions × max_rounds × factors_per_hypothesis`:

| Configuration | Approximate LLM Tokens | Approximate Time |
| :--- | :--- | :--- |
| 2 directions × 3 rounds × 3 factors | ~100K tokens | ~30–60 min |
| 3 directions × 5 rounds × 5 factors | ~500K tokens | ~2–4 hours |
| 5 directions × 10 rounds × 5 factors | ~2M tokens | ~8–16 hours |
