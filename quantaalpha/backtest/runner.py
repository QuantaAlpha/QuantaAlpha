#!/usr/bin/env python3
"""
回测执行器 - 使用 Qlib 进行完整回测

功能:
1. 加载因子（官方/自定义）
2. 计算自定义因子值 (使用 AlphaAgent 表达式解析器)
3. 训练模型
4. 执行回测
5. 计算评估指标

支持两种模式:
- 官方因子模式: 使用 Qlib 内置的 DataLoader
- 自定义因子模式: 使用 expr_parser + function_lib 计算因子值
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd
import yaml

# 添加项目路径 (从 quantaalpha/backtest/ 向上三级到项目根目录)
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class BacktestRunner:
    """回测执行器"""
    
    def __init__(self, config_path: str):
        """
        初始化回测执行器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._qlib_initialized = False
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"✓ 加载配置文件: {self.config_path}")
        return config
    
    def _init_qlib(self):
        """初始化 Qlib"""
        if self._qlib_initialized:
            return
            
        import os
        import qlib
        
        # 优先使用 .env 中的 QLIB_DATA_DIR，其次使用配置文件中的 provider_uri
        provider_uri = (
            os.environ.get('QLIB_DATA_DIR')
            or os.environ.get('QLIB_PROVIDER_URI')
            or self.config['data']['provider_uri']
        )
        provider_uri = os.path.expanduser(provider_uri)
        region = self.config['data'].get('region', 'cn')
        qlib.init(provider_uri=provider_uri, region=region)
        self._qlib_initialized = True
        logger.info(f"✓ Qlib 初始化完成: {provider_uri} (region={region})")
    
    def run(self, 
            factor_source: Optional[str] = None,
            factor_json: Optional[List[str]] = None,
            experiment_name: Optional[str] = None,
            output_name: Optional[str] = None) -> Dict:
        """
        执行完整回测流程
        
        Args:
            factor_source: 因子源类型 (覆盖配置文件)
            factor_json: 自定义因子 JSON 文件路径列表 (覆盖配置文件)
            experiment_name: 实验名称 (覆盖配置文件)
            output_name: 输出文件名前缀 (可选，默认使用因子库文件名)
            
        Returns:
            Dict: 回测结果指标
        """
        start_time_total = time.time()
        
        # 初始化 Qlib
        self._init_qlib()
        
        # 更新配置
        if factor_source:
            self.config['factor_source']['type'] = factor_source
        if factor_json:
            self.config['factor_source']['custom']['json_files'] = factor_json
        
        # 自动从因子库文件名生成输出名称
        if output_name is None and factor_json:
            # 取第一个因子库文件名（去掉扩展名）
            output_name = Path(factor_json[0]).stem
        
        exp_name = experiment_name or output_name or self.config['experiment']['name']
        rec_name = self.config['experiment']['recorder']
        
        print(f"\n{'='*50}")
        src = factor_json[0] if factor_json else exp_name
        print(f"开始回测: {src}")
        print(f"{'='*50}")
        
        # 1. 加载因子
        factor_expressions, custom_factors = self._load_factors()
        print(f"[1/4] 加载因子: Qlib {len(factor_expressions)} 个, 自定义 {len(custom_factors)} 个")
        
        # 2. 计算自定义因子（如果有）
        computed_factors = None
        if custom_factors:
            computed_factors = self._compute_custom_factors(custom_factors)
            n_computed = len(computed_factors.columns) if computed_factors is not None and not computed_factors.empty else 0
            print(f"[2/4] 计算自定义因子: 成功 {n_computed} 个")
        else:
            logger.debug("[2/4] 无自定义因子，跳过")
        
        # 3. 创建数据集
        dataset = self._create_dataset(factor_expressions, computed_factors)
        print("[3/4] 创建数据集完成")
        
        # 4. 训练模型并回测
        metrics = self._train_and_backtest(dataset, exp_name, rec_name, output_name=output_name)
        
        # 5. 输出结果
        total_time = time.time() - start_time_total
        self._print_results(metrics, total_time)
        
        # 6. 保存结果
        self._save_results(metrics, exp_name, factor_source or self.config['factor_source']['type'], 
                          len(factor_expressions) + len(custom_factors), total_time,
                          output_name=output_name)
        
        return metrics
    
    def _load_factors(self) -> Tuple[Dict[str, str], List[Dict]]:
        """加载因子"""
        from .factor_loader import FactorLoader
        
        loader = FactorLoader(self.config)
        return loader.load_factors()
    
    def _compute_custom_factors(self, factors: List[Dict]) -> Optional[pd.DataFrame]:
        """
        计算自定义因子
        使用 AlphaAgent 的 expr_parser 和 function_lib
        支持从缓存加载预计算的因子值
        
        优化: 先尝试从缓存加载，只有需要从表达式计算时才加载股票数据
        """
        from .custom_factor_calculator import CustomFactorCalculator
        from pathlib import Path
        
        # 获取缓存配置
        llm_config = self.config.get('llm', {})
        cache_dir = llm_config.get('cache_dir')
        if cache_dir:
            cache_dir = Path(cache_dir)
        
        # 是否自动从主程序日志提取缓存
        auto_extract = llm_config.get('auto_extract_cache', True)
        
        # 创建计算器 — 延迟加载股票数据
        # 只有当因子需要从表达式计算时，才会加载股票数据
        calculator = CustomFactorCalculator(
            data_df=None,  # 延迟加载
            cache_dir=cache_dir, 
            auto_extract_cache=auto_extract,
            config=self.config,  # 传入配置用于按需加载
        )
        
        # 计算因子 (会优先检查缓存，缓存不存在才加载数据并计算)
        result_df = calculator.calculate_factors_batch(factors, use_cache=True)
        
        # 验证结果
        if result_df is None:
            logger.error("因子计算返回 None")
            return None
        
        if not isinstance(result_df, pd.DataFrame):
            logger.error(f"因子计算返回类型错误: {type(result_df)}")
            return None
        
        if result_df.empty:
            logger.error("因子计算结果为空 DataFrame")
            return None
        
        # 确保索引正确
        if not isinstance(result_df.index, pd.MultiIndex):
            logger.warning("因子数据索引不是 MultiIndex，尝试修复...")
        
        logger.debug(f"  因子计算完成: {len(result_df.columns)} 个因子, {len(result_df)} 行数据")
        
        return result_df
    
    def _create_dataset(self, 
                       factor_expressions: Dict[str, str],
                       computed_factors: Optional[pd.DataFrame] = None):
        """
        创建 Qlib 数据集
        
        支持两种模式:
        1. 纯 Qlib 因子模式: 使用 QlibDataLoader
        2. 自定义因子模式: 使用预计算的因子值 + StaticDataLoader
        """
        from qlib.data.dataset import DatasetH
        from qlib.data.dataset.handler import DataHandlerLP
        
        data_config = self.config['data']
        dataset_config = self.config['dataset']
        
        # 检查 computed_factors 的有效性
        has_computed_factors = False
        if computed_factors is not None:
            if isinstance(computed_factors, pd.DataFrame):
                # 检查是否有数据
                if len(computed_factors) > 0 and len(computed_factors.columns) > 0:
                    has_computed_factors = True
                    logger.debug(f"  检测到预计算因子: {len(computed_factors.columns)} 个因子, {len(computed_factors)} 行数据")
                else:
                    logger.warning(f"  预计算因子 DataFrame 为空: {computed_factors.shape}")
            else:
                logger.warning(f"  预计算因子类型不正确: {type(computed_factors)}")
        
        # 如果有计算好的自定义因子，优先使用自定义因子模式
        if has_computed_factors:
            logger.debug("  使用自定义因子模式 (预计算因子值)")
            return self._create_dataset_with_computed_factors(
                factor_expressions, computed_factors
            )
        
        # 纯 Qlib 因子模式
        expressions = list(factor_expressions.values())
        names = list(factor_expressions.keys())
        
        # 检查是否有有效的因子
        if not expressions:
            raise ValueError("没有可用的因子表达式。如果使用自定义因子，请确保因子计算成功。")
        
        handler_config = {
            'start_time': data_config['start_time'],
            'end_time': data_config['end_time'],
            'instruments': data_config['market'],
            'data_loader': {
                'class': 'QlibDataLoader',
                'module_path': 'qlib.contrib.data.loader',
                'kwargs': {
                    'config': {
                        'feature': (expressions, names),
                        'label': ([dataset_config['label']], ['LABEL0'])
                    }
                }
            },
            'learn_processors': dataset_config['learn_processors'],
            'infer_processors': dataset_config['infer_processors']
        }
        
        dataset = DatasetH(
            handler=DataHandlerLP(**handler_config),
            segments=dataset_config['segments']
        )
        
        logger.debug(f"  Qlib因子模式: {len(expressions)} 个因子, 训练集={dataset_config['segments']['train']}")
        
        return dataset
    
    def _create_dataset_with_computed_factors(self,
                                              factor_expressions: Dict[str, str],
                                              computed_factors: pd.DataFrame):
        """
        使用预计算的因子值创建数据集
        
        这种模式下:
        1. 先计算标签
        2. 将因子值和标签合并
        3. 使用自定义 DataHandler 加载数据
        """
        from qlib.data.dataset import DatasetH
        from qlib.data.dataset.handler import DataHandler
        from qlib.data import D
        
        data_config = self.config['data']
        dataset_config = self.config['dataset']
        
        logger.debug(f"  计算因子数量: {len(computed_factors.columns)}")
        
        # 计算标签
        label_expr = dataset_config['label']
        label_df = self._compute_label(label_expr)
        
        # 合并 Qlib 兼容因子 (如果有)
        all_feature_dfs = [computed_factors]
        
        if factor_expressions:
            logger.debug(f"  加载 {len(factor_expressions)} 个 Qlib 兼容因子")
            qlib_factors = self._load_qlib_factors(factor_expressions)
            if qlib_factors is not None and not qlib_factors.empty:
                all_feature_dfs.append(qlib_factors)
        
        # 合并所有因子
        features_df = pd.concat(all_feature_dfs, axis=1)
        
        # 去除重复列
        features_df = features_df.loc[:, ~features_df.columns.duplicated()]
        
        logger.debug(f"  总因子数量: {len(features_df.columns)}")
        
        # ---- 标准化 MultiIndex level 名称 ----
        # Qlib label 通常是 (datetime, instrument), 但自定义因子缓存可能
        # 有不同的 level 名称 (如 None, 或 'date'). 统一规范化为 (datetime, instrument).
        def _normalize_multiindex(df, df_name):
            """确保 DataFrame 的 MultiIndex 具有标准的 (datetime, instrument) level 名称"""
            if not isinstance(df.index, pd.MultiIndex):
                logger.warning(f"  {df_name} 索引不是 MultiIndex: {type(df.index)}")
                return df
            
            names = list(df.index.names)
            logger.debug(f"  {df_name} index levels: {names}, "
                        f"dtypes: {[str(df.index.get_level_values(i).dtype) for i in range(len(names))]}, "
                        f"len: {len(df)}")
            
            # 检测哪个 level 是 datetime, 哪个是 instrument
            new_names = list(names)
            for i, name in enumerate(names):
                level_vals = df.index.get_level_values(i)
                if name == 'datetime' or name == 'date':
                    new_names[i] = 'datetime'
                elif name == 'instrument' or name == 'stock':
                    new_names[i] = 'instrument'
                elif name is None:
                    # 通过 dtype 推断
                    if pd.api.types.is_datetime64_any_dtype(level_vals):
                        new_names[i] = 'datetime'
                    elif level_vals.dtype == object or pd.api.types.is_string_dtype(level_vals):
                        new_names[i] = 'instrument'
            
            if new_names != names:
                logger.debug(f"  {df_name} index 重命名: {names} → {new_names}")
                df.index = df.index.set_names(new_names)
            
            # 确保 (datetime, instrument) 顺序
            actual_names = list(df.index.names)
            if len(actual_names) == 2 and actual_names == ['instrument', 'datetime']:
                df = df.swaplevel()
                df = df.sort_index()
                logger.debug(f"  {df_name} index 已交换为 (datetime, instrument) 顺序")
            
            return df
        
        features_df = _normalize_multiindex(features_df, "features")
        label_df = _normalize_multiindex(label_df, "label")
        
        # ---- 对齐索引 ----
        # 先尝试直接 intersection
        common_index = features_df.index.intersection(label_df.index)
        
        # 如果直接 intersection 为空，尝试对齐 datetime 类型
        if len(common_index) == 0 and len(features_df) > 0 and len(label_df) > 0:
            logger.warning("  直接索引交集为空，尝试对齐 datetime 类型...")
            
            # 获取两侧的 datetime level 样本
            feat_dt = features_df.index.get_level_values('datetime')
            label_dt = label_df.index.get_level_values('datetime')
            logger.debug(f"  features datetime dtype={feat_dt.dtype}, sample={feat_dt[:3].tolist()}")
            logger.debug(f"  label    datetime dtype={label_dt.dtype}, sample={label_dt[:3].tolist()}")
            
            feat_inst = features_df.index.get_level_values('instrument')
            label_inst = label_df.index.get_level_values('instrument')
            logger.debug(f"  features instrument sample={feat_inst[:3].tolist()}")
            logger.debug(f"  label    instrument sample={label_inst[:3].tolist()}")
            
            # 尝试统一 datetime 为 pandas Timestamp
            try:
                if not pd.api.types.is_datetime64_any_dtype(feat_dt):
                    features_df.index = features_df.index.set_levels(
                        pd.to_datetime(feat_dt.unique()), level='datetime'
                    )
                    logger.debug("  features datetime 已转换为 Timestamp")
                if not pd.api.types.is_datetime64_any_dtype(label_dt):
                    label_df.index = label_df.index.set_levels(
                        pd.to_datetime(label_dt.unique()), level='datetime'
                    )
                    logger.debug("  label datetime 已转换为 Timestamp")
            except Exception as e:
                logger.warning(f"  datetime 类型转换失败: {e}")
            
            # 重新计算交集
            common_index = features_df.index.intersection(label_df.index)
            logger.debug(f"  类型对齐后交集大小: {len(common_index)}")
        
        if len(common_index) == 0:
            # 最后兜底：使用 pd.merge 基于 reset_index 做 inner join
            logger.warning("  索引交集仍为空，尝试使用 merge 对齐...")
            feat_reset = features_df.reset_index()
            label_reset = label_df.reset_index()
            
            # 找到共同的 datetime 和 instrument 列
            dt_col = 'datetime' if 'datetime' in feat_reset.columns else feat_reset.columns[0]
            inst_col = 'instrument' if 'instrument' in feat_reset.columns else feat_reset.columns[1]
            
            merged = pd.merge(
                feat_reset, label_reset,
                on=[dt_col, inst_col],
                how='inner'
            )
            logger.debug(f"  merge 后行数: {len(merged)}")
            
            if len(merged) == 0:
                raise ValueError(
                    f"因子数据和标签数据无法对齐。"
                    f"features: {len(features_df)} 行, index names={list(features_df.index.names)}; "
                    f"label: {len(label_df)} 行, index names={list(label_df.index.names)}"
                )
            
            merged = merged.set_index([dt_col, inst_col])
            merged.index.names = ['datetime', 'instrument']
            
            feature_cols = [c for c in features_df.columns if c in merged.columns]
            label_cols = [c for c in label_df.columns if c in merged.columns]
            features_df = merged[feature_cols]
            label_df = merged[label_cols]
        else:
            features_df = features_df.loc[common_index]
            label_df = label_df.loc[common_index]
        
        logger.debug(f"  数据行数: {len(features_df)}")
        
        if len(features_df) == 0:
            raise ValueError("索引对齐后数据行数为 0，无法进行回测")
        
        # 直接使用 DataHandler 构建数据集
        # 合并 feature 和 label
        combined_df = pd.concat([features_df, label_df], axis=1)
        
        # 应用预处理
        from qlib.data.dataset.processor import Fillna, ProcessInf, CSRankNorm, DropnaLabel
        
        # 分离 feature 和 label 列
        feature_cols = list(features_df.columns)
        label_cols = list(label_df.columns)
        
        # 处理 feature
        combined_df[feature_cols] = combined_df[feature_cols].fillna(0)
        combined_df[feature_cols] = combined_df[feature_cols].replace([np.inf, -np.inf], 0)
        
        # 对 feature 做 CSRankNorm
        # 使用实际的第一个 index level 名称，以防万一
        dt_level = combined_df.index.names[0] if combined_df.index.names[0] else 0
        for col in feature_cols:
            combined_df[col] = combined_df.groupby(level=dt_level)[col].transform(
                lambda x: (x.rank(pct=True) - 0.5) if len(x) > 1 else 0
            )
        
        # 处理 label - 删除 label 为 NaN 的行
        combined_df = combined_df.dropna(subset=label_cols)
        
        # 对 label 做 CSRankNorm  
        for col in label_cols:
            combined_df[col] = combined_df.groupby(level=dt_level)[col].transform(
                lambda x: (x.rank(pct=True) - 0.5) if len(x) > 1 else 0
            )
        
        logger.debug(f"  预处理后数据行数: {len(combined_df)}")
        
        # 使用多级列索引标识 feature 和 label (Qlib 标准格式)
        # 重构 DataFrame 列为 MultiIndex: (col_set, col_name)
        feature_tuples = [('feature', col) for col in feature_cols]
        label_tuples = [('label', col) for col in label_cols]
        
        combined_df_multi = combined_df.copy()
        combined_df_multi.columns = pd.MultiIndex.from_tuples(
            feature_tuples + label_tuples
        )
        
        # 构建自定义 DataHandler
        class PrecomputedDataHandler(DataHandler):
            """使用预计算数据的 DataHandler"""
            
            def __init__(self, data_df, segments):
                self._data = data_df
                self._segments = segments
            
            @property
            def data_loader(self):
                return None
            
            @property
            def instruments(self):
                # 使用 level name 或 position fallback
                try:
                    return list(self._data.index.get_level_values('instrument').unique())
                except KeyError:
                    return list(self._data.index.get_level_values(1).unique())
            
            def fetch(self, selector=None, level='datetime', col_set='feature', 
                     data_key=None, squeeze=False, proc_func=None):
                """获取数据"""
                # 根据 col_set 选择列
                if col_set in ('feature', 'label'):
                    result = self._data[col_set].copy()
                elif col_set == '__all' or col_set is None:
                    result = self._data.copy()
                else:
                    # col_set 可能是列名列表
                    if isinstance(col_set, (list, tuple)):
                        result = self._data[list(col_set)].copy()
                    else:
                        result = self._data.copy()
                
                # 过滤日期范围
                if selector is not None:
                    try:
                        dates = result.index.get_level_values('datetime')
                    except KeyError:
                        dates = result.index.get_level_values(0)
                    if isinstance(selector, tuple) and len(selector) == 2:
                        start, end = selector
                        mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
                        result = result.loc[mask]
                    elif isinstance(selector, slice):
                        start = selector.start
                        end = selector.stop
                        if start is not None and end is not None:
                            mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
                            result = result.loc[mask]
                
                if squeeze and result.shape[1] == 1:
                    result = result.iloc[:, 0]
                
                return result
            
            def get_cols(self, col_set='feature'):
                """获取列名"""
                if col_set in self._data.columns.get_level_values(0):
                    return list(self._data[col_set].columns)
                return list(self._data.columns.get_level_values(1))
            
            def setup_data(self, **kwargs):
                pass
            
            def config(self, **kwargs):
                pass
        
        # 创建 handler
        handler = PrecomputedDataHandler(combined_df_multi, dataset_config['segments'])
        
        # 创建数据集
        dataset = DatasetH(
            handler=handler,
            segments=dataset_config['segments']
        )
        
        logger.debug(f"  自定义因子模式: {len(feature_cols)} 个因子, {len(combined_df)} 行, 训练集={dataset_config['segments']['train']}")
        
        return dataset
    
    def _compute_label(self, label_expr: str) -> pd.DataFrame:
        """
        计算标签
        
        使用 Qlib 原生方式计算标签（因为标签需要向前看）
        """
        from qlib.data import D
        
        data_config = self.config['data']
        
        logger.debug(f"  标签表达式: {label_expr}")
        
        stock_list = D.instruments(data_config['market'])
        
        # 使用 Qlib 计算标签
        label_df = D.features(
            stock_list,
            [label_expr],
            start_time=data_config['start_time'],
            end_time=data_config['end_time'],
            freq='day'
        )
        
        label_df.columns = ['LABEL0']
        
        logger.debug(f"  标签数据行数: {len(label_df)}")
        
        return label_df
    
    def _load_qlib_factors(self, factor_expressions: Dict[str, str]) -> Optional[pd.DataFrame]:
        """加载 Qlib 兼容的因子"""
        from qlib.data import D
        
        data_config = self.config['data']
        
        try:
            stock_list = D.instruments(data_config['market'])
            
            expressions = list(factor_expressions.values())
            names = list(factor_expressions.keys())
            
            df = D.features(
                stock_list,
                expressions,
                start_time=data_config['start_time'],
                end_time=data_config['end_time'],
                freq='day'
            )
            
            df.columns = names
            return df
        except Exception as e:
            logger.warning(f"加载 Qlib 因子失败: {e}")
            return None
    
    def _train_and_backtest(self, dataset, exp_name: str, rec_name: str, output_name: Optional[str] = None) -> Dict:
        """训练模型并执行回测"""
        from qlib.contrib.model.gbdt import LGBModel
        from qlib.data import D
        from qlib.workflow import R
        from qlib.workflow.record_temp import SignalRecord, SigAnaRecord
        from qlib.backtest import backtest as qlib_backtest
        from qlib.contrib.evaluate import risk_analysis
        
        model_config = self.config['model']
        backtest_config = self.config['backtest']['backtest']
        strategy_config = self.config['backtest']['strategy']
        
        metrics = {}
        
        with R.start(experiment_name=exp_name, recorder_name=rec_name):
            # 训练模型
            train_start = time.time()
            
            if model_config['type'] == 'lgb':
                model = LGBModel(**model_config['params'])
            else:
                raise ValueError(f"不支持的模型类型: {model_config['type']}")
            
            model.fit(dataset)
            print(f"[4/4] 训练 LightGBM → 完成 ({time.time()-train_start:.1f}s)")
            
            # 生成预测
            pred = model.predict(dataset)
            logger.debug(f"  预测数据形状: {pred.shape}")
            
            # 保存预测
            sr = SignalRecord(recorder=R.get_recorder(), model=model, dataset=dataset)
            sr.generate()
            
            # 计算 IC 指标
            try:
                sar = SigAnaRecord(recorder=R.get_recorder(), ana_long_short=False, ann_scaler=252)
                sar.generate()
                
                recorder = R.get_recorder()
                try:
                    ic_series = recorder.load_object("sig_analysis/ic.pkl")
                    ric_series = recorder.load_object("sig_analysis/ric.pkl")
                    
                    if isinstance(ic_series, pd.Series) and len(ic_series) > 0:
                        metrics['IC'] = float(ic_series.mean())
                        metrics['ICIR'] = float(ic_series.mean() / ic_series.std()) if ic_series.std() > 0 else 0.0
                    
                    if isinstance(ric_series, pd.Series) and len(ric_series) > 0:
                        metrics['Rank IC'] = float(ric_series.mean())
                        metrics['Rank ICIR'] = float(ric_series.mean() / ric_series.std()) if ric_series.std() > 0 else 0.0
                    
                    print(f"  IC={metrics.get('IC', 0):.6f}, ICIR={metrics.get('ICIR', 0):.6f}, "
                          f"Rank IC={metrics.get('Rank IC', 0):.6f}, Rank ICIR={metrics.get('Rank ICIR', 0):.6f}")
                except Exception as e:
                    logger.warning(f"无法读取 IC 结果: {e}")
            except Exception as e:
                logger.warning(f"IC 分析失败: {e}")
            
            # 执行组合回测
            try:
                bt_start = time.time()
                
                market = self.config['data']['market']
                instruments = D.instruments(market)
                stock_list = D.list_instruments(
                    instruments,
                    start_time=backtest_config['start_time'],
                    end_time=backtest_config['end_time'],
                    as_list=True
                )
                logger.debug(f"  股票数量: {len(stock_list)}")
                
                if len(stock_list) < 10:
                    logger.warning(f"股票池过小 ({len(stock_list)} 只)，结果可能不可信")
                
                # 过滤价格异常的股票信号
                try:
                    price_data = D.features(
                        stock_list,
                        ['$close'],
                        start_time=backtest_config['start_time'],
                        end_time=backtest_config['end_time'],
                        freq='day'
                    )
                    invalid_mask = (price_data['$close'] == 0) | (price_data['$close'].isna())
                    invalid_count = invalid_mask.sum()
                    
                    if invalid_count > 0:
                        logger.debug(f"  发现 {invalid_count} 条价格为0/NaN的记录")
                        if isinstance(pred, pd.Series):
                            invalid_indices = invalid_mask[invalid_mask].index
                            invalid_set = set()
                            for idx in invalid_indices:
                                instrument, datetime = idx
                                invalid_set.add((datetime, instrument))
                            
                            filtered_count = 0
                            for idx in pred.index:
                                if idx in invalid_set:
                                    pred.loc[idx] = np.nan
                                    filtered_count += 1
                            
                            if filtered_count > 0:
                                logger.debug(f"  已过滤 {filtered_count} 条价格异常信号")
                except Exception as filter_err:
                    logger.warning(f"价格过滤失败: {filter_err}")
                
                portfolio_metric_dict, indicator_dict = qlib_backtest(
                    executor={
                        "class": "SimulatorExecutor",
                        "module_path": "qlib.backtest.executor",
                        "kwargs": {
                            "time_per_step": "day",
                            "generate_portfolio_metrics": True,
                            "verbose": False,
                            "indicator_config": {"show_indicator": False}
                        }
                    },
                    strategy={
                        "class": strategy_config['class'],
                        "module_path": strategy_config['module_path'],
                        "kwargs": {
                            "signal": pred,
                            "topk": strategy_config['kwargs']['topk'],
                            "n_drop": strategy_config['kwargs']['n_drop']
                        }
                    },
                    start_time=backtest_config['start_time'],
                    end_time=backtest_config['end_time'],
                    account=backtest_config['account'],
                    benchmark=backtest_config['benchmark'],
                    exchange_kwargs={
                        "codes": stock_list,
                        **backtest_config['exchange_kwargs']
                    }
                )
                
                print(f"  组合回测 → 完成 ({time.time()-bt_start:.1f}s)")
                
                # 提取组合指标
                if portfolio_metric_dict and "1day" in portfolio_metric_dict:
                    report_df, positions_df = portfolio_metric_dict["1day"]
                    
                    if isinstance(report_df, pd.DataFrame) and 'return' in report_df.columns:
                        portfolio_return = report_df['return'].replace([np.inf, -np.inf], np.nan).fillna(0)
                        bench_return = report_df['bench'].replace([np.inf, -np.inf], np.nan).fillna(0) if 'bench' in report_df.columns else 0
                        cost = report_df['cost'].replace([np.inf, -np.inf], np.nan).fillna(0) if 'cost' in report_df.columns else 0
                        
                        excess_return_with_cost = portfolio_return - bench_return - cost
                        excess_return_with_cost = excess_return_with_cost.dropna()
                        
                        if len(excess_return_with_cost) > 0:
                            # 保存每日数据到 CSV
                            try:
                                daily_df = report_df.copy()
                                daily_df['excess_return'] = excess_return_with_cost
                                
                                output_dir = Path(self.config['experiment'].get('output_dir', './backtest_v2_results'))
                                output_dir.mkdir(parents=True, exist_ok=True)
                                
                                # 使用 output_name 或 experiment_name
                                file_prefix = output_name if output_name else exp_name
                                csv_path = output_dir / f"{file_prefix}_cumulative_excess.csv"
                                
                                # 只保留需要的列并重命名
                                save_df = daily_df[['excess_return']].copy()
                                save_df.columns = ['daily_excess_return']
                                save_df['cumulative_excess_return'] = save_df['daily_excess_return'].cumsum()
                                
                                save_df.index.name = 'date'
                                save_df.to_csv(csv_path)
                                logger.debug(f"  每日累计超额收益已保存: {csv_path}")
                            except Exception as csv_err:
                                logger.warning(f"保存每日CSV失败: {csv_err}")

                            analysis = risk_analysis(excess_return_with_cost)
                            
                            if isinstance(analysis, pd.DataFrame):
                                analysis = analysis['risk'] if 'risk' in analysis.columns else analysis.iloc[:, 0]
                            
                            ann_ret = float(analysis.get('annualized_return', 0))
                            info_ratio = float(analysis.get('information_ratio', 0))
                            max_dd = float(analysis.get('max_drawdown', 0))
                            
                            if not np.isnan(ann_ret) and not np.isinf(ann_ret):
                                metrics['annualized_return'] = ann_ret
                            if not np.isnan(info_ratio) and not np.isinf(info_ratio):
                                metrics['information_ratio'] = info_ratio
                            if not np.isnan(max_dd) and not np.isinf(max_dd):
                                metrics['max_drawdown'] = max_dd
                            
                            if max_dd != 0 and not np.isnan(ann_ret) and not np.isinf(ann_ret):
                                calmar = ann_ret / abs(max_dd)
                                if not np.isnan(calmar) and not np.isinf(calmar):
                                    metrics['calmar_ratio'] = calmar
                            
            except Exception as e:
                logger.warning(f"组合回测失败: {e}")
                import traceback
                traceback.print_exc()
        
        return metrics
    
    def _print_results(self, metrics: Dict, total_time: float):
        """打印结果摘要"""
        def _f(val, fmt='.6f'):
            return format(val, fmt) if isinstance(val, (int, float)) else 'N/A'

        print(f"\n{'='*50}")
        print("回测结果")
        print(f"{'='*50}")
        
        print("【IC 指标】")
        print(f"  IC: {_f(metrics.get('IC'))}  ICIR: {_f(metrics.get('ICIR'))}")
        print(f"  Rank IC: {_f(metrics.get('Rank IC'))}  Rank ICIR: {_f(metrics.get('Rank ICIR'))}")
        print("【策略指标】")
        print(f"  年化收益: {_f(metrics.get('annualized_return'), '.4f')}  最大回撤: {_f(metrics.get('max_drawdown'), '.4f')}")
        print(f"  信息比率: {_f(metrics.get('information_ratio'), '.4f')}  Calmar: {_f(metrics.get('calmar_ratio'), '.4f')}")
        print(f"总耗时: {total_time:.1f} 秒")
        print(f"{'='*50}")
    
    def _save_results(self, metrics: Dict, exp_name: str, 
                     factor_source: str, num_factors: int, elapsed: float,
                     output_name: Optional[str] = None):
        """保存结果"""
        output_dir = Path(self.config['experiment'].get('output_dir', './backtest_v2_results'))
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用自定义输出名称或配置中的默认名称
        if output_name:
            output_file = f"{output_name}_backtest_metrics.json"
        else:
            output_file = self.config['experiment']['output_metrics_file']
        output_path = output_dir / output_file
        
        result_data = {
            "experiment_name": exp_name,
            "factor_source": factor_source,
            "num_factors": num_factors,
            "metrics": metrics,
            "config": {
                "data_range": f"{self.config['data']['start_time']} ~ {self.config['data']['end_time']}",
                "test_range": f"{self.config['dataset']['segments']['test'][0]} ~ {self.config['dataset']['segments']['test'][1]}",
                "backtest_range": f"{self.config['backtest']['backtest']['start_time']} ~ {self.config['backtest']['backtest']['end_time']}",
                "market": self.config['data']['market'],
                "benchmark": self.config['backtest']['backtest']['benchmark']
            },
            "elapsed_seconds": elapsed
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"结果已保存: {output_path}")
        
        # 同时追加到汇总文件
        summary_file = output_dir / "batch_summary.json"
        summary_data = []
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
            except:
                summary_data = []
        
        # 添加当前结果到汇总
        ann_ret = metrics.get('annualized_return')
        mdd = metrics.get('max_drawdown')
        calmar_ratio = None
        if ann_ret is not None and mdd is not None and mdd != 0:
            calmar_ratio = ann_ret / abs(mdd)
        
        summary_entry = {
            "name": output_name or exp_name,
            "num_factors": num_factors,
            "IC": metrics.get('IC'),
            "ICIR": metrics.get('ICIR'),
            "Rank_IC": metrics.get('Rank IC'),
            "Rank_ICIR": metrics.get('Rank ICIR'),
            "annualized_return": ann_ret,
            "information_ratio": metrics.get('information_ratio'),
            "max_drawdown": mdd,
            "calmar_ratio": calmar_ratio,
            "elapsed_seconds": elapsed
        }
        summary_data.append(summary_entry)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"已追加到汇总: {summary_file}")
