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

# 添加项目路径
project_root = Path(__file__).parent.parent
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
            
        import qlib
        
        provider_uri = self.config['data']['provider_uri']
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
        
        print(f"\n{'='*70}")
        print(f"🚀 开始回测: {exp_name}")
        if factor_json:
            print(f"📁 因子库: {factor_json[0]}")
        print(f"{'='*70}\n")
        
        # 1. 加载因子
        print("📊 第一步：加载因子...")
        factor_expressions, custom_factors = self._load_factors()
        print(f"  ✓ Qlib 兼容因子: {len(factor_expressions)} 个")
        print(f"  ✓ 需要计算的自定义因子: {len(custom_factors)} 个")
        
        # 2. 计算自定义因子（如果有）
        computed_factors = None
        if custom_factors:
            print("\n🔧 第二步：计算自定义因子...")
            computed_factors = self._compute_custom_factors(custom_factors)
            if computed_factors is not None and not computed_factors.empty:
                print(f"  ✓ 成功计算 {len(computed_factors.columns)} 个因子")
        
        # 3. 创建数据集
        print("\n📈 第三步：创建数据集...")
        dataset = self._create_dataset(factor_expressions, computed_factors)
        
        # 4. 训练模型并回测
        print("\n🤖 第四步：训练模型并执行回测...")
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
        """
        from .custom_factor_calculator import CustomFactorCalculator, get_qlib_stock_data
        from pathlib import Path
        
        # 获取数据
        print("  获取股票数据...")
        data_df = get_qlib_stock_data(self.config)
        
        if data_df is None or data_df.empty:
            logger.error("无法获取股票数据")
            return None
        
        logger.info(f"  ✓ 加载股票数据: {len(data_df)} 条记录")
        
        # 获取缓存配置
        llm_config = self.config.get('llm', {})
        cache_dir = llm_config.get('cache_dir')
        if cache_dir:
            cache_dir = Path(cache_dir)
        
        # 是否自动从主程序日志提取缓存
        auto_extract = llm_config.get('auto_extract_cache', True)
        
        # 创建计算器 (传递缓存目录和自动提取配置)
        calculator = CustomFactorCalculator(data_df, cache_dir=cache_dir, auto_extract_cache=auto_extract)
        
        # 计算因子 (会优先检查缓存，缓存不存在会自动提取)
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
            # 尝试使用原始数据的索引
            if isinstance(data_df.index, pd.MultiIndex):
                result_df.index = data_df.index
        
        logger.info(f"  ✓ 因子计算完成: {len(result_df.columns)} 个因子, {len(result_df)} 行数据")
        
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
                    logger.info(f"  检测到预计算因子: {len(computed_factors.columns)} 个因子, {len(computed_factors)} 行数据")
                else:
                    logger.warning(f"  预计算因子 DataFrame 为空: {computed_factors.shape}")
            else:
                logger.warning(f"  预计算因子类型不正确: {type(computed_factors)}")
        
        # 如果有计算好的自定义因子，优先使用自定义因子模式
        if has_computed_factors:
            print("  使用自定义因子模式 (预计算因子值)...")
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
        
        print(f"  训练集: {dataset_config['segments']['train']}")
        print(f"  验证集: {dataset_config['segments']['valid']}")
        print(f"  测试集: {dataset_config['segments']['test']}")
        print(f"  因子数量: {len(expressions)}")
        
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
        
        print(f"  计算因子数量: {len(computed_factors.columns)}")
        
        # 计算标签
        print("  计算标签...")
        label_expr = dataset_config['label']
        label_df = self._compute_label(label_expr)
        
        # 合并 Qlib 兼容因子 (如果有)
        all_feature_dfs = [computed_factors]
        
        if factor_expressions:
            print(f"  加载 {len(factor_expressions)} 个 Qlib 兼容因子...")
            qlib_factors = self._load_qlib_factors(factor_expressions)
            if qlib_factors is not None and not qlib_factors.empty:
                all_feature_dfs.append(qlib_factors)
        
        # 合并所有因子
        features_df = pd.concat(all_feature_dfs, axis=1)
        
        # 去除重复列
        features_df = features_df.loc[:, ~features_df.columns.duplicated()]
        
        print(f"  总因子数量: {len(features_df.columns)}")
        
        # 合并特征和标签
        # 确保索引对齐
        common_index = features_df.index.intersection(label_df.index)
        features_df = features_df.loc[common_index]
        label_df = label_df.loc[common_index]
        
        print(f"  数据行数: {len(features_df)}")
        
        # 直接使用 DataHandler 构建数据集
        # 合并 feature 和 label
        combined_df = pd.concat([features_df, label_df], axis=1)
        
        # 应用预处理
        from qlib.data.dataset.processor import Fillna, ProcessInf, CSRankNorm, DropnaLabel
        
        print("  应用数据预处理...")
        
        # 分离 feature 和 label 列
        feature_cols = list(features_df.columns)
        label_cols = list(label_df.columns)
        
        # 处理 feature
        combined_df[feature_cols] = combined_df[feature_cols].fillna(0)
        combined_df[feature_cols] = combined_df[feature_cols].replace([np.inf, -np.inf], 0)
        
        # 对 feature 做 CSRankNorm
        for col in feature_cols:
            combined_df[col] = combined_df.groupby(level='datetime')[col].transform(
                lambda x: (x.rank(pct=True) - 0.5) if len(x) > 1 else 0
            )
        
        # 处理 label - 删除 label 为 NaN 的行
        combined_df = combined_df.dropna(subset=label_cols)
        
        # 对 label 做 CSRankNorm  
        for col in label_cols:
            combined_df[col] = combined_df.groupby(level='datetime')[col].transform(
                lambda x: (x.rank(pct=True) - 0.5) if len(x) > 1 else 0
            )
        
        print(f"  预处理后数据行数: {len(combined_df)}")
        
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
                return list(self._data.index.get_level_values('instrument').unique())
            
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
                    if isinstance(selector, tuple) and len(selector) == 2:
                        start, end = selector
                        dates = result.index.get_level_values('datetime')
                        mask = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
                        result = result.loc[mask]
                    elif isinstance(selector, slice):
                        dates = result.index.get_level_values('datetime')
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
        
        print(f"  训练集: {dataset_config['segments']['train']}")
        print(f"  验证集: {dataset_config['segments']['valid']}")
        print(f"  测试集: {dataset_config['segments']['test']}")
        
        return dataset
    
    def _compute_label(self, label_expr: str) -> pd.DataFrame:
        """
        计算标签
        
        使用 Qlib 原生方式计算标签（因为标签需要向前看）
        """
        from qlib.data import D
        
        data_config = self.config['data']
        
        print(f"  标签表达式: {label_expr}")
        
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
        
        print(f"  标签数据行数: {len(label_df)}")
        
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
            print("  训练 LightGBM 模型...")
            train_start = time.time()
            
            if model_config['type'] == 'lgb':
                model = LGBModel(**model_config['params'])
            else:
                raise ValueError(f"不支持的模型类型: {model_config['type']}")
            
            model.fit(dataset)
            print(f"  ✓ 模型训练完成 (耗时: {time.time()-train_start:.2f}秒)")
            
            # 生成预测
            print("  生成预测...")
            pred = model.predict(dataset)
            print(f"  ✓ 预测数据形状: {pred.shape}")
            
            # 保存预测
            sr = SignalRecord(recorder=R.get_recorder(), model=model, dataset=dataset)
            sr.generate()
            
            # 计算 IC 指标
            print("  计算 IC 指标...")
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
                    
                    print(f"  ✓ IC={metrics.get('IC', 0):.6f}, ICIR={metrics.get('ICIR', 0):.6f}")
                    print(f"  ✓ Rank IC={metrics.get('Rank IC', 0):.6f}, Rank ICIR={metrics.get('Rank ICIR', 0):.6f}")
                except Exception as e:
                    logger.warning(f"无法读取 IC 结果: {e}")
            except Exception as e:
                logger.warning(f"IC 分析失败: {e}")
            
            # 执行组合回测
            print("  执行组合回测...")
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
                print(f"  ✓ 股票数量: {len(stock_list)}")
                
                if len(stock_list) < 10:
                    logger.warning(f"⚠️  警告: 股票池过小 ({len(stock_list)} 只股票)，回测结果可能不可信！")
                
                # 过滤价格异常的股票信号
                print("  检查并过滤价格异常数据...")
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
                        print(f"  ⚠️ 发现 {invalid_count} 条价格为0/NaN的记录")
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
                                print(f"  ✓ 已将 {filtered_count} 条价格异常的预测信号设为NaN")
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
                
                print(f"  ✓ 组合回测完成 (耗时: {time.time()-bt_start:.2f}秒)")
                
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
                                print(f"  ✓ 每日累计超额收益已保存: {csv_path}")
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
                            
                            print(f"  ✓ 提取了组合策略指标")
                            
            except Exception as e:
                logger.warning(f"组合回测失败: {e}")
                import traceback
                traceback.print_exc()
        
        return metrics
    
    def _print_results(self, metrics: Dict, total_time: float):
        """打印结果"""
        print(f"\n{'='*70}")
        print("📈 回测结果:")
        print(f"{'='*70}")
        
        print("\n【IC 指标】")
        print(f"  IC:               {metrics.get('IC', 'N/A'):.6f}" if isinstance(metrics.get('IC'), float) else f"  IC:               {metrics.get('IC', 'N/A')}")
        print(f"  ICIR:             {metrics.get('ICIR', 'N/A'):.6f}" if isinstance(metrics.get('ICIR'), float) else f"  ICIR:             {metrics.get('ICIR', 'N/A')}")
        print(f"  Rank IC:          {metrics.get('Rank IC', 'N/A'):.6f}" if isinstance(metrics.get('Rank IC'), float) else f"  Rank IC:          {metrics.get('Rank IC', 'N/A')}")
        print(f"  Rank ICIR:        {metrics.get('Rank ICIR', 'N/A'):.6f}" if isinstance(metrics.get('Rank ICIR'), float) else f"  Rank ICIR:        {metrics.get('Rank ICIR', 'N/A')}")
        
        print("\n【策略指标】")
        print(f"  年化收益:         {metrics.get('annualized_return', 'N/A'):.4f}" if isinstance(metrics.get('annualized_return'), float) else f"  年化收益:         {metrics.get('annualized_return', 'N/A')}")
        print(f"  信息比率:         {metrics.get('information_ratio', 'N/A'):.4f}" if isinstance(metrics.get('information_ratio'), float) else f"  信息比率:         {metrics.get('information_ratio', 'N/A')}")
        print(f"  最大回撤:         {metrics.get('max_drawdown', 'N/A'):.4f}" if isinstance(metrics.get('max_drawdown'), float) else f"  最大回撤:         {metrics.get('max_drawdown', 'N/A')}")
        print(f"  卡尔玛比率:       {metrics.get('calmar_ratio', 'N/A'):.4f}" if isinstance(metrics.get('calmar_ratio'), float) else f"  卡尔玛比率:       {metrics.get('calmar_ratio', 'N/A')}")
        
        print(f"\n⏱️  总耗时: {total_time:.2f} 秒")
        print(f"{'='*70}\n")
    
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
        
        print(f"✓ 结果已保存到: {output_path}\n")
        
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
        
        print(f"✓ 已追加到汇总: {summary_file}")
