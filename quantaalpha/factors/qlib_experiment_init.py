"""
Compatibility layer: quantaalpha.factors.qlib_experiment_init.
Load factor/model experiment classes from QuantaAlpha first, fallback to rdagent.
"""

from importlib import import_module
from pathlib import Path
import sys

try:
    current_file = Path(__file__).resolve()
    repo_root = current_file.parents[5]
    rd_agent_root = repo_root / "RD-Agent"
    if rd_agent_root.exists():
        rd_agent_root_str = str(rd_agent_root)
        if rd_agent_root_str not in sys.path:
            sys.path.insert(0, rd_agent_root_str)
except Exception:
    pass

def _lazy_import(module_name: str):
    """Try quantaalpha.scenarios.qlib.experiment.<name>, then rdagent.scenarios.qlib.experiment.<name>."""
    base_paths = [
        "quantaalpha.scenarios.qlib.experiment",
        "rdagent.scenarios.qlib.experiment",
    ]
    last_exc = None
    for base in base_paths:
        try:
            return import_module(f"{base}.{module_name}")
        except ModuleNotFoundError as e:
            last_exc = e
            continue
    raise last_exc


factor_experiment = _lazy_import("factor_experiment")
model_experiment = _lazy_import("model_experiment")
factor_from_report_experiment = _lazy_import("factor_from_report_experiment")
workspace = _lazy_import("workspace")


