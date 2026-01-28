#!/usr/bin/env python3
"""
自定义因子计算器 - 直接使用 QuantaAlpha 的表达式解析器
支持所有因子挖掘时使用的表达式语法

功能:
1. 解析因子表达式 (使用 expr_parser)
2. 计算因子值 (使用 function_lib)
3. 生成与 Qlib DataLoader 兼容的数据格式
4. 支持从缓存加载预计算的因子值
"""

import hashlib
import json
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 抑制一些不必要的警告
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
warnings.filterwarnings('ignore', category=UserWarning, module='quantaalpha')

# 配置 joblib 使用线程后端而不是进程后端，避免子进程导入 LLM 模块
os.environ.setdefault('JOBLIB_START_METHOD', 'loky')

logger = logging.getLogger(__name__)

# 默认缓存目录
DEFAULT_CACHE_DIR = Path("/mnt/DATA/quantagent/QuantaAlpha/factor_cache")


class CustomFactorCalculator:
    """
    自定义因子计算器
    直接使用 QuantaAlpha 的表达式解析器和函数库
    支持从缓存加载预计算的因子值
    支持自动从主程序日志中提取缓存
    """
    
    def __init__(self, data_df: pd.DataFrame, cache_dir: Optional[Path] = None, auto_extract_cache: bool = True):
        """
        初始化因子计算器
        
        Args:
            data_df: 股票数据 DataFrame，需要有 MultiIndex (datetime, instrument)
                    列包含: $open, $high, $low, $close, $volume, $vwap
            cache_dir: 缓存目录路径 (可选)
            auto_extract_cache: 是否自动从主程序日志中提取缓存 (默认 True)
        """
        self.data_df = data_df
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.auto_extract_cache = auto_extract_cache
        self._cache_extracted = False  # 标记是否已执行过自动提取
        self._prepare_data()
        
    def _prepare_data(self):
        """准备数据，添加常用衍生列"""
        df = self.data_df.copy()
        
        # 添加 $return 列 (如果不存在)
        if '$return' not in df.columns:
            df['$return'] = df.groupby('instrument')['$close'].transform(
                lambda x: x / x.shift(1) - 1
            )
        
        self.data_df = df
        logger.info(f"数据准备完成: {len(df)} 行, 列: {list(df.columns)}")
    
    def _get_cache_key(self, expr: str) -> str:
        """生成缓存键 (使用表达式的 MD5 哈希)"""
        return hashlib.md5(expr.encode()).hexdigest()
    
    def _load_from_cache(self, expr: str) -> Optional[pd.Series]:
        """
        从缓存加载因子值
        
        Args:
            expr: 因子表达式
            
        Returns:
            Optional[pd.Series]: 缓存的因子值，如果不存在则返回 None
        """
        cache_key = self._get_cache_key(expr)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                result = pd.read_pickle(cache_file)
                return self._process_cached_result(result, cache_key)
            except Exception as e:
                logger.debug(f"缓存加载失败 [{cache_key}]: {e}")
                return None
        return None
    
    def _load_from_cache_location(self, cache_location: Dict) -> Optional[pd.Series]:
        """
        从 cache_location 字段指定的路径加载因子值
        
        Args:
            cache_location: 缓存位置信息，包含 result_h5_path
            
        Returns:
            Optional[pd.Series]: 缓存的因子值，如果不存在则返回 None
        """
        if not cache_location:
            return None
        
        result_h5_path = cache_location.get('result_h5_path', '')
        if not result_h5_path:
            return None
        
        h5_file = Path(result_h5_path)
        if not h5_file.exists():
            logger.debug(f"缓存文件不存在: {result_h5_path}")
            return None
        
        try:
            # 读取 HDF5 文件
            result = pd.read_hdf(str(h5_file))
            return self._process_cached_result(result, result_h5_path)
        except Exception as e:
            logger.debug(f"从 cache_location 加载失败 [{result_h5_path}]: {e}")
            return None
    
    def _process_cached_result(self, result: Any, source: str) -> Optional[pd.Series]:
        """
        处理缓存结果，统一格式
        
        Args:
            result: 从缓存加载的原始数据
            source: 数据来源（用于日志）
            
        Returns:
            Optional[pd.Series]: 处理后的因子值
        """
        try:
            # 处理可能的 DataFrame 格式
            if isinstance(result, pd.DataFrame):
                if len(result.columns) == 1:
                    result = result.iloc[:, 0]
                elif 'factor' in result.columns:
                    result = result['factor']
                else:
                    # 取第一列
                    result = result.iloc[:, 0]
            
            # 处理索引顺序不一致的问题
            # 缓存可能是 (datetime, instrument)，而回测数据是 (instrument, datetime)
            if isinstance(result.index, pd.MultiIndex):
                cache_idx_names = list(result.index.names)
                data_idx_names = list(self.data_df.index.names)
                
                # 如果索引名称顺序不同，调整顺序
                if cache_idx_names != data_idx_names and set(cache_idx_names) == set(data_idx_names):
                    # 交换索引级别以匹配目标数据
                    result = result.swaplevel()
                    result = result.sort_index()
            
            return result
        except Exception as e:
            logger.debug(f"处理缓存结果失败 [{source}]: {e}")
            return None
    
    def _save_to_cache(self, expr: str, result: pd.Series):
        """
        保存因子值到缓存
        
        Args:
            expr: 因子表达式
            result: 计算的因子值
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = self._get_cache_key(expr)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            result.to_pickle(cache_file)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def _auto_extract_cache_from_logs(self):
        """
        自动从主程序日志中提取缓存
        只在首次需要时执行一次
        """
        if self._cache_extracted:
            return
        
        self._cache_extracted = True
        
        try:
            # 动态导入缓存提取器
            from tools.factor_cache_extractor import extract_factors_to_cache
            
            logger.info("🔄 自动提取主程序缓存...")
            new_count = extract_factors_to_cache(
                output_dir=self.cache_dir,
                verbose=False
            )
            if new_count > 0:
                logger.info(f"   ✓ 新提取 {new_count} 个因子到缓存")
        except ImportError:
            logger.debug("缓存提取器不可用，跳过自动提取")
        except Exception as e:
            logger.warning(f"自动提取缓存失败: {e}")
        
    def calculate_factor(self, factor_name: str, factor_expression: str) -> Optional[pd.Series]:
        """
        计算单个因子
        
        Args:
            factor_name: 因子名称
            factor_expression: 因子表达式
            
        Returns:
            pd.Series: 因子值 (MultiIndex: datetime, instrument)
        """
        try:
            # 导入表达式解析器（静默导入，避免不必要的日志）
            import io
            import sys as _sys
            from contextlib import redirect_stdout
            
            # 配置 joblib 使用单线程模式，避免子进程导入问题
            from joblib import parallel_backend
            
            from quantaalpha.components.coder.factor_coder.expr_parser import (
                parse_expression, parse_symbol
            )
            # 导入函数库
            import quantaalpha.components.coder.factor_coder.function_lib as func_lib
            
            # 复制数据
            df = self.data_df.copy()
            
            # 解析表达式（抑制 parse_expression 的打印输出）
            expr = parse_symbol(factor_expression, df.columns)
            
            # 静默解析（抑制 print 输出）
            old_stdout = _sys.stdout
            _sys.stdout = io.StringIO()
            try:
                expr = parse_expression(expr)
            finally:
                _sys.stdout = old_stdout
            
            # 替换变量为 DataFrame 列引用
            for col in df.columns:
                if col.startswith('$'):
                    expr = expr.replace(col[1:], f"df['{col}']")
            
            # 构建执行环境
            exec_globals = {
                'df': df,
                'np': np,
                'pd': pd,
            }
            
            # 添加所有函数库中的函数
            for name in dir(func_lib):
                if not name.startswith('_'):
                    obj = getattr(func_lib, name)
                    if callable(obj):
                        exec_globals[name] = obj
            
            # 使用线程后端进行计算，避免子进程导入 LLM 模块
            # 注意：在loky多进程后端中，这里嵌套使用 threading 是安全的
            # from joblib import parallel_backend
            # with parallel_backend('threading', n_jobs=1):
            #     # 计算因子值
            #     result = eval(expr, exec_globals)
            result = eval(expr, exec_globals)
            
            if isinstance(result, pd.DataFrame):
                result = result.iloc[:, 0]
            
            if isinstance(result, pd.Series):
                result.name = factor_name
                # 确保结果与原始数据有相同的索引
                if not result.index.equals(df.index):
                    result = result.reindex(df.index)
                return result.astype(np.float64)
            else:
                # 如果结果是标量或数组，转换为 Series
                return pd.Series(result, index=df.index, name=factor_name).astype(np.float64)
                
        except Exception as e:
            logger.warning(f"因子计算失败 [{factor_name}]: {str(e)[:200]}")
            return None
    
    def calculate_factors_from_json(self, json_path: str, 
                                   max_factors: Optional[int] = None) -> pd.DataFrame:
        """
        从 JSON 文件批量计算因子
        
        Args:
            json_path: 因子 JSON 文件路径
            max_factors: 最大因子数量限制
            
        Returns:
            pd.DataFrame: 计算得到的因子值 DataFrame
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        factors = data.get('factors', {})
        
        results = {}
        success_count = 0
        fail_count = 0
        
        factor_items = list(factors.items())
        if max_factors:
            factor_items = factor_items[:max_factors]
        
        total = len(factor_items)
        logger.info(f"开始计算 {total} 个因子...")
        
        for i, (factor_id, factor_info) in enumerate(factor_items):
            factor_name = factor_info.get('factor_name', factor_id)
            factor_expr = factor_info.get('factor_expression', '')
            
            if not factor_expr:
                fail_count += 1
                continue
            
            if (i + 1) % 10 == 0 or i == 0:
                logger.info(f"  进度: {i+1}/{total}")
            
            result = self.calculate_factor(factor_name, factor_expr)
            
            if result is not None:
                results[factor_name] = result
                success_count += 1
            else:
                fail_count += 1
        
        logger.info(f"因子计算完成: 成功 {success_count}, 失败 {fail_count}")
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def calculate_factors_batch(self, factors: List[Dict], use_cache: bool = True, n_jobs: int = 1) -> pd.DataFrame:
        """
        批量计算因子 (全并行优化版)
        """
        if use_cache and self.auto_extract_cache:
            self._auto_extract_cache_from_logs()
        
        logger.info(f"开始处理 {len(factors)} 个因子 (并行度: {n_jobs})...")
        
        from joblib import Parallel, delayed
        
        # 并行执行所有任务 (缓存检查 + 计算)
        # 使用 loky 后端 (多进程) 以避免 Python GIL 导致的性能瓶颈
        # 注意: 需要将内部函数改为类方法以便 pickling
        parallel_results = Parallel(n_jobs=n_jobs, backend='loky')(
            delayed(self._process_single_factor)(info, use_cache) for info in factors
        )
        
        results = {}
        success_count = 0
        fail_count = 0
        stats = {"cache_location": 0, "md5_cache": 0, "computed": 0, "failed": 0, "empty_expr": 0}
        
        for name, expr, result, source in parallel_results:
            stats[source] = stats.get(source, 0) + 1
            
            if result is not None and len(result) > 0:
                if not result.isna().all():
                    results[name] = result
                    success_count += 1
                    # 如果是新计算的，保存到缓存
                    if source == "computed" and use_cache:
                        self._save_to_cache(expr, result)
                else:
                    fail_count += 1
                    logger.warning(f"    ✗ 因子 {name} 全为 NaN")
            elif source != "empty_expr":
                fail_count += 1
                if source == "computed":
                    logger.warning(f"    ✗ 因子 {name} 计算失败")
        
        logger.info(f"因子处理完成: 成功 {success_count}, 失败 {fail_count}")
        logger.info(f"  统计: {stats}")
        
        if results:
            result_df = pd.DataFrame(results, index=self.data_df.index)
            logger.info(f"  结果 DataFrame: {result_df.shape}")
            return result_df
        
        return pd.DataFrame()

    def _process_single_factor(self, factor_info, use_cache):
        """处理单个因子 (支持并行调用)"""
        import logging
        import sys
        
        # 配置简单的 logger，输出到 stderr
        logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(message)s')
        logger = logging.getLogger(f"worker_{os.getpid()}")
        
        factor_name = factor_info.get('factor_name', 'unknown')
        factor_expr = factor_info.get('factor_expression', '')
        cache_location = factor_info.get('cache_location')
        
        if not factor_expr:
            return factor_name, factor_expr, None, "empty_expr"
        
        # 1. 优先检查 cache_location
        if use_cache and cache_location:
            try:
                result = self._load_from_cache_location(cache_location)
                if result is not None:
                    result = self._validate_and_align_result(result, factor_name)
                    if result is not None:
                        return factor_name, factor_expr, result, "cache_location"
            except Exception:
                pass
        
        # 2. 检查 MD5 缓存
        if use_cache:
            try:
                result = self._load_from_cache(factor_expr)
                if result is not None:
                    result = self._validate_and_align_result(result, factor_name)
                    if result is not None:
                        return factor_name, factor_expr, result, "md5_cache"
            except Exception:
                pass
        
        # 3. 计算因子
        logger.info(f"    计算: {factor_name}")
        try:
            # 重新导入必要的模块以确保在子进程中可用
            import numpy as np
            import pandas as pd
            import quantaalpha.components.coder.factor_coder.function_lib as func_lib
            
            # 使用 eval 计算，不使用 self.calculate_factor 因为它包含了可能无法序列化的对象
            
            # 复制数据
            df = self.data_df.copy()
            
            # 导入表达式解析器
            from quantaalpha.components.coder.factor_coder.expr_parser import (
                parse_expression, parse_symbol
            )
            import io
            import sys as _sys
            
            # 解析表达式
            expr = parse_symbol(factor_expr, df.columns)
            
            # 静默解析
            old_stdout = _sys.stdout
            _sys.stdout = io.StringIO()
            try:
                expr = parse_expression(expr)
            finally:
                _sys.stdout = old_stdout
            
            # 替换变量为 DataFrame 列引用
            for col in df.columns:
                if col.startswith('$'):
                    expr = expr.replace(col[1:], f"df['{col}']")
            
            # 构建执行环境
            exec_globals = {
                'df': df,
                'np': np,
                'pd': pd,
            }
            
            # 添加所有函数库中的函数
            for name in dir(func_lib):
                if not name.startswith('_'):
                    obj = getattr(func_lib, name)
                    if callable(obj):
                        exec_globals[name] = obj
            
            result = eval(expr, exec_globals)
            
            if isinstance(result, pd.DataFrame):
                result = result.iloc[:, 0]
            
            if isinstance(result, pd.Series):
                result.name = factor_name
                # 确保结果与原始数据有相同的索引
                if not result.index.equals(df.index):
                    result = result.reindex(df.index)
                result = result.astype(np.float64)
            else:
                # 如果结果是标量或数组，转换为 Series
                result = pd.Series(result, index=df.index, name=factor_name).astype(np.float64)
            
            return factor_name, factor_expr, result, "computed"
        except Exception as e:
            # 记录详细错误信息
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            # logger 在子进程中可能无法正常工作，打印到标准错误
            import sys
            print(f"Error calculating {factor_name}: {error_msg}", file=sys.stderr)
            return factor_name, factor_expr, None, "failed"
    
    def _validate_and_align_result(self, result: pd.Series, factor_name: str) -> Optional[pd.Series]:
        """
        验证并对齐缓存结果的索引
        
        Args:
            result: 缓存加载的因子值
            factor_name: 因子名称（用于日志）
            
        Returns:
            Optional[pd.Series]: 对齐后的结果，如果验证失败则返回 None
        """
        if result is None:
            return None
        
        # 确保索引对齐
        if not result.index.equals(self.data_df.index):
            try:
                # 尝试对齐索引 - 缓存可能包含更多股票/日期
                common_idx = result.index.intersection(self.data_df.index)
                if len(common_idx) > len(self.data_df.index) * 0.5:  # 至少50%匹配
                    result = result.reindex(self.data_df.index)
                    logger.debug(f"    索引对齐: 共同索引 {len(common_idx)}, 目标 {len(self.data_df.index)}")
                else:
                    logger.warning(f"    ⚠ 缓存索引匹配率过低 ({len(common_idx)}/{len(self.data_df.index)}), 将重新计算")
                    return None
            except Exception as e:
                logger.warning(f"    ⚠ 索引对齐失败: {e}, 将重新计算")
                return None
        
        # 验证数据有效性
        if result is None or len(result) == 0 or result.isna().all():
            return None
        
        return result


class CustomFactorDataLoader:
    """
    自定义因子数据加载器
    将计算好的因子值转换为 Qlib 可用的格式
    """
    
    def __init__(self, factor_df: pd.DataFrame, label_expr: str = "Ref($close, -2) / Ref($close, -1) - 1"):
        """
        初始化数据加载器
        
        Args:
            factor_df: 因子值 DataFrame (MultiIndex: datetime, instrument)
            label_expr: 标签表达式
        """
        self.factor_df = factor_df
        self.label_expr = label_expr
        
    def to_qlib_format(self, data_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        转换为 Qlib 数据格式
        
        Args:
            data_df: 原始价格数据
            
        Returns:
            Tuple[features_df, labels_df]
        """
        # 计算标签
        from quantaalpha.components.coder.factor_coder.expr_parser import (
            parse_expression, parse_symbol
        )
        import quantaalpha.components.coder.factor_coder.function_lib as func_lib
        
        df = data_df.copy()
        
        # 解析标签表达式
        expr = parse_symbol(self.label_expr, df.columns)
        expr = parse_expression(expr)
        
        for col in df.columns:
            if col.startswith('$'):
                expr = expr.replace(col[1:], f"df['{col}']")
        
        exec_globals = {'df': df, 'np': np, 'pd': pd}
        for name in dir(func_lib):
            if not name.startswith('_'):
                obj = getattr(func_lib, name)
                if callable(obj):
                    exec_globals[name] = obj
        
        label = eval(expr, exec_globals)
        if isinstance(label, pd.DataFrame):
            label = label.iloc[:, 0]
        
        labels_df = pd.DataFrame({'LABEL0': label})
        
        return self.factor_df, labels_df


def get_qlib_stock_data(config: Dict) -> pd.DataFrame:
    """
    从 Qlib 获取股票数据
    
    Args:
        config: 配置字典，包含 data 配置
        
    Returns:
        pd.DataFrame: 股票数据
    """
    import qlib
    from qlib.data import D
    
    data_config = config.get('data', {})
    
    provider_uri = data_config.get('provider_uri', '/home/tjxy/.qlib/qlib_data/cn_data')
    
    # 初始化 Qlib (如果尚未初始化)
    try:
        qlib.init(provider_uri=provider_uri, region='cn')
    except Exception:
        pass  # 已经初始化
    
    start_time = data_config.get('start_time', '2016-01-01')
    end_time = data_config.get('end_time', '2025-12-31')
    market = data_config.get('market', 'csi300')
    
    # 获取股票列表
    stock_list = D.instruments(market)
    
    # 获取数据
    fields = ['$open', '$high', '$low', '$close', '$volume', '$vwap']
    df = D.features(
        stock_list,
        fields,
        start_time=start_time,
        end_time=end_time,
        freq='day'
    )
    
    df.columns = fields
    
    logger.info(f"✓ 加载股票数据: {len(df)} 行")
    
    return df


if __name__ == '__main__':
    """测试因子计算"""
    import yaml
    
    logging.basicConfig(level=logging.INFO)
    
    # 加载配置
    config_path = Path(__file__).parent / 'config.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 获取数据
    print("获取股票数据...")
    data_df = get_qlib_stock_data(config)
    
    # 创建计算器
    calculator = CustomFactorCalculator(data_df)
    
    # 测试单个因子
    test_expr = "RANK(-1 * TS_PCTCHANGE($close, 10))"
    print(f"\n测试表达式: {test_expr}")
    
    result = calculator.calculate_factor("test_factor", test_expr)
    if result is not None:
        print(f"计算成功! 结果形状: {result.shape}")
        print(result.head())
    else:
        print("计算失败!")

