#!/usr/bin/env python3
"""
因子库管理器

用于在实验过程中自动保存因子到统一的因子库JSON文件。
每完成一轮回测后，会自动将挖掘出的因子追加到因子库中。

使用方式：
    from factor_library_manager import FactorLibraryManager
    
    manager = FactorLibraryManager("all_factors_library.json")
    manager.add_factors_from_experiment(
        experiment=exp,
        experiment_id="2026-01-18_12-00-00",
        round_number=0,
        hypothesis="...",
        feedback=feedback_obj,
        evolution_phase="original",
        ...
    )
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from collections import OrderedDict
from typing import Any, Optional, List
import threading


class FactorLibraryManager:
    """因子库管理器，用于保存和管理挖掘出的因子"""
    
    _lock = threading.Lock()  # 文件写入锁，确保并发安全
    
    def __init__(self, library_path: str):
        """
        初始化因子库管理器
        
        Args:
            library_path: 因子库JSON文件路径
        """
        self.library_path = Path(library_path)
        
    def _generate_factor_id(self, factor_name: str, factor_expression: str, timestamp: str) -> str:
        """
        生成唯一的因子ID
        
        Args:
            factor_name: 因子名称
            factor_expression: 因子表达式
            timestamp: 时间戳
            
        Returns:
            16位十六进制字符串作为因子ID
        """
        content = f"{factor_name}_{factor_expression}_{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _load_library(self) -> dict:
        """
        加载因子库，如果不存在则创建新的
        
        Returns:
            因子库字典，包含 metadata 和 factors
        """
        if self.library_path.exists():
            try:
                with open(self.library_path, 'r', encoding='utf-8') as f:
                    return json.load(f, object_pairs_hook=OrderedDict)
            except (json.JSONDecodeError, IOError):
                pass
        
        # 创建新的因子库
        return {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_factors": 0,
                "version": "1.0"
            },
            "factors": OrderedDict()
        }
    
    def _save_library(self, data: dict) -> None:
        """
        保存因子库到文件
        
        Args:
            data: 因子库字典
        """
        # 更新元数据
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        data["metadata"]["total_factors"] = len(data.get("factors", {}))
        
        # 确保目录存在
        self.library_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(self.library_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
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
        evolution_phase: str = "original",
        trajectory_id: str = "",
        parent_trajectory_ids: Optional[List[str]] = None,
    ) -> int:
        """
        从实验对象中提取因子并保存到库中
        
        Args:
            experiment: 实验对象，包含 sub_tasks 和 result
            experiment_id: 实验ID
            round_number: 轮次编号
            hypothesis: 假设文本
            feedback: 反馈对象
            initial_direction: 初始方向
            user_initial_direction: 用户初始方向
            planning_direction: 规划方向
            evolution_phase: 进化阶段 (original/mutation/crossover)
            trajectory_id: 轨迹ID
            parent_trajectory_ids: 父轨迹ID列表
            
        Returns:
            添加的因子数量
        """
        if experiment is None:
            return 0
        
        # 获取时间戳
        timestamp = datetime.now().isoformat()
        
        # 提取实验结果指标
        result_metrics = {}
        if hasattr(experiment, 'result') and experiment.result is not None:
            result = experiment.result
            if hasattr(result, 'to_dict'):
                result_metrics = result.to_dict()
            elif isinstance(result, dict):
                result_metrics = result
            else:
                try:
                    # pandas Series
                    result_metrics = result.to_dict() if hasattr(result, 'to_dict') else {}
                except:
                    result_metrics = {}
        
        # 提取反馈信息
        feedback_info = {}
        if feedback is not None:
            if hasattr(feedback, 'observations'):
                feedback_info['observations'] = str(feedback.observations)
            if hasattr(feedback, 'hypothesis_evaluation'):
                feedback_info['hypothesis_evaluation'] = str(feedback.hypothesis_evaluation)
            if hasattr(feedback, 'decision'):
                feedback_info['decision'] = feedback.decision
            if hasattr(feedback, 'reason'):
                feedback_info['reason'] = str(feedback.reason)
        
        # 从实验中提取因子
        factors_to_add = []
        
        if hasattr(experiment, 'sub_tasks'):
            for idx, task in enumerate(experiment.sub_tasks):
                try:
                    # 获取任务信息
                    task_info = {}
                    if hasattr(task, 'get_task_information_and_implementation_result'):
                        task_info = task.get_task_information_and_implementation_result()
                    
                    factor_name = task_info.get('factor_name') or getattr(task, 'factor_name', f'factor_{idx}')
                    factor_expression = task_info.get('factor_expression') or getattr(task, 'factor_expression', '')
                    factor_description = task_info.get('factor_description') or getattr(task, 'factor_description', '')
                    factor_formulation = task_info.get('factor_formulation') or getattr(task, 'factor_formulation', '')
                    
                    # 获取实现代码和因子目录路径（稳健处理）
                    implementation_code = ""
                    factor_dir = ""
                    result_h5_path = ""
                    full_workspace_path = ""
                    cache_location = None
                    
                    try:
                        if hasattr(experiment, 'sub_workspace_list') and idx < len(experiment.sub_workspace_list):
                            workspace = experiment.sub_workspace_list[idx]
                            # 获取实现代码
                            if hasattr(workspace, 'code'):
                                implementation_code = workspace.code or ""
                            
                            # 尝试多种方式获取 workspace_path
                            ws_path = None
                            
                            # 方式1: 直接从 workspace.workspace_path 获取
                            if hasattr(workspace, 'workspace_path'):
                                try:
                                    ws_path_attr = workspace.workspace_path
                                    if ws_path_attr is not None:
                                        ws_path = Path(ws_path_attr) if not isinstance(ws_path_attr, Path) else ws_path_attr
                                except Exception:
                                    pass
                            
                            # 方式2: 尝试从 workspace 字符串表示中提取
                            if ws_path is None:
                                try:
                                    ws_str = str(workspace)
                                    if 'workspace_path=' in ws_str:
                                        # 格式类似: Workspace[workspace_path=PosixPath('/path/to/workspace')]
                                        import re
                                        match = re.search(r"workspace_path=(?:PosixPath\('|Path\('|')([^']+)", ws_str)
                                        if match:
                                            ws_path = Path(match.group(1))
                                except Exception:
                                    pass
                            
                            # 如果成功获取到 workspace_path
                            if ws_path is not None:
                                factor_dir = ws_path.name
                                full_workspace_path = str(ws_path)
                                result_h5_path = str(ws_path / 'result.h5')
                        
                        # 获取环境变量
                        workspace_suffix = os.environ.get('EXPERIMENT_ID', '')
                        pickle_cache_path = os.environ.get('PICKLE_CACHE_FOLDER_PATH_STR', '')
                        env_workspace_path = os.environ.get('WORKSPACE_PATH', '')
                        
                        # 调试日志：显示获取到的路径信息
                        # print(f"[DEBUG] Factor {idx} cache info: workspace_suffix={workspace_suffix}, "
                        #       f"full_workspace_path={full_workspace_path}, factor_dir={factor_dir}")
                        
                        # 构建缓存位置信息
                        # 条件放宽：只要有 workspace_suffix 或者有 full_workspace_path 就尝试记录
                        if workspace_suffix or full_workspace_path:
                            cache_location = {
                                "experiment_id": workspace_suffix,
                                "env_workspace_path": env_workspace_path,
                                "factor_workspace_path": full_workspace_path,  # 完整的因子工作空间路径
                                "factor_dir": factor_dir,
                                "result_h5_path": result_h5_path,
                                "pickle_cache_path": pickle_cache_path,
                            }
                            # print(f"[DEBUG] Factor {idx} cache_location set: {cache_location}")
                        else:
                            print(f"[INFO] Factor {idx}: No cache location available "
                                  f"(workspace_suffix={workspace_suffix!r}, full_workspace_path={full_workspace_path!r})")
                    except Exception as cache_err:
                        # 缓存位置获取失败不影响因子保存
                        print(f"Warning: Failed to get cache location for factor {idx}: {cache_err}")
                        import traceback
                        traceback.print_exc()
                        cache_location = None
                    
                    # 生成因子ID
                    factor_id = self._generate_factor_id(factor_name, factor_expression, timestamp)
                    
                    # 构建因子记录
                    factor_record = {
                        "factor_id": factor_id,
                        "factor_name": factor_name,
                        "factor_expression": factor_expression,
                        "factor_implementation_code": implementation_code,
                        "factor_description": factor_description,
                        "factor_formulation": factor_formulation,
                        "cache_location": cache_location,  # 新增：完整的缓存位置信息
                        "metadata": {
                            "experiment_id": experiment_id,
                            "round_number": round_number,
                            "evolution_phase": evolution_phase,
                            "trajectory_id": trajectory_id,
                            "parent_trajectory_ids": parent_trajectory_ids or [],
                            "hypothesis": hypothesis,
                            "initial_direction": initial_direction,
                            "planning_direction": planning_direction,
                            "created_at": timestamp,
                        },
                        "backtest_results": result_metrics,
                        "feedback": feedback_info,
                    }
                    
                    factors_to_add.append((factor_id, factor_record))
                    
                except Exception as e:
                    print(f"Warning: Failed to extract factor {idx}: {e}")
                    continue
        
        # 写入因子库（线程安全）
        if factors_to_add:
            with self._lock:
                data = self._load_library()
                for factor_id, factor_record in factors_to_add:
                    data["factors"][factor_id] = factor_record
                self._save_library(data)
        
        return len(factors_to_add)

# ============================================================
# 以下是原有的因子库抽样工具函数
# ============================================================

def load_factor_library(filepath: Path):
    """
    加载因子库，返回 metadata 和 factors（保持原始顺序）
    """
    print(f"📖 加载因子库: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    metadata = data.get('metadata', {})
    factors = data.get('factors', OrderedDict())
    
    print(f"   总因子数: {len(factors)}")
    return metadata, factors


def save_factor_library(factors: OrderedDict, output_path: Path, note: str):
    """
    保存因子库到 JSON 文件
    """
    output_data = OrderedDict([
        ('metadata', OrderedDict([
            ('created_at', datetime.now().isoformat()),
            ('total_factors', len(factors)),
            ('sampling_note', note),
            ('version', '1.0')
        ])),
        ('factors', factors)
    ])
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已保存: {output_path} ({len(factors)} 个因子)")

