"""
Backtest V2 - 全功能回测工具

支持:
- Qlib 官方因子库 (alpha158, alpha158(20), alpha360)
- 自定义因子库 (JSON格式)
- LLM 驱动的因子表达式计算
"""

from .factor_loader import FactorLoader
from .factor_calculator import FactorCalculator
from .backtest_runner import BacktestRunner

__version__ = "2.0.0"
__all__ = ["FactorLoader", "FactorCalculator", "BacktestRunner"]

