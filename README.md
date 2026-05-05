<div align="center">
  <img src="docs/images/overview.jpg" alt="QuantaAlpha Framework Overview" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 10px 0;"/>
</div>

<div align="center">

  <h1 align="center" style="color: #2196F3; font-size: 32px; font-weight: 700; margin: 20px 0; line-height: 1.4;">
    🌟 QuantaAlpha: <span style="color: #555; font-weight: 400; font-size: 20px;"><em>LLM-Driven Self-Evolving Framework for Factor Mining</em></span>
  </h1>

  <p align="center" style="font-size: 14px; color: #888; max-width: 700px; margin: 10px auto;">
    🧬 <em>Achieving superior quantitative alpha through trajectory-based self-evolution with diversified planning initialization, trajectory-level evolution, and structured hypothesis-code constraint</em>
  </p>

  <p style="margin: 20px 0;">
    <a href="https://arxiv.org/abs/2602.07085"><img src="https://img.shields.io/badge/arXiv-b31b1b.svg?style=flat-square&logo=arxiv&logoColor=white" /></a>
    <a href="#"><img src="https://img.shields.io/badge/License-MIT-00A98F.svg?style=flat-square&logo=opensourceinitiative&logoColor=white" /></a>
    <a href="#"><img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat-square&logo=python&logoColor=white" /></a>
    <a href="https://github.com/QuantaAlpha/QuantaAlpha"><img src="https://img.shields.io/github/stars/QuantaAlpha/QuantaAlpha?style=flat-square&logo=github&logoColor=white&color=yellow" /></a>
  </p>

</div>

<div align="center" style="margin: 30px 0;">
  <a href="#-quick-start" style="text-decoration: none; margin: 0 4px;">
    <img src="https://img.shields.io/badge/🚀_Quick_Start-Get_Started-4CAF50?style=flat-square&logo=rocket&logoColor=white&labelColor=2E7D32" alt="Quick Start" />
  </a>
  <a href="#️-web-dashboard" style="text-decoration: none; margin: 0 4px;">
    <img src="https://img.shields.io/badge/🖥️_Web_UI-Try_It_Now-FF9800?style=flat-square&logo=play&logoColor=white&labelColor=F57C00" alt="Web Dashboard" />
  </a>
  <a href="docs/user_guide.md" style="text-decoration: none; margin: 0 4px;">
    <img src="https://img.shields.io/badge/📖_User_Guide-Complete_Guide-2196F3?style=flat-square&logo=gitbook&logoColor=white&labelColor=1565C0" alt="User Guide" />
  </a>
</div>

---

## 🎯 Overview

**QuantaAlpha** transforms how you discover quantitative alpha factors by combining LLM intelligence with evolutionary strategies. Just describe your research direction, and watch as factors are automatically mined, evolved, and validated through self-evolving trajectories.

<p align="center">💬 Research Direction → 🧩 Diversified Planning → 🔄 Trajectory → ✅ Validated Alpha Factors</p>

---

## 📊 Performance

### 1. Factor Performance

<div align="center">
  <img src="docs/images/figure3.png" width="90%" alt="Zero-Shot Transfer" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
  <p style="font-size: 12px; color: #666;">CSI 300 factors transferred to CSI 500/S&P 500</p>
</div>

### 2. Key Results

<div align="center">

| Dimension | Metric | Performance |
| :---: | :---: | :---: |
| **Predictive Power** | Information Coefficient (IC) | **0.1501** |
| | Rank IC | **0.1465** |
| **Strategy Return** | Annualized Excess Return (ARR) | **27.75%** |
| | Max Drawdown (MDD) | **7.98%** |
| | Calmar Ratio (CR) | **3.4774** |

</div>

<div align="center">
  <img src="docs/images/主实验.png" width="90%" alt="Main Experiment Results" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);"/>
</div>

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/QuantaAlpha/QuantaAlpha.git
cd QuantaAlpha
conda create -n quantaalpha python=3.10
conda activate quantaalpha
# Install the package in development mode
SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pip install -e .

# Install additional dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

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

### 3. Prepare Data

QuantaAlpha requires two types of data: **Qlib market data** (for backtesting) and **pre-computed price-volume HDF5 files** (for factor mining). We provide all of them on HuggingFace for convenience.

> **Dataset**: [https://huggingface.co/datasets/QuantaAlpha/qlib_csi300](https://huggingface.co/datasets/QuantaAlpha/qlib_csi300)

| File | Description | Size | Usage |
| :--- | :--- | :--- | :--- |
| `cn_data.zip` | Qlib raw market data (A-share, 2016–2025) | 493 MB | Required for Qlib initialization & backtesting |
| `daily_pv.h5` | Pre-computed full price-volume data | 398 MB | Required for factor mining |
| `daily_pv_debug.h5` | Pre-computed debug subset (smaller) | 1.41 MB | Required for factor mining (debug/validation) |

> **Why provide HDF5 files?** The system can auto-generate `daily_pv.h5` from Qlib data on first run, but this process is very slow. Downloading pre-built HDF5 files saves significant time.

#### Step 1: Download

```bash
# Option A: Using huggingface-cli (recommended)
pip install huggingface_hub
huggingface-cli download QuantaAlpha/qlib_csi300 --repo-type dataset --local-dir ./hf_data

# Option B: Using wget
mkdir -p hf_data
wget -P hf_data https://huggingface.co/datasets/QuantaAlpha/qlib_csi300/resolve/main/cn_data.zip
wget -P hf_data https://huggingface.co/datasets/QuantaAlpha/qlib_csi300/resolve/main/daily_pv.h5
wget -P hf_data https://huggingface.co/datasets/QuantaAlpha/qlib_csi300/resolve/main/daily_pv_debug.h5
```

#### Step 2: Extract & Place Files

```bash
# 1. Extract Qlib data
unzip hf_data/cn_data.zip -d ./data/qlib

# 2. Place HDF5 files into the default data directories
mkdir -p git_ignore_folder/factor_implementation_source_data
mkdir -p git_ignore_folder/factor_implementation_source_data_debug

cp hf_data/daily_pv.h5       git_ignore_folder/factor_implementation_source_data/daily_pv.h5
cp hf_data/daily_pv_debug.h5  git_ignore_folder/factor_implementation_source_data_debug/daily_pv.h5
```

> **Note**: `daily_pv_debug.h5` must be renamed to `daily_pv.h5` when placed in the debug directory.

#### Step 3: Configure Paths in `.env`

```bash
# Point to the extracted Qlib data directory (must contain calendars/, features/, instruments/)
QLIB_DATA_DIR=./data/qlib/cn_data

# Output directory for experiment results
DATA_RESULTS_DIR=./data/results
```

The HDF5 data directories can also be customized via environment variables if you prefer a different location:

```bash
# Optional: override default HDF5 data paths
FACTOR_CoSTEER_DATA_FOLDER=/your/custom/path/factor_source_data
FACTOR_CoSTEER_DATA_FOLDER_DEBUG=/your/custom/path/factor_source_data_debug
```

### 4. Run Factor Mining

```bash
./run.sh "<your input>"

# Example: Run with a research direction
./run.sh "Price-Volume Factor Mining"

# Example: Run with custom factor library suffix
./run.sh "Microstructure Factors" "exp_micro"
```

The experiment will automatically mine, evolve, and validate alpha factors, and save all discovered factors to `all_factors_library*.json`.

### 5. Independent Backtesting

After mining, combine factors from the library for a full-period backtest:

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

> 📘 Need help? Check our comprehensive **[User Guide](docs/user_guide.md)** for advanced configuration, experiment reproduction, and detailed usage examples.

---

## 🖥️ Web UI

QuantaAlpha provides a web-based dashboard where you can complete the entire workflow through a visual interface — no command line needed.

```bash
conda activate quantaalpha
cd frontend-v2
bash start.sh
# Visit http://localhost:3000
```

- **⚙️ Settings**: Configure LLM API, data paths, and experiment parameters directly in the UI
- **⛏️ Factor Mining**: Start experiments with natural language input and monitor progress in real-time
- **📚 Factor Library**: Browse, search, and filter all discovered factors with quality classifications
- **📈 Independent Backtest**: Select a factor library and run full-period backtests with visual results

---

## 🤝 Contributing

We welcome all forms of contributions to make QuantaAlpha better! Here's how you can get involved:

- **🐛 Bug Reports**: Found a bug? [Open an issue](https://github.com/QuantaAlpha/QuantaAlpha/issues) to help us fix it.
- **💡 Feature Requests**: Have a great idea? [Start a discussion](https://github.com/QuantaAlpha/QuantaAlpha/discussions) to suggest new features.
- **📝 Docs & Tutorials**: Improve documentation, add usage examples, or write tutorials.
- **🔧 Code Contributions**: Submit PRs for bug fixes, performance improvements, or new functionality.
- **🧬 New Factors**: Share high-quality factors discovered in your own runs to benefit the community.

---
