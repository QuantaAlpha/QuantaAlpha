# Project Structure

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
