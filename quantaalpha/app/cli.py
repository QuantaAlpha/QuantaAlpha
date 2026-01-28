"""
CLI entrance for all quantaalpha application.

This will 
- make quantaalpha a nice entry and
- autoamtically load dotenv
"""

from pathlib import Path
from dotenv import load_dotenv

# Prefer QuantaAlpha root .env, fallback to current working directory .env
_quantaalpha_root = Path(__file__).resolve().parents[3]
_env_path = _quantaalpha_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv(".env")
# 1) Make sure it is at the beginning of the script so that it will load dotenv before initializing BaseSettings.
# 2) The ".env" argument is necessary to make sure it loads `.env` from the current directory.

import subprocess
from importlib.resources import path as rpath

import fire
from quantaalpha.app.qlib_rd_loop.factor_mining import main as mine
from quantaalpha.app.qlib_rd_loop.factor_backtest import main as backtest
from quantaalpha.app.utils.health_check import health_check
from quantaalpha.app.utils.info import collect_info


def ui(port=19899, log_dir="./log", debug=False):
    """
    start web app to show the log traces.
    """
    with rpath("quantaalpha.log.ui", "app.py") as app_path:
        cmds = ["streamlit", "run", app_path, f"--server.port={port}"]
        if log_dir or debug:
            cmds.append("--")
        if log_dir:
            cmds.append(f"--log_dir={log_dir}")
        if debug:
            cmds.append("--debug")
        subprocess.run(cmds)


def app():
    fire.Fire(
        {
            "mine": mine,
            "backtest": backtest,
            "ui": ui,
            "health_check": health_check,
            "collect_info": collect_info,
        }
    )
