"""
兼容层：quantaalpha.factors.qlib_experiment_init

QuantaAlpha 基于 RD-Agent 的实验框架，提供因子/模型实验类。
优先从 QuantaAlpha 自己的模块加载，如果不存在则回退到 rdagent 版本。
"""

from importlib import import_module
from pathlib import Path
import sys

# 将本仓库中的 RD-Agent 根目录加入 sys.path，以便正常导入 `rdagent.*`
try:
    current_file = Path(__file__).resolve()
    # 仓库根目录: .../quantagent
    repo_root = current_file.parents[5]
    rd_agent_root = repo_root / "wuyinze" / "RD-Agent"
    if rd_agent_root.exists():
        rd_agent_root_str = str(rd_agent_root)
        if rd_agent_root_str not in sys.path:
            sys.path.insert(0, rd_agent_root_str)
except Exception:
    # 这里属于兼容增强逻辑，失败时不阻塞主流程，后续导入时会给出明确报错
    pass

# 优先从 QuantaAlpha 加载，不存在则降级到 RD-Agent 版本
def _lazy_import(module_name: str):
    """
    延迟导入工具：
    1. 先尝试 quantaalpha.factors.<module_name>
    2. 如果失败，再尝试 rdagent.scenarios.qlib.experiment.<module_name>
    """
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


# 对外暴露与原路径兼容的子模块，实际逻辑在对应实现模块中
factor_experiment = _lazy_import("factor_experiment")
model_experiment = _lazy_import("model_experiment")
factor_from_report_experiment = _lazy_import("factor_from_report_experiment")
workspace = _lazy_import("workspace")


