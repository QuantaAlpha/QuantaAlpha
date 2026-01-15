#!/usr/bin/env python3
"""
统一因子库管理器
自动收集和保存所有实验挖出的因子到统一的JSON文件
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from alphaagent.log import logger


class FactorLibraryManager:
    """因子库管理器"""
    
    def __init__(self, library_path: str = "all_factors_library.json"):
        """
        初始化因子库管理器
        
        Args:
            library_path: 因子库JSON文件路径
        """
        self.library_path = Path(library_path)
        self.library = self._load_library()
    
    def _load_library(self) -> Dict:
        """加载因子库"""
        if self.library_path.exists():
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    library = json.load(f)
                logger.info(f"加载因子库: {self.library_path}, 当前有 {len(library.get('factors', {}))} 个因子")
                return library
            except Exception as e:
                logger.warning(f"加载因子库失败: {e}, 创建新库")
        
        # 创建新的因子库
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_factors": 0,
                "version": "1.0"
            },
            "factors": {}
        }
    
    def _save_library(self):
        """保存因子库到文件"""
        try:
            self.library["metadata"]["last_updated"] = datetime.now().isoformat()
            self.library["metadata"]["total_factors"] = len(self.library["factors"])
            
            # 创建备份
            if self.library_path.exists():
                backup_path = self.library_path.with_suffix('.json.bak')
                import shutil
                shutil.copy(self.library_path, backup_path)
            
            # 保存新库
            with open(self.library_path, 'w', encoding='utf-8') as f:
                json.dump(self.library, f, ensure_ascii=False, indent=2)
            
            logger.info(f"保存因子库: {self.library_path}, 共 {len(self.library['factors'])} 个因子")
        except Exception as e:
            logger.error(f"保存因子库失败: {e}")
            raise
    
    def _generate_factor_id(self, factor_name: str, factor_expression: str) -> str:
        """生成因子唯一ID（基于名称和表达式的哈希）"""
        content = f"{factor_name}:{factor_expression}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def _extract_ic_info(self, result: Any) -> Dict[str, Optional[float]]:
        """从回测结果中提取IC信息和所有回测指标"""
        ic_info = {
            "IC": None,
            "ICIR": None,
            "RankIC": None,
            "RankICIR": None,
            "annualized_return": None,
            "information_ratio": None,
            "max_drawdown": None
        }
        
        if result is None:
            return ic_info
        
        try:
            index_mapping = {
                'IC': ['IC', 'ic'],
                'ICIR': ['ICIR', 'icir'],
                'RankIC': ['RankIC', 'Rank IC', 'rank_ic', 'rankic'],
                'RankICIR': ['RankICIR', 'Rank ICIR', 'rank_icir', 'rankicir'],
                'annualized_return': [
                    '1day.excess_return_without_cost.annualized_return',
                    '1day.excess_return_with_cost.annualized_return',
                    'annualized_return',
                    'Annualized Return'
                ],
                'information_ratio': [
                    '1day.excess_return_without_cost.information_ratio',
                    '1day.excess_return_with_cost.information_ratio',
                    'information_ratio',
                    'Information Ratio'
                ],
                'max_drawdown': [
                    '1day.excess_return_without_cost.max_drawdown',
                    '1day.excess_return_with_cost.max_drawdown',
                    'max_drawdown',
                    'Max Drawdown'
                ]
            }

            # 如果result是DataFrame
            if isinstance(result, pd.DataFrame):
                # 获取列名（通常是'0'）
                col_name = result.columns[0] if len(result.columns) > 0 else 0
                
                # 遍历所有索引，尝试匹配
                for target_key, possible_names in index_mapping.items():
                    for idx_name in possible_names:
                        # 精确匹配
                        if idx_name in result.index:
                            try:
                                value = result.loc[idx_name, col_name] if col_name in result.columns else result.loc[idx_name]
                                if pd.notna(value):
                                    ic_info[target_key] = float(value)
                                    break
                            except (KeyError, IndexError):
                                continue
                        # 部分匹配（大小写不敏感）
                        else:
                            matching_indices = [idx for idx in result.index if str(idx).lower() == str(idx_name).lower()]
                            if matching_indices:
                                try:
                                    value = result.loc[matching_indices[0], col_name] if col_name in result.columns else result.loc[matching_indices[0]]
                                    if pd.notna(value):
                                        ic_info[target_key] = float(value)
                                        break
                                except (KeyError, IndexError):
                                    continue

            # 如果result是Series
            elif isinstance(result, pd.Series):
                for target_key, possible_names in index_mapping.items():
                    for idx_name in possible_names:
                        if idx_name in result.index:
                            value = result[idx_name]
                            if pd.notna(value):
                                ic_info[target_key] = float(value)
                                break
                        else:
                            matching_indices = [idx for idx in result.index if str(idx).lower() == str(idx_name).lower()]
                            if matching_indices:
                                value = result[matching_indices[0]]
                                if pd.notna(value):
                                    ic_info[target_key] = float(value)
                                    break
        except Exception as e:
            logger.warning(f"提取回测指标失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return ic_info
    
    def _judge_factor_quality(self, rank_ic: Optional[float], max_correlation: Optional[float] = None) -> str:
        """
        判断因子质量
        
        标准:
        当前简化标准（仅根据 RankIC 判断）:
        - RankIC > 0.01 -> high_quality
        - 0 < RankIC <= 0.01 且不为 None -> valid
        - rank_ic 为 None 或解析失败 或小于等于0 -> Poor
        """
        if rank_ic is None:
            return "Poor"
        
        try:
            rank_ic_val = float(rank_ic)
            # 只要 RankIC 大于 0.01，就认为是有效因子
            if rank_ic_val > 0.01:
                return "high_quality"
            elif rank_ic_val > 0:
                return "valid"
            else:
                return "Poor"
        except Exception as e:
            logger.warning(f"判断因子质量失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return "Poor"
    
    def add_factor(
        self,
        factor_name: str,
        factor_expression: str,
        experiment_id: str,
        round_number: int,
        hypothesis: Optional[str] = None,
        factor_description: Optional[str] = None,
        backtest_result: Any = None,
        is_sota: bool = False,
        max_correlation_with_alpha158: Optional[float] = None,
        initial_direction: Optional[str] = None,
        factor_implementation_code: Optional[str] = None,
        user_initial_direction: Optional[str] = None,
        planning_direction: Optional[str] = None,
    ) -> str:
        """
        添加因子到库中
        
        Args:
            factor_name: 因子名称
            factor_expression: 因子表达式
            experiment_id: 实验ID
            round_number: 轮次
            hypothesis: 市场假设
            factor_description: 因子描述
            backtest_result: 回测结果
            is_sota: 是否为SOTA因子
            max_correlation_with_alpha158: 与Alpha158的最大相关性
            initial_direction: 初始方向（如"均值回归"）
            
        Returns:
            因子ID
        """
        # 生成因子ID
        factor_id = self._generate_factor_id(factor_name, factor_expression)
        
        # 提取回测指标
        ic_info = self._extract_ic_info(backtest_result)
        
        # 判断因子质量
        quality = self._judge_factor_quality(
            ic_info.get("RankIC"),
            max_correlation_with_alpha158
        )
        
        # 构建因子信息
        factor_info = {
            "factor_id": factor_id,
            "factor_name": factor_name,
            "factor_expression": factor_expression,
            "factor_implementation_code": factor_implementation_code or "",
            "factor_description": factor_description or "",
            "experiment_id": experiment_id,
            "round_number": round_number,
            "hypothesis": hypothesis or "",
            # planning 分支方向（如果启用 planning 则为分支方向，否则等同用户输入）
            "initial_direction": initial_direction or "",
            # 用户最初输入（始终记录）
            "user_initial_direction": user_initial_direction or "",
            # 显式保存 planning 方向字段，方便后续区分
            "planning_direction": planning_direction or "",
            "is_sota": is_sota,
            "quality": quality,
            "backtest_metrics": {
                "IC": ic_info.get("IC"),
                "ICIR": ic_info.get("ICIR"),
                "RankIC": ic_info.get("RankIC"),
                "RankICIR": ic_info.get("RankICIR"),
                "annualized_return": ic_info.get("annualized_return"),
                "information_ratio": ic_info.get("information_ratio"),
                "max_drawdown": ic_info.get("max_drawdown")
            },
            "max_correlation_with_alpha158": max_correlation_with_alpha158,
            "added_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # 如果因子已存在，更新信息（保留最早的added_at）
        if factor_id in self.library["factors"]:
            existing_factor = self.library["factors"][factor_id]
            factor_info["added_at"] = existing_factor.get("added_at", factor_info["added_at"])
            logger.info(f"更新已存在的因子: {factor_name} (ID: {factor_id})")
        else:
            logger.info(f"添加新因子: {factor_name} (ID: {factor_id})")
        
        # 保存到库中
        self.library["factors"][factor_id] = factor_info
        
        # 保存到文件
        self._save_library()
        
        return factor_id
    
    def add_factors_from_experiment(
        self,
        experiment: Any,
        experiment_id: str,
        round_number: int,
        hypothesis: Optional[str] = None,
        feedback: Optional[Any] = None,
        initial_direction: Optional[str] = None,
        user_initial_direction: Optional[str] = None,
        planning_direction: Optional[str] = None,
    ):
        """
        从实验对象中添加所有因子
        
        Args:
            experiment: 实验对象（QlibFactorExperiment）
            experiment_id: 实验ID
            round_number: 轮次
            hypothesis: 市场假设
            feedback: 反馈对象（用于判断is_sota）
            initial_direction: 初始方向（如"均值回归"）
        """
        if not hasattr(experiment, 'sub_tasks'):
            logger.warning(f"实验 {experiment_id} 没有sub_tasks")
            return
        
        # 获取回测结果
        backtest_result = getattr(experiment, 'result', None)
        
        # 判断是否为SOTA
        is_sota = False
        if feedback is not None and hasattr(feedback, 'decision'):
            is_sota = feedback.decision
        
        # 遍历所有因子任务
        for idx, task in enumerate(experiment.sub_tasks):
            if not hasattr(task, 'factor_name'):
                continue
            
            factor_name = task.factor_name
            factor_expression = getattr(task, 'factor_expression', '')
            factor_description = getattr(task, 'factor_description', '')
            
            # 尝试获取因子实现代码
            factor_code = ""
            try:
                # 从 workspace 获取代码
                if hasattr(experiment, 'sub_workspace_list') and idx < len(experiment.sub_workspace_list):
                    workspace = experiment.sub_workspace_list[idx]
                    if workspace and hasattr(workspace, 'code_dict') and workspace.code_dict:
                        factor_code = workspace.code_dict.get('factor.py', '')
            except Exception as e:
                logger.debug(f"无法获取因子 {factor_name} 的代码: {e}")
            
            # 添加因子
            self.add_factor(
                factor_name=factor_name,
                factor_expression=factor_expression,
                factor_implementation_code=factor_code,
                experiment_id=experiment_id,
                round_number=round_number,
                hypothesis=hypothesis,
                factor_description=factor_description,
                backtest_result=backtest_result,
                is_sota=is_sota,
                initial_direction=initial_direction,
                user_initial_direction=user_initial_direction,
                planning_direction=planning_direction,
            )
    
    def get_factors_by_quality(self, quality: str) -> List[Dict]:
        """根据质量获取因子列表"""
        return [
            factor for factor in self.library["factors"].values()
            if factor.get("quality") == quality
        ]
    
    def get_sota_factors(self) -> List[Dict]:
        """获取所有SOTA因子"""
        return [
            factor for factor in self.library["factors"].values()
            if factor.get("is_sota", False)
        ]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        factors = list(self.library["factors"].values())
        
        return {
            "total_factors": len(factors),
            "high_quality": len([f for f in factors if f.get("quality") == "high_quality"]),
            "valid": len([f for f in factors if f.get("quality") == "valid"]),
            "poor": len([f for f in factors if f.get("quality") == "poor"]),
            "unknown": len([f for f in factors if f.get("quality") == "unknown"]),
            "sota_factors": len([f for f in factors if f.get("is_sota", False)]),
            "experiments": len(set(f.get("experiment_id", "") for f in factors))
        }


# 全局实例
_manager = None

def get_manager(library_path: str = "all_factors_library.json") -> FactorLibraryManager:
    """获取全局因子库管理器实例"""
    global _manager
    if _manager is None:
        _manager = FactorLibraryManager(library_path)
    return _manager

