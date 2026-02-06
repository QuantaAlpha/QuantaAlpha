"""
Factor Regulator Module
因子正则化模块

This module provides:
- FactorRegulator: Factor duplication and complexity checking
- FactorConsistencyChecker: Semantic consistency checking between hypothesis, description, and expression
- FactorQualityGate: Integrated quality gate combining all checks

该模块提供：
- FactorRegulator: 因子重复性和复杂度检查
- FactorConsistencyChecker: 假设、描述、表达式之间的语义一致性检查
- FactorQualityGate: 整合所有检查的质量门控
"""

from quantaalpha.factors.regulator.factor_regulator import FactorRegulator

# 尝试导入一致性检验模块（可选依赖）
try:
    from quantaalpha.factors.regulator.consistency_checker import (
        FactorConsistencyChecker,
        ConsistencyCheckResult,
        ComplexityChecker,
        RedundancyChecker,
        FactorQualityGate
    )
    CONSISTENCY_CHECKER_AVAILABLE = True
except ImportError:
    CONSISTENCY_CHECKER_AVAILABLE = False
    FactorConsistencyChecker = None
    ConsistencyCheckResult = None
    ComplexityChecker = None
    RedundancyChecker = None
    FactorQualityGate = None


__all__ = [
    'FactorRegulator',
    'FactorConsistencyChecker',
    'ConsistencyCheckResult',
    'ComplexityChecker',
    'RedundancyChecker',
    'FactorQualityGate',
    'CONSISTENCY_CHECKER_AVAILABLE'
]
