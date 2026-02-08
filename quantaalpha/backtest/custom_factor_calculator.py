#!/usr/bin/env python3
"""
自定义因子计算器 - 直接使用 AlphaAgent 的表达式解析器
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

# 添加项目路径 (从 quantaalpha/backtest/ 向上三级到项目根目录)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

# 抑制一些不必要的警告
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
warnings.filterwarnings('ignore', category=UserWarning, module='quantaalpha')

# 配置 joblib 使用线程后端而不是进程后端，避免子进程导入 LLM 模块
os.environ.setdefault('JOBLIB_START_METHOD', 'loky')

logger = logging.getLogger(__name__)

# 默认缓存目录（优先从环境变量 FACTOR_CACHE_DIR 读取）
DEFAULT_CACHE_DIR = Path(os.environ.get("FACTOR_CACHE_DIR", "data/results/factor_cache"))


class CustomFactorCalculator:
    """
    自定义因子计算器
    直接使用 AlphaAgent 的表达式解析器和函数库
    支持从缓存加载预计算的因子值
    支持自动从主程序日志中提取缓存
    """
    
    def __init__(self, data_df: Optional[pd.DataFrame] = None, cache_dir: Optional[Path] = None, 
                 auto_extract_cache: bool = True, config: Optional[Dict] = None):
        """
        初始化因子计算器
        
        Args:
            data_df: 股票数据 DataFrame (可选，延迟加载)
            cache_dir: 缓存目录路径 (可选)
            auto_extract_cache: 是否自动从主程序日志中提取缓存 (默认 True)
            config: 配置字典，用于延迟加载数据 (可选)
        """
        self._raw_data_df = data_df
        self._data_prepared = False
        self._config = config
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.auto_extract_cache = auto_extract_cache
        self._cache_extracted = False  # 标记是否已执行过自动提取
        
        # 如果已经提供了数据，立即准备
        if data_df is not None and len(data_df) > 0:
            self._prepare_data()
    
    @property
    def data_df(self) -> pd.DataFrame:
        """延迟加载股票数据"""
        if not self._data_prepared:
            if self._raw_data_df is None or len(self._raw_data_df) == 0:
                if self._config is not None:
                    print("  加载股票数据（需要从表达式计算因子）...")
                    self._raw_data_df = get_qlib_stock_data(self._config)
                else:
                    raise ValueError("未提供股票数据且无配置用于加载")
            self._prepare_data()
        return self._raw_data_df
        
    def _prepare_data(self):
        """准备数据，添加常用衍生列"""
        if self._data_prepared:
            return
        
        df = self._raw_data_df.copy()
        
        # 添加 $return 列 (如果不存在)
        if '$return' not in df.columns:
            df['$return'] = df.groupby('instrument')['$close'].transform(
                lambda x: x / x.shift(1) - 1
            )
        
        # 去除重复索引（保留最后出现的），避免 reindex 时报错
        if df.index.duplicated().any():
            dup_count = df.index.duplicated().sum()
            logger.warning(f"数据存在 {dup_count} 个重复索引，已自动去重")
            df = df[~df.index.duplicated(keep='last')]
        
        self._raw_data_df = df
        self._data_prepared = True
        logger.debug(f"数据准备完成: {len(df)} 行, 列: {list(df.columns)}")
    
    def _get_cache_key(self, expr: str) -> str:
        """生成缓存键 (使用表达式的 MD5 哈希)"""
        return hashlib.md5(expr.encode()).hexdigest()
    
    def _load_from_cache(self, expr: str) -> Optional[pd.Series]:
        """从缓存加载因子值"""
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
        """从 cache_location 字段指定的路径加载因子值"""
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
            result = pd.read_hdf(str(h5_file))
            return self._process_cached_result(result, result_h5_path)
        except Exception as e:
            logger.debug(f"从 cache_location 加载失败 [{result_h5_path}]: {e}")
            return None
    
    def _process_cached_result(self, result: Any, source: str) -> Optional[pd.Series]:
        """处理缓存结果，统一格式（不访问 self.data_df，避免触发延迟加载）"""
        try:
            # 处理可能的 DataFrame 格式
            if isinstance(result, pd.DataFrame):
                if len(result.columns) == 1:
                    result = result.iloc[:, 0]
                elif 'factor' in result.columns:
                    result = result['factor']
                else:
                    result = result.iloc[:, 0]
            
            # 处理索引顺序不一致的问题
            # 标准顺序应该是 (datetime, instrument)
            if isinstance(result.index, pd.MultiIndex):
                cache_idx_names = list(result.index.names)
                expected_order = ['datetime', 'instrument']
                if cache_idx_names != expected_order and set(cache_idx_names) == set(expected_order):
                    result = result.swaplevel()
                    result = result.sort_index()
            
            return result
        except Exception as e:
            logger.debug(f"处理缓存结果失败 [{source}]: {e}")
            return None
    
    def _save_to_cache(self, expr: str, result: pd.Series):
        """保存因子值到缓存"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = self._get_cache_key(expr)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            result.to_pickle(cache_file)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def _auto_extract_cache_from_logs(self):
        """自动从主程序日志中提取缓存，只在首次需要时执行一次"""
        if self._cache_extracted:
            return
        
        self._cache_extracted = True
        
        try:
            from tools.factor_cache_extractor import extract_factors_to_cache
            
            logger.debug("自动提取主程序缓存...")
            new_count = extract_factors_to_cache(
                output_dir=self.cache_dir,
                verbose=False
            )
            if new_count > 0:
                logger.debug(f"新提取 {new_count} 个因子到缓存")
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
            import io
            import sys as _sys
            from joblib import parallel_backend
            
            from quantaalpha.factors.coder.expr_parser import (
                parse_expression, parse_symbol
            )
            import quantaalpha.factors.coder.function_lib as func_lib
            
            df = self.data_df.copy()
            
            # 解析表达式（抑制 parse_expression 的打印输出）
            expr = parse_symbol(factor_expression, df.columns)
            
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
            
            for name in dir(func_lib):
                if not name.startswith('_'):
                    obj = getattr(func_lib, name)
                    if callable(obj):
                        exec_globals[name] = obj
            
            # 使用线程后端进行计算
            with parallel_backend('threading', n_jobs=1):
                result = eval(expr, exec_globals)
            
            if isinstance(result, pd.DataFrame):
                result = result.iloc[:, 0]
            
            if isinstance(result, pd.Series):
                result.name = factor_name
                # 确保结果与原始数据有相同的索引 (duplicate-safe)
                if not result.index.equals(df.index):
                    try:
                        if result.index.duplicated().any():
                            result = result[~result.index.duplicated(keep='last')]
                        result = result.reindex(df.index)
                    except Exception:
                        logger.debug(f"reindex fallback for [{factor_name}]")
                        result = result[~result.index.duplicated(keep='last')]
                        clean_idx = df.index[~df.index.duplicated(keep='last')]
                        result = result.reindex(clean_idx)
                return result.astype(np.float64)
            else:
                return pd.Series(result, index=df.index, name=factor_name).astype(np.float64)
                
        except Exception as e:
            logger.warning(f"因子计算失败 [{factor_name}]: {str(e)[:200]}")
            return None
    
    def calculate_factors_from_json(self, json_path: str, 
                                   max_factors: Optional[int] = None) -> pd.DataFrame:
        """从 JSON 文件批量计算因子"""
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
        logger.debug(f"开始计算 {total} 个因子...")
        
        for i, (factor_id, factor_info) in enumerate(factor_items):
            factor_name = factor_info.get('factor_name', factor_id)
            factor_expr = factor_info.get('factor_expression', '')
            
            if not factor_expr:
                fail_count += 1
                continue
            
            if (i + 1) % 10 == 0 or i == 0:
                logger.debug(f"  进度: {i+1}/{total}")
            
            result = self.calculate_factor(factor_name, factor_expr)
            
            if result is not None:
                results[factor_name] = result
                success_count += 1
            else:
                fail_count += 1
        
        print(f"因子计算完成: 成功 {success_count}, 失败 {fail_count}")
        
        if results:
            return pd.DataFrame(results)
        return pd.DataFrame()
    
    def calculate_factors_batch(self, factors: List[Dict], use_cache: bool = True) -> pd.DataFrame:
        """
        批量计算因子
        
        优先级:
        1. cache_location 字段（直接从 result.h5 读取）
        2. MD5 缓存（factor_cache 目录）
        3. 使用 factor_expression 重新计算
        """
        import time as _time
        
        # 自动从主程序日志中提取缓存
        if use_cache and self.auto_extract_cache:
            self._auto_extract_cache_from_logs()
        
        results = {}
        success_count = 0
        fail_count = 0
        cache_hit_count = 0
        cache_location_hit_count = 0
        compute_count = 0
        failed_names = []
        total = len(factors)
        need_compute_factors = []  # 记录需要从表达式计算的因子
        
        # === Pass 1: 尝试从缓存加载所有因子 ===
        for i, factor_info in enumerate(factors):
            factor_name = factor_info.get('factor_name', 'unknown')
            factor_expr = factor_info.get('factor_expression', '')
            cache_location = factor_info.get('cache_location')
            
            if not factor_expr:
                fail_count += 1
                failed_names.append(factor_name)
                continue
            
            result = None
            
            # 1. 优先检查 cache_location (从 result.h5 直接读取)
            if use_cache and cache_location:
                h5_path = cache_location.get('result_h5_path', '')
                if h5_path:
                    result = self._load_from_cache_location(cache_location)
                    if result is not None:
                        cache_location_hit_count += 1
                        results[factor_name] = result
                        success_count += 1
                        print(f"  [{i+1}/{total}] ✓ H5缓存: {factor_name}")
                        continue
            
            # 2. 检查 MD5 缓存
            if use_cache:
                result = self._load_from_cache(factor_expr)
                if result is not None:
                    cache_hit_count += 1
                    results[factor_name] = result
                    success_count += 1
                    print(f"  [{i+1}/{total}] ✓ MD5缓存: {factor_name}")
                    continue
            
            # 3. 需要从表达式计算，记录下来
            need_compute_factors.append((i, factor_info))
            print(f"  [{i+1}/{total}] ⏳ 待计算: {factor_name}")
        
        # === Pass 2: 从表达式计算未缓存的因子 ===
        if need_compute_factors:
            print(f"  开始从表达式计算 {len(need_compute_factors)} 个因子...")
            
            for idx, (orig_i, factor_info) in enumerate(need_compute_factors):
                factor_name = factor_info.get('factor_name', 'unknown')
                factor_expr = factor_info.get('factor_expression', '')
                
                print(f"  计算 [{idx+1}/{len(need_compute_factors)}]: {factor_name} ...", end='', flush=True)
                t0 = _time.time()
                
                try:
                    # 超时保护：单个因子计算最多 120 秒
                    import signal as _signal
                    
                    class _FactorTimeout(Exception):
                        pass
                    
                    def _timeout_handler(signum, frame):
                        raise _FactorTimeout()
                    
                    old_handler = None
                    try:
                        old_handler = _signal.signal(_signal.SIGALRM, _timeout_handler)
                        _signal.alarm(120)  # 120 秒超时
                    except (AttributeError, ValueError):
                        pass  # Windows 或非主线程不支持 SIGALRM
                    
                    result = self.calculate_factor(factor_name, factor_expr)
                    
                    try:
                        _signal.alarm(0)  # 取消超时
                        if old_handler is not None:
                            _signal.signal(_signal.SIGALRM, old_handler)
                    except (AttributeError, ValueError):
                        pass
                    
                except _FactorTimeout:
                    elapsed = _time.time() - t0
                    print(f" ✗ 超时 ({elapsed:.1f}s)")
                    fail_count += 1
                    failed_names.append(f"{factor_name}(超时)")
                    try:
                        _signal.alarm(0)
                        if old_handler is not None:
                            _signal.signal(_signal.SIGALRM, old_handler)
                    except (AttributeError, ValueError):
                        pass
                    continue
                except Exception as e:
                    elapsed = _time.time() - t0
                    print(f" ✗ 异常 ({elapsed:.1f}s): {str(e)[:80]}")
                    fail_count += 1
                    failed_names.append(factor_name)
                    continue
                
                elapsed = _time.time() - t0
                
                if result is not None and len(result) > 0:
                    if not result.isna().all():
                        results[factor_name] = result
                        success_count += 1
                        compute_count += 1
                        print(f" ✓ ({elapsed:.1f}s)")
                        # 保存到 MD5 缓存
                        if use_cache:
                            self._save_to_cache(factor_expr, result)
                    else:
                        fail_count += 1
                        failed_names.append(factor_name)
                        print(f" ✗ 全NaN ({elapsed:.1f}s)")
                else:
                    fail_count += 1
                    failed_names.append(factor_name)
                    print(f" ✗ 失败 ({elapsed:.1f}s)")
        
        # 摘要
        print(f"因子加载完成: 成功 {success_count}, 失败 {fail_count} | "
              f"H5缓存 {cache_location_hit_count}, MD5缓存 {cache_hit_count}, 重算 {compute_count}")
        if failed_names:
            print(f"  失败因子: {', '.join(failed_names)}")
        
        # === 构建 DataFrame ===
        if not results:
            return pd.DataFrame()
        
        # 对齐所有结果到统一索引
        # 如果有缓存结果，可能需要对齐索引
        aligned_results = {}
        reference_index = None
        
        for name, series in results.items():
            if reference_index is None:
                reference_index = series.index
            validated = self._validate_and_align_result(series, name, reference_index)
            if validated is not None:
                aligned_results[name] = validated
        
        if aligned_results:
            result_df = pd.DataFrame(aligned_results)
            logger.debug(f"  结果 DataFrame: {result_df.shape}")
            return result_df
        
        return pd.DataFrame()
    
    def _validate_and_align_result(self, result: pd.Series, factor_name: str, 
                                    reference_index: Optional[pd.Index] = None) -> Optional[pd.Series]:
        """验证并对齐缓存结果的索引"""
        if result is None:
            return None
        
        # 确定目标索引
        target_idx = reference_index
        if target_idx is None:
            # 只有在需要对齐时才访问 data_df（触发延迟加载）
            try:
                target_idx = self.data_df.index
            except Exception:
                # 如果无法加载数据，直接返回原始结果
                return result if len(result) > 0 and not result.isna().all() else None
        
        # 确保索引对齐 (duplicate-safe)
        if not result.index.equals(target_idx):
            try:
                if result.index.duplicated().any():
                    result = result[~result.index.duplicated(keep='last')]
                if target_idx.duplicated().any():
                    target_idx = target_idx[~target_idx.duplicated(keep='last')]
                
                common_idx = result.index.intersection(target_idx)
                if len(common_idx) > len(target_idx) * 0.5:
                    result = result.reindex(target_idx)
                    logger.debug(f"    索引对齐: 共同索引 {len(common_idx)}, 目标 {len(target_idx)}")
                else:
                    logger.warning(f"    缓存索引匹配率过低 ({len(common_idx)}/{len(target_idx)}), 将重新计算")
                    return None
            except Exception as e:
                logger.warning(f"    索引对齐失败: {e}, 将重新计算")
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
        self.factor_df = factor_df
        self.label_expr = label_expr
        
    def to_qlib_format(self, data_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """转换为 Qlib 数据格式"""
        from quantaalpha.factors.coder.expr_parser import (
            parse_expression, parse_symbol
        )
        import quantaalpha.factors.coder.function_lib as func_lib
        
        df = data_df.copy()
        
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
    """从 Qlib 获取股票数据"""
    import qlib
    from qlib.data import D
    
    data_config = config.get('data', {})
    
    # 优先使用环境变量中的 QLIB_DATA_DIR，与 runner.py 保持一致
    provider_uri = (
        os.environ.get('QLIB_DATA_DIR')
        or os.environ.get('QLIB_PROVIDER_URI')
        or data_config.get('provider_uri', os.path.expanduser('~/.qlib/qlib_data/cn_data'))
    )
    provider_uri = os.path.expanduser(provider_uri)
    region = data_config.get('region', 'cn')
    
    try:
        qlib.init(provider_uri=provider_uri, region=region)
    except Exception:
        pass  # 已经初始化
    
    start_time = data_config.get('start_time', '2016-01-01')
    end_time = data_config.get('end_time', '2025-12-31')
    market = data_config.get('market', 'csi300')
    
    stock_list = D.instruments(market)
    
    fields = ['$open', '$high', '$low', '$close', '$volume', '$vwap']
    df = D.features(
        stock_list,
        fields,
        start_time=start_time,
        end_time=end_time,
        freq='day'
    )
    
    df.columns = fields
    
    logger.debug(f"加载股票数据: {len(df)} 行")
    
    return df


if __name__ == '__main__':
    """测试因子计算"""
    import yaml
    
    logging.basicConfig(level=logging.INFO)
    
    _project_root = Path(__file__).resolve().parents[2]
    config_path = _project_root / 'configs' / 'backtest.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("获取股票数据...")
    data_df = get_qlib_stock_data(config)
    
    calculator = CustomFactorCalculator(data_df)
    
    test_expr = "RANK(-1 * TS_PCTCHANGE($close, 10))"
    print(f"\n测试表达式: {test_expr}")
    
    result = calculator.calculate_factor("test_factor", test_expr)
    if result is not None:
        print(f"计算成功! 结果形状: {result.shape}")
        print(result.head())
    else:
        print("计算失败!")
