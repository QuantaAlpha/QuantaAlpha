#!/usr/bin/env python3
"""
因子计算器 - 使用表达式解析器或 LLM 计算因子值

支持:
1. 直接使用表达式解析器计算
2. 使用 LLM 生成代码计算复杂因子
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class FactorCalculator:
    """因子计算器"""
    
    # 允许的操作符文档
    OPERATIONS_DOC = """
Only the following operations are allowed in expressions: 
### **Cross-sectional Functions**
- **RANK(A)**: Ranking of each element in the cross-sectional dimension of A.
- **ZSCORE(A)**: Z-score of each element in the cross-sectional dimension of A.
- **MEAN(A)**: Mean value of each element in the cross-sectional dimension of A.
- **STD(A)**: Standard deviation in the cross-sectional dimension of A.
- **MAX(A)**: Maximum value in the cross-sectional dimension of A.
- **MIN(A)**: Minimum value in the cross-sectional dimension of A.
- **MEDIAN(A)**: Median value in the cross-sectional dimension of A

### **Time-Series Functions**
- **DELTA(A, n)**: Change in value of A over n periods.
- **DELAY(A, n)**: Value of A delayed by n periods.
- **TS_MEAN(A, n)**: Mean value of sequence A over the past n days.
- **TS_SUM(A, n)**: Sum of sequence A over the past n days.
- **TS_RANK(A, n)**: Time-series rank of the last value of A in the past n days.
- **TS_ZSCORE(A, n)**: Z-score for each sequence in A over the past n days.
- **TS_MEDIAN(A, n)**: Median value of sequence A over the past n days.
- **TS_PCTCHANGE(A, p)**: Percentage change in the value of sequence A over p periods.
- **TS_MIN(A, n)**: Minimum value of A in the past n days.
- **TS_MAX(A, n)**: Maximum value of A in the past n days.
- **TS_ARGMAX(A, n)**: The index of the maximum value of A over the past n days.
- **TS_ARGMIN(A, n)**: The index of the minimum value of A over the past n days.
- **TS_QUANTILE(A, p, q)**: Rolling quantile of sequence A over the past p periods.
- **TS_STD(A, n)**: Standard deviation of sequence A over the past n days.
- **TS_VAR(A, p)**: Rolling variance of sequence A over the past p periods.
- **TS_CORR(A, B, n)**: Correlation coefficient between A and B over the past n days.
- **TS_COVARIANCE(A, B, n)**: Covariance between A and B over the past n days.
- **TS_MAD(A, n)**: Rolling Median Absolute Deviation of A over the past n days.

### **Moving Averages and Smoothing Functions**
- **SMA(A, n, m)**: Simple moving average of A over n periods with modifier m.
- **WMA(A, n)**: Weighted moving average of A over n periods.
- **EMA(A, n)**: Exponential moving average of A over n periods.
- **DECAYLINEAR(A, d)**: Linearly weighted moving average of A over d periods.

### **Mathematical Operations**
- **PROD(A, n)**: Product of values in A over the past n days.
- **LOG(A)**: Natural logarithm of each element in A.
- **SQRT(A)**: Square root of each element in A.
- **POW(A, n)**: Raise each element in A to the power of n.
- **SIGN(A)**: Sign of each element in A.
- **EXP(A)**: Exponential of each element in A.
- **ABS(A)**: Absolute value of A.
- **MAX(A, B)**: Maximum value between A and B.
- **MIN(A, B)**: Minimum value between A and B.
- **INV(A)**: Reciprocal of each element in A.
- **FLOOR(A)**: Floor of each element in A.

### **Conditional and Logical Functions**
- **COUNT(C, n)**: Count of samples satisfying condition C in the past n periods.
- **SUMIF(A, n, C)**: Sum of A over the past n periods if condition C is met.
- **FILTER(A, C)**: Filtering sequence A based on condition C.
- **(C1)&&(C2)**: Logical AND operation.
- **(C1)||(C2)**: Logical OR operation.
- **(C1)?(A):(B)**: Conditional expression.

### **Regression and Residual Functions**
- **SEQUENCE(n)**: A sequence from 1 to n.
- **REGBETA(A, B, n)**: Regression coefficient of A on B over the past n samples.
- **REGRESI(A, B, n)**: Residual of regression of A on B over the past n samples.

### **Technical Indicators**
- **RSI(A, n)**: Relative Strength Index of A over n periods.
- **MACD(A, short, long)**: Moving Average Convergence Divergence.
- **BB_MIDDLE(A, n)**: Middle Bollinger Band.
- **BB_UPPER(A, n)**: Upper Bollinger Band.
- **BB_LOWER(A, n)**: Lower Bollinger Band.
"""
    
    def __init__(self, config: Dict, data_df: Optional[pd.DataFrame] = None):
        """
        初始化因子计算器
        
        Args:
            config: 配置字典
            data_df: 股票数据 DataFrame（可选，如果不提供则从 qlib 获取）
        """
        self.config = config
        self.data_df = data_df
        self.llm_config = config.get('llm', {})
        self.calc_config = config.get('factor_calculation', {})
        
        # 缓存目录
        self.cache_dir = Path(self.llm_config.get('cache_dir', './factor_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 输出目录
        self.output_dir = Path(self.calc_config.get('output_dir', './computed_factors'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def set_data(self, data_df: pd.DataFrame):
        """设置股票数据"""
        self.data_df = data_df
        
    def calculate_factors(self, factors: List[Dict]) -> pd.DataFrame:
        """
        计算因子值
        
        Args:
            factors: 因子列表，每个因子包含:
                - factor_name: 因子名称
                - factor_expression: 因子表达式
                - factor_description: 因子描述（可选）
                - variables: 变量说明（可选）
        
        Returns:
            pd.DataFrame: 计算得到的因子值
        """
        if self.data_df is None:
            raise ValueError("数据未设置，请先调用 set_data() 或在初始化时提供 data_df")
        
        results = {}
        success_count = 0
        fail_count = 0
        
        for factor_info in factors:
            factor_name = factor_info.get('factor_name', 'unknown')
            factor_expr = factor_info.get('factor_expression', '')
            
            logger.info(f"  计算因子: {factor_name}")
            
            try:
                # 首先检查缓存
                if self.llm_config.get('cache_results', True):
                    cached_result = self._load_from_cache(factor_expr)
                    if cached_result is not None:
                        results[factor_name] = cached_result
                        success_count += 1
                        valid_count = cached_result.notna().sum()
                        total_count = len(cached_result)
                        logger.info(f"    ✓ 从缓存加载 (有效数据: {valid_count}/{total_count})")
                        continue
                
                # 缓存未命中，尝试直接使用表达式解析器
                factor_value = self._calculate_with_parser(factor_expr)
                
                if factor_value is not None:
                    results[factor_name] = factor_value
                    success_count += 1
                    valid_count = factor_value.notna().sum()
                    total_count = len(factor_value)
                    logger.info(f"    ✓ 成功 (有效数据: {valid_count}/{total_count})")
                    # 保存到缓存
                    if self.llm_config.get('cache_results', True):
                        self._save_to_cache(factor_expr, factor_value)
                else:
                    # 如果解析失败，使用 LLM
                    if self.llm_config.get('enabled', True):
                        factor_value = self._calculate_with_llm(factor_info)
                        if factor_value is not None:
                            results[factor_name] = factor_value
                            success_count += 1
                            logger.info(f"    ✓ LLM 计算成功")
                        else:
                            fail_count += 1
                            logger.warning(f"    ✗ 计算失败")
                    else:
                        fail_count += 1
                        logger.warning(f"    ✗ 表达式不兼容且 LLM 已禁用")
                        
            except Exception as e:
                fail_count += 1
                logger.error(f"    ✗ 计算错误: {str(e)}")
        
        logger.info(f"  因子计算完成: 成功 {success_count}, 失败 {fail_count}")
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def _calculate_with_parser(self, expr: str) -> Optional[pd.Series]:
        """
        使用表达式解析器计算因子
        
        Args:
            expr: 因子表达式
            
        Returns:
            Optional[pd.Series]: 因子值
        """
        try:
            # 导入表达式解析器
            from quantaalpha.components.coder.factor_coder.expr_parser import (
                parse_expression, parse_symbol
            )
            # 导入函数库
            import quantaalpha.components.coder.factor_coder.function_lib as func_lib
            
            # 准备数据
            df = self.data_df.copy()
            
            # 解析表达式
            parsed_expr = parse_symbol(expr, df.columns)
            parsed_expr = parse_expression(parsed_expr)
            
            # 替换变量
            for col in df.columns:
                if col.startswith('$'):
                    parsed_expr = parsed_expr.replace(col[1:], f"df['{col}']")
            
            # 构建执行环境
            exec_globals = {
                'df': df,
                'np': np,
                'pd': pd,
            }
            # 添加所有函数库中的函数
            for name in dir(func_lib):
                if not name.startswith('_'):
                    exec_globals[name] = getattr(func_lib, name)
            
            # 计算因子值
            result = eval(parsed_expr, exec_globals)
            
            if isinstance(result, pd.Series):
                return result
            elif isinstance(result, pd.DataFrame):
                return result.iloc[:, 0]
            else:
                return pd.Series(result, index=df.index)
                
        except Exception as e:
            logger.debug(f"表达式解析失败: {str(e)}")
            return None
    
    def _calculate_with_llm(self, factor_info: Dict) -> Optional[pd.Series]:
        """
        使用 LLM 生成代码计算因子
        
        Args:
            factor_info: 因子信息字典
            
        Returns:
            Optional[pd.Series]: 因子值
        """
        factor_name = factor_info.get('factor_name', 'unknown')
        factor_expr = factor_info.get('factor_expression', '')
        
        # 检查缓存
        if self.llm_config.get('cache_results', True):
            cached_result = self._load_from_cache(factor_expr)
            if cached_result is not None:
                logger.debug(f"    从缓存加载因子: {factor_name}")
                return cached_result
        
        try:
            # 生成代码
            code = self._generate_factor_code(factor_info)
            
            if code is None:
                return None
            
            # 执行代码
            result = self._execute_factor_code(code, factor_name)
            
            # 保存缓存
            if result is not None and self.llm_config.get('cache_results', True):
                self._save_to_cache(factor_expr, result)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM 计算失败: {str(e)}")
            return None
    
    def _generate_factor_code(self, factor_info: Dict) -> Optional[str]:
        """
        使用 LLM 生成因子计算代码
        
        Args:
            factor_info: 因子信息
            
        Returns:
            Optional[str]: 生成的 Python 代码
        """
        try:
            from quantaalpha.oai.llm_utils import APIBackend
        except ImportError:
            logger.error("无法导入 LLM 模块，请确保 quantaalpha 已正确安装")
            return None
        
        factor_name = factor_info.get('factor_name', 'unknown')
        factor_expr = factor_info.get('factor_expression', '')
        factor_desc = factor_info.get('factor_description', '')
        variables = factor_info.get('variables', {})
        
        # 构建提示
        system_prompt = f"""You are an expert quantitative analyst. Your task is to convert factor expressions into executable Python code.

The code should:
1. Use pandas DataFrame operations
2. Handle the datetime and instrument multi-index properly
3. Use the function library provided

{self.OPERATIONS_DOC}

The input data is a pandas DataFrame with multi-index (datetime, instrument) and columns: $open, $high, $low, $close, $volume, $vwap.

Please output ONLY the factor expression string that can be directly used with the expression parser. 
The expression should use $variable format (e.g., $close, $open, $volume).
Do NOT include any Python code, just the expression string.
"""

        user_prompt = f"""Convert this factor into an expression:

Factor Name: {factor_name}
Factor Expression: {factor_expr}
Factor Description: {factor_desc}
Variables: {json.dumps(variables, ensure_ascii=False)}

Please provide the corrected expression that uses only the allowed operations.
Output format: Just the expression string, nothing else.
"""

        try:
            api = APIBackend()
            response = api.build_messages_and_create_chat_completion(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # 清理响应
            expr = response.strip().strip('"\'')
            
            # 验证表达式
            if self._validate_expression(expr):
                return expr
            else:
                logger.warning(f"LLM 生成的表达式无效: {expr}")
                return None
                
        except Exception as e:
            logger.error(f"LLM 调用失败: {str(e)}")
            return None
    
    def _validate_expression(self, expr: str) -> bool:
        """验证表达式是否有效"""
        if not expr:
            return False
        
        # 检查是否包含必要的变量
        if '$' not in expr:
            return False
        
        # 检查括号是否匹配
        if expr.count('(') != expr.count(')'):
            return False
        
        return True
    
    def _execute_factor_code(self, expr: str, factor_name: str) -> Optional[pd.Series]:
        """
        执行因子计算代码
        
        Args:
            expr: 因子表达式
            factor_name: 因子名称
            
        Returns:
            Optional[pd.Series]: 计算结果
        """
        try:
            return self._calculate_with_parser(expr)
        except Exception as e:
            logger.error(f"执行因子代码失败: {str(e)}")
            return None
    
    def _get_cache_key(self, expr: str) -> str:
        """生成缓存键"""
        return hashlib.md5(expr.encode()).hexdigest()
    
    def _load_from_cache(self, expr: str) -> Optional[pd.Series]:
        """从缓存加载因子值"""
        cache_key = self._get_cache_key(expr)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                return pd.read_pickle(cache_file)
            except Exception:
                return None
        return None
    
    def _save_to_cache(self, expr: str, result: pd.Series):
        """保存因子值到缓存"""
        cache_key = self._get_cache_key(expr)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            result.to_pickle(cache_file)
        except Exception as e:
            logger.warning(f"保存缓存失败: {str(e)}")


class QlibDataProvider:
    """Qlib 数据提供器"""
    
    def __init__(self, config: Dict):
        """
        初始化数据提供器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.data_config = config.get('data', {})
        self._initialized = False
        
    def _init_qlib(self):
        """初始化 Qlib"""
        if self._initialized:
            return
            
        import qlib
        from qlib.config import REG_CN
        
        provider_uri = self.data_config.get('provider_uri', '~/.qlib/qlib_data/cn_data')
        qlib.init(provider_uri=provider_uri, region=REG_CN)
        self._initialized = True
        logger.info(f"✓ Qlib 初始化完成: {provider_uri}")
        
    def get_stock_data(self, 
                      start_time: Optional[str] = None,
                      end_time: Optional[str] = None,
                      instruments: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            instruments: 股票池
            
        Returns:
            pd.DataFrame: 股票数据
        """
        self._init_qlib()
        
        from qlib.data import D
        
        start_time = start_time or self.data_config.get('start_time', '2016-01-01')
        end_time = end_time or self.data_config.get('end_time', '2025-12-31')
        instruments = instruments or self.data_config.get('market', 'csi300')
        
        # 获取股票列表
        stock_list = D.instruments(instruments)
        
        # 定义需要获取的字段
        fields = ['$open', '$high', '$low', '$close', '$volume', '$vwap']
        
        # 获取数据
        df = D.features(
            stock_list,
            fields,
            start_time=start_time,
            end_time=end_time,
            freq='day'
        )
        
        # 重命名列
        df.columns = fields
        
        # 计算收益率
        df['$return'] = df['$close'] / df.groupby('instrument')['$close'].shift(1) - 1
        
        logger.info(f"✓ 加载股票数据: {len(df)} 条记录")
        
        return df

