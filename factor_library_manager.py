"""
Factor Library Manager - 因子库管理器

统一管理和存储所有实验产生的因子，支持：
- 因子去重（基于表达式）
- 元数据追踪（实验ID、轮次、进化阶段等）
- JSON 格式持久化
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from quantaalpha.log import logger


class FactorLibraryManager:
    """
    因子库管理器
    
    用于统一管理和存储所有实验产生的因子。
    """
    
    def __init__(self, library_path: str = "all_factors_library.json"):
        """
        初始化因子库管理器
        
        Args:
            library_path: 因子库 JSON 文件路径
        """
        self.library_path = Path(library_path)
        self.factors: Dict[str, Dict[str, Any]] = {}
        self._load_library()
    
    def _load_library(self):
        """加载现有因子库"""
        if self.library_path.exists():
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.factors = data.get("factors", {})
                    logger.info(f"加载因子库: {len(self.factors)} 个因子")
            except Exception as e:
                logger.warning(f"加载因子库失败: {e}，使用空库")
                self.factors = {}
        else:
            self.factors = {}
    
    def _save_library(self):
        """保存因子库到文件"""
        data = {
            "metadata": {
                "total_factors": len(self.factors),
                "last_updated": datetime.now().isoformat(),
            },
            "factors": self.factors
        }
        
        # 确保目录存在
        self.library_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _generate_factor_id(self, expression: str) -> str:
        """
        根据因子表达式生成唯一ID
        
        Args:
            expression: 因子表达式
            
        Returns:
            因子ID（基于表达式的哈希）
        """
        # 移除空白字符后计算哈希
        normalized = expression.strip().replace(" ", "")
        hash_obj = hashlib.md5(normalized.encode('utf-8'))
        return f"factor_{hash_obj.hexdigest()[:12]}"
    
    def add_factor(
        self,
        factor_name: str,
        factor_expression: str,
        factor_description: str = "",
        hypothesis: str = "",
        experiment_id: str = "",
        round_number: int = 0,
        backtest_metrics: Dict[str, float] = None,
        initial_direction: str = "",
        user_initial_direction: str = "",
        planning_direction: str = "",
        evolution_phase: str = "original",
        trajectory_id: str = "",
        parent_trajectory_ids: List[str] = None,
        **kwargs
    ) -> str:
        """
        添加因子到库
        
        Args:
            factor_name: 因子名称
            factor_expression: 因子表达式
            factor_description: 因子描述
            hypothesis: 假设文本
            experiment_id: 实验ID
            round_number: 轮次
            backtest_metrics: 回测指标
            initial_direction: 初始方向
            user_initial_direction: 用户初始方向
            planning_direction: 规划方向
            evolution_phase: 进化阶段
            trajectory_id: 轨迹ID
            parent_trajectory_ids: 父轨迹ID列表
            
        Returns:
            因子ID
        """
        factor_id = self._generate_factor_id(factor_expression)
        
        # 检查是否已存在
        if factor_id in self.factors:
            # 更新现有因子的元数据
            existing = self.factors[factor_id]
            if backtest_metrics:
                # 如果新的指标更好，更新
                old_ic = existing.get("backtest_metrics", {}).get("IC", 0)
                new_ic = backtest_metrics.get("IC", 0)
                if new_ic > old_ic:
                    existing["backtest_metrics"] = backtest_metrics
                    existing["last_updated"] = datetime.now().isoformat()
            logger.debug(f"因子已存在，更新元数据: {factor_id}")
        else:
            # 添加新因子
            self.factors[factor_id] = {
                "factor_id": factor_id,
                "factor_name": factor_name,
                "factor_expression": factor_expression,
                "factor_description": factor_description,
                "hypothesis": hypothesis,
                "experiment_id": experiment_id,
                "round_number": round_number,
                "backtest_metrics": backtest_metrics or {},
                "initial_direction": initial_direction,
                "user_initial_direction": user_initial_direction,
                "planning_direction": planning_direction,
                "evolution_phase": evolution_phase,
                "trajectory_id": trajectory_id,
                "parent_trajectory_ids": parent_trajectory_ids or [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
            }
            logger.debug(f"添加新因子: {factor_id} ({factor_name})")
        
        self._save_library()
        return factor_id
    
    def add_factors_from_experiment(
        self,
        experiment,
        experiment_id: str = "",
        round_number: int = 0,
        hypothesis: str = "",
        feedback = None,
        initial_direction: str = "",
        user_initial_direction: str = "",
        planning_direction: str = "",
        evolution_phase: str = "original",
        trajectory_id: str = "",
        parent_trajectory_ids: List[str] = None,
    ) -> List[str]:
        """
        从实验结果中提取并添加因子
        
        Args:
            experiment: 实验对象
            experiment_id: 实验ID
            round_number: 轮次
            hypothesis: 假设文本
            feedback: 反馈对象
            initial_direction: 初始方向
            user_initial_direction: 用户初始方向
            planning_direction: 规划方向
            evolution_phase: 进化阶段
            trajectory_id: 轨迹ID
            parent_trajectory_ids: 父轨迹ID列表
            
        Returns:
            添加的因子ID列表
        """
        factor_ids = []
        
        if experiment is None:
            logger.warning("实验对象为空，跳过因子提取")
            return factor_ids
        
        # 尝试从实验对象中提取因子
        sub_tasks = getattr(experiment, 'sub_tasks', []) or []
        sub_results = getattr(experiment, 'sub_results', []) or []
        
        for i, task in enumerate(sub_tasks):
            try:
                factor_name = getattr(task, 'factor_name', f'factor_{i}')
                factor_expression = getattr(task, 'factor_expression', '')
                factor_description = getattr(task, 'factor_description', '')
                
                if not factor_expression:
                    continue
                
                # 尝试获取回测指标
                backtest_metrics = {}
                if i < len(sub_results) and sub_results[i] is not None:
                    result = sub_results[i]
                    if hasattr(result, 'ic'):
                        backtest_metrics['IC'] = float(result.ic) if result.ic else 0
                    if hasattr(result, 'icir'):
                        backtest_metrics['ICIR'] = float(result.icir) if result.icir else 0
                    if hasattr(result, 'rank_ic'):
                        backtest_metrics['RankIC'] = float(result.rank_ic) if result.rank_ic else 0
                    if hasattr(result, 'rank_icir'):
                        backtest_metrics['RankICIR'] = float(result.rank_icir) if result.rank_icir else 0
                
                factor_id = self.add_factor(
                    factor_name=factor_name,
                    factor_expression=factor_expression,
                    factor_description=factor_description,
                    hypothesis=hypothesis,
                    experiment_id=experiment_id,
                    round_number=round_number,
                    backtest_metrics=backtest_metrics,
                    initial_direction=initial_direction,
                    user_initial_direction=user_initial_direction,
                    planning_direction=planning_direction,
                    evolution_phase=evolution_phase,
                    trajectory_id=trajectory_id,
                    parent_trajectory_ids=parent_trajectory_ids,
                )
                factor_ids.append(factor_id)
                
            except Exception as e:
                logger.warning(f"提取因子失败: {e}")
                continue
        
        logger.info(f"从实验中提取了 {len(factor_ids)} 个因子")
        return factor_ids
    
    def get_factor(self, factor_id: str) -> Optional[Dict[str, Any]]:
        """获取因子信息"""
        return self.factors.get(factor_id)
    
    def get_all_factors(self) -> Dict[str, Dict[str, Any]]:
        """获取所有因子"""
        return self.factors
    
    def get_factors_by_experiment(self, experiment_id: str) -> List[Dict[str, Any]]:
        """获取指定实验的所有因子"""
        return [
            f for f in self.factors.values()
            if f.get("experiment_id") == experiment_id
        ]
    
    def get_factors_by_phase(self, phase: str) -> List[Dict[str, Any]]:
        """获取指定进化阶段的所有因子"""
        return [
            f for f in self.factors.values()
            if f.get("evolution_phase") == phase
        ]
    
    def get_top_factors(self, n: int = 10, metric: str = "RankIC") -> List[Dict[str, Any]]:
        """
        获取指标最好的 N 个因子
        
        Args:
            n: 返回数量
            metric: 排序指标 (IC, ICIR, RankIC, RankICIR)
            
        Returns:
            因子列表，按指标降序排列
        """
        factors_with_metric = [
            f for f in self.factors.values()
            if f.get("backtest_metrics", {}).get(metric) is not None
        ]
        
        sorted_factors = sorted(
            factors_with_metric,
            key=lambda x: x.get("backtest_metrics", {}).get(metric, 0),
            reverse=True
        )
        
        return sorted_factors[:n]
    
    def __len__(self) -> int:
        return len(self.factors)
    
    def __repr__(self) -> str:
        return f"FactorLibraryManager({self.library_path}, {len(self.factors)} factors)"

