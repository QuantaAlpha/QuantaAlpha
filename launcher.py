#!/usr/bin/env python3
"""
QuantaAlpha unified launcher.

Usage:
    python launcher.py mine --direction "price-volume factor mining"
    python launcher.py mine --direction "momentum reversal" --config configs/experiment.yaml
    python launcher.py backtest --factor-source alpha158_20
    python launcher.py health_check
"""

import sys
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    print("=" * 60)
    print("Error: .env file not found")
    print()
    print("Please create config file:")
    print(f"  cp configs/.env.example .env")
    print("  Then edit .env with your data path and API Key")
    print("=" * 60)
    sys.exit(1)

# Apply Windows compatibility patches to rdagent (no-op on Linux)
from quantaalpha.compat.rdagent_patches import apply as _apply_rdagent_patches
_apply_rdagent_patches()

from quantaalpha.cli import app

if __name__ == "__main__":
    app()
