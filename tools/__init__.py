"""
QuantaAlpha 工具集

该目录包含各种用于因子分析、数据处理的工具。

工具列表：
- extract_factor_ast: 因子AST提取工具，用于解析因子表达式并保存AST结构
- extract_factor_cache_from_workspace: 从工作空间提取因子缓存
- factor_cache_extractor: 因子缓存提取器
- plot_round_backtest_results: 绘制回测结果
- download_sp500_data: 下载SP500数据
"""

# 导出常用的AST提取工具
from .extract_factor_ast import (
    # 核心函数
    extract_ast_for_factor,
    process_factor_library,
    extract_ast_only,
    
    # AST序列化/反序列化
    serialize_ast,
    deserialize_ast,
    
    # AST分析函数
    collect_functions,
    collect_variables,
    compute_tree_depth,
    get_node_name,
)

__all__ = [
    'extract_ast_for_factor',
    'process_factor_library', 
    'extract_ast_only',
    'serialize_ast',
    'deserialize_ast',
    'collect_functions',
    'collect_variables',
    'compute_tree_depth',
    'get_node_name',
]

