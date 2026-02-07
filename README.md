<div align="center">

  <img src="images/overview.jpg" alt="QuantaAlpha Logo" width="100%"/>

  <h1 align="center" style="color: #2196F3; font-size: 32px; font-weight: 700; margin: 20px 0; line-height: 1.4;">
    🌟 QuantaAlpha: <span style="color: #555; font-weight: 400; font-size: 20px;"><em>LLM-Driven Experimental Framework for Factor Mining</em></span>
  </h1>

  <p align="center" style="font-size: 16px; color: #666; margin: 10px 0; font-weight: 500;">
    🚀 <em>Trajectory-Based Self-Evolution Paradigm: Plan - Evolve - Constrain</em>
  </p>

  <p style="margin: 20px 0;">
    <a href="#"><img src="https://img.shields.io/badge/License-MIT-00A98F.svg?style=flat-square&logo=opensourceinitiative&logoColor=white" /></a>
    <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" /></a>
    <a href="#"><img src="https://img.shields.io/badge/Platform-Linux-FCC624.svg?style=flat-square&logo=linux&logoColor=black" /></a>
  </p>

  <p style="font-size: 16px; color: #666; margin: 15px 0; font-weight: 500;">
    🌐 <a href="README.md" style="text-decoration: none; color: #0066cc;">English</a> | <a href="README_CN.md" style="text-decoration: none; color: #0066cc;">中文</a>
  </p>

</div>

---

## 🚀 Core Framework: Trajectory-Based Self-Evolution Paradigm

<div align="center">
  <h3>🎯 Plan · Evolve · Constrain - Empowering AI Survival in Real Financial Markets</h3>
  
  <p style="font-size: 16px; color: #666; max-width: 800px; margin: 0 auto; line-height: 1.6;">
    QuantaAlpha goes beyond single-shot mining success, pursuing <strong>Trajectory-Level Evolution</strong>. By simulating iterative research in real markets, it builds an Agentic Science experimental platform capable of logical self-consistency and environmental adaptation.
  </p>
</div>

<br/>

### ✨ Key Features

- **🧩 Diversified Planning Initialization**: Instead of relying on blind randomness, the initialization Agent uses a `planning` operator to generate significantly different research directions in parallel, avoiding local optima.
- **🧬 Trajectory Evolution**: 
    - **Mutation**: Precisely locates failure nodes and performs **targeted refinement** on local logic.
    - **Crossover**: Fuses superior genes across trajectories, creating new, robust logic (e.g., combining Institutional Capital Flow with Retail Sentiment).
- **🛡️ Structured Constraint**: Enforces a "Investment Hypothesis -- Language Description -- Code Implementation" trinity using AST verification, ensuring evolved codes are **interpretable economic hypotheses**.

---

## 📊 Empirical Performance

### 1. Peak Performance Metrics

| Dimension | Metric | Performance |
| :--- | :--- | :--- |
| **Predictive Power** | Information Coefficient (IC) | **0.1501** |
| | Rank IC | **0.1465** |
| **Strategy Return** | Annualized Excess Return (ARR) | **27.75%** |
| | Max Drawdown (MDD) | **7.98%** |
| | Calmar Ratio (CR) | **3.4774** |

<div align="center">
  <img src="images/主实验.png" width="90%" alt="Main Experiment Results" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
</div>

### 2. Zero-Shot Transferability & 3. Resilience

<div align="center" style="display: flex; justify-content: center; gap: 20px;">
  <div style="flex: 1; text-align: center;">
    <p><strong>Zero-Shot Transfer</strong></p>
    <img src="images/figure3.png" width="95%" alt="Zero-Shot Transfer" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
    <p style="font-size: 12px; color: #666;">CSI 300 factors transferred to CSI 500/S&P 500</p>
  </div>
  <div style="flex: 1; text-align: center;">
    <p><strong>Resilience Test</strong></p>
    <img src="images/figure4.png" width="95%" alt="Resilience Test" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
  </div>
</div>

<br/>

## System Requirements

| Requirement | Specification |
| :--- | :--- |
| **Operating System** | Linux (Ubuntu 20.04+ recommended). Windows / macOS support planned for future releases |
| **Python** | 3.10+ (Conda recommended) |
| **RAM** | 32 GB+ (LightGBM training + factor computation) |
| **Disk** | ~50 GB for Qlib data, ~100 GB recommended for experiment cache |
| **LLM API** | Any OpenAI-compatible API (DashScope, OpenAI, etc.) |

---

## Project Structure

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
│   ├── backtest/                #   Independent backtest module (V2)
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

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/QuantaAlpha/QuantaAlpha.git
cd QuantaAlpha
```

### 2. Create Python Environment

```bash
conda create -n quantaalpha python=3.10
conda activate quantaalpha
```

### 3. Install Dependencies

```bash
# Install in development mode (automatically installs all dependencies from requirements.txt)
SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pip install -e .
```

> **Note**: `pip install -e .` reads `pyproject.toml`, which declares `dependencies = {file = ["requirements.txt"]}`, so all dependencies are installed automatically -- no need to run `pip install -r requirements.txt` separately. The `SETUPTOOLS_SCM_PRETEND_VERSION` environment variable provides a version number when no git tag is available.

### 4. Configure Environment Variables

```bash
cp configs/.env.example .env
```

Edit `.env` with your settings:

```bash
# === Required: Data Paths ===
QLIB_DATA_DIR=/path/to/your/qlib/cn_data      # Qlib data directory
DATA_RESULTS_DIR=/path/to/your/results         # Output directory

# === Required: LLM API ===
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-llm-provider/v1   # e.g. DashScope, OpenAI
CHAT_MODEL=deepseek-v3                         # or gpt-4, qwen-max, etc.
REASONING_MODEL=deepseek-v3
```

### 5. Prepare Qlib Data

QuantaAlpha uses Microsoft's [Qlib](https://github.com/microsoft/qlib) for financial data. You need A-share market data covering **2016-2025**:

```bash
# Option A: Use qlib's built-in data download
python -c "
import qlib
from qlib.contrib.data.handler import Alpha158
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region='cn')
"

# Option B: If you already have Qlib data, point QLIB_DATA_DIR to it
# The directory should contain: calendars/, features/, instruments/ subdirectories
```

### 6. Run Your First Experiment

```bash
./run.sh "Price-Volume Factor Mining"
```

The experiment will automatically:
1. Generate diverse research directions via LLM
2. Propose factor hypotheses for each direction
3. Generate and validate factor expressions
4. Run backtests on the validation set (2021)
5. Evolve factors through mutation and crossover
6. Save all discovered factors to `all_factors_library*.json`

---

## Main Experiment: Factor Mining

### Basic Usage

```bash
# Run with a research direction
./run.sh "Momentum and Reversal Factor Mining"

# Run with custom factor library suffix
./run.sh "Microstructure Factors" "exp_micro"
```

### Key Configuration (configs/experiment.yaml)

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

- **Factor Library**: `all_factors_library*.json` -- all discovered factors with backtest metrics
- **Logs**: `log/` directory with detailed execution traces
- **Cache**: Controlled by `DATA_RESULTS_DIR` in `.env`

---

## Independent Backtesting

After mining, combine factors from the library for a full-period backtest on the **test set (2022-2025)**:

```bash
# Backtest with custom factors only
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source custom \
  --factor-json all_factors_library.json

# Combine with Alpha158(20) baseline factors
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source combined \
  --factor-json all_factors_library.json

# Dry run (load factors only, skip backtest)
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source custom \
  --factor-json all_factors_library.json \
  --dry-run -v
```

Results are saved to the directory specified in `configs/backtest.yaml` (`experiment.output_dir`).

---

## Web Dashboard

QuantaAlpha includes a web-based dashboard for experiment monitoring, factor library browsing, and independent backtesting.

### One-Click Start

```bash
conda activate quantaalpha
cd frontend-v2
bash start.sh
```

This will start both the FastAPI backend (port 8000) and Vite frontend dev server (port 3000).

### Manual Start

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

### Features

- **Factor Mining**: Start experiments with natural language, monitor progress in real-time via WebSocket
- **Factor Library**: Browse, search, and filter all discovered factors with quality classifications
- **Independent Backtest**: Select a factor library JSON and run full-period backtests from the UI
- **Settings**: Configure LLM API, data paths, and experiment parameters

---

## Quality Gates

Configure in `configs/experiment.yaml`:

```yaml
quality_gate:
  consistency_enabled: false     # LLM verifies hypothesis-description-formula-expression alignment
  complexity_enabled: true       # Limits expression length and over-parameterization
  redundancy_enabled: true       # Prevents high correlation with existing factors
  consistency_strict_mode: false # Strict mode rejects inconsistent factors
  max_correction_attempts: 3    # Max LLM correction retries
```

---

## FAQ

| Problem | Solution |
| :--- | :--- |
| **Qlib data not found** | Ensure `QLIB_DATA_DIR` in `.env` points to a valid Qlib data directory containing `calendars/`, `features/`, `instruments/` |
| **LLM API errors** | Check `OPENAI_API_KEY` and `OPENAI_BASE_URL` in `.env`. QuantaAlpha supports any OpenAI-compatible API |
| **Factor parsing error** | Check if the expression functions are within the parser's supported range. See `quantaalpha/factors/coder/function_lib.py` |
| **Cache read failure** | Ensure `DATA_RESULTS_DIR` exists and is writable |
| **Empty backtest results** | Make sure Qlib data covers the configured time periods (train: 2016-2020, valid: 2021) |
| **`setuptools-scm` version error** | Use `SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pip install -e .` |
| **Backend only supports Linux** | Windows and macOS support is planned for future releases. Use WSL2 on Windows as a workaround |
| **Frontend cannot connect to backend** | Ensure the backend is running on port 8000 and the Vite proxy is configured correctly |
