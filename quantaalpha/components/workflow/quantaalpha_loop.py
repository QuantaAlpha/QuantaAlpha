"""
Model workflow with session control
It is from `rdagent/app/qlib_rd_loop/model.py` and try to replace `rdagent/app/qlib_rd_loop/RDAgent.py`
"""

import os
import time
import yaml
import pandas as pd
from typing import Any, Dict

from quantaalpha.components.workflow.conf import BaseFacSetting
from quantaalpha.core.developer import Developer
from quantaalpha.core.proposal import (
    Hypothesis2Experiment,
    HypothesisExperiment2Feedback,
    HypothesisGen,  
    Trace,
)
from quantaalpha.core.scenario import Scenario
from quantaalpha.core.utils import import_class
from quantaalpha.log import logger
from quantaalpha.log.time import measure_time
from quantaalpha.utils.workflow import LoopBase, LoopMeta
from quantaalpha.core.exception import FactorEmptyError
import threading


import datetime
import pickle
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from tqdm.auto import tqdm

from quantaalpha.core.exception import CoderError
from quantaalpha.log import logger
from functools import wraps

# 导入质量门控模块
from quantaalpha.scenarios.qlib.regulator.consistency_checker import (
    FactorQualityGate,
    FactorConsistencyChecker,
    ComplexityChecker,
    RedundancyChecker
)

# 定义装饰器：在函数调用前检查stop_event

            
def stop_event_check(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if STOP_EVENT is not None and STOP_EVENT.is_set():
            # 当收到停止信号时，可以直接抛出异常或返回特定值，这里示例抛出异常
            raise Exception("Operation stopped due to stop_event flag.")
        return func(self, *args, **kwargs)
    return wrapper


class QuantaAlphaLoop(LoopBase, metaclass=LoopMeta):
    skip_loop_error = (FactorEmptyError,)
    
    @measure_time
    def __init__(
        self, 
        PROP_SETTING: BaseFacSetting, 
        potential_direction, 
        stop_event: threading.Event, 
        use_local: bool = True,
        strategy_suffix: str = "",
        evolution_phase: str = "original",
        trajectory_id: str = "",
        parent_trajectory_ids: list = None,
        direction_id: int = 0,
        round_idx: int = 0,
    ):
        with logger.tag("init"):
            self.use_local = use_local
            # 保存初始方向，用于后续因子溯源
            self.potential_direction = potential_direction
            
            # 进化相关属性
            self.strategy_suffix = strategy_suffix  # 策略指导后缀
            self.evolution_phase = evolution_phase  # 进化阶段: original/mutation/crossover
            self.trajectory_id = trajectory_id  # 轨迹ID
            self.parent_trajectory_ids = parent_trajectory_ids or []  # 父代轨迹ID列表
            self.direction_id = direction_id  # 方向ID
            self.round_idx = round_idx  # 进化轮次: 0=original, 1=mutation, 2=crossover, ...
            
            # 用于收集轨迹数据
            self._last_hypothesis = None
            self._last_experiment = None
            self._last_feedback = None
            
            logger.info(f"初始化QuantaAlphaLoop，使用{'本地环境' if use_local else 'Docker容器'}回测")
            if potential_direction:
                logger.info(f"初始方向: {potential_direction}")
            if evolution_phase != "original":
                logger.info(f"进化阶段: {evolution_phase}, 轮次: {round_idx}, 轨迹ID: {trajectory_id}")
                
            scen: Scenario = import_class(PROP_SETTING.scen)(use_local=use_local)
            logger.log_object(scen, tag="scenario")

            ### 换成基于初始hypo的，生成完整的hypo
            # 如果有策略后缀，将其附加到方向中
            effective_direction = potential_direction
            if strategy_suffix:
                effective_direction = (potential_direction or "") + "\n" + strategy_suffix
            
            self.hypothesis_generator: HypothesisGen = import_class(PROP_SETTING.hypothesis_gen)(scen, effective_direction)
            logger.log_object(self.hypothesis_generator, tag="hypothesis generator")

            ### 换成一次生成10个因子
            self.factor_constructor: Hypothesis2Experiment = import_class(PROP_SETTING.hypothesis2experiment)()
            logger.log_object(self.factor_constructor, tag="experiment generation")

            ### 加入代码执行中的 Variables / Functions
            self.coder: Developer = import_class(PROP_SETTING.coder)(scen)
            logger.log_object(self.coder, tag="coder")
            
            self.runner: Developer = import_class(PROP_SETTING.runner)(scen)
            logger.log_object(self.runner, tag="runner")

            self.summarizer: HypothesisExperiment2Feedback = import_class(PROP_SETTING.summarizer)(scen)
            logger.log_object(self.summarizer, tag="summarizer")
            self.trace = Trace(scen=scen)
            
            # 初始化质量门控（从配置文件加载设置）
            self.quality_gate = self._init_quality_gate()
            
            global STOP_EVENT
            STOP_EVENT = stop_event
            super().__init__()
    
    def _init_quality_gate(self) -> FactorQualityGate:
        """
        从配置文件初始化质量门控
        
        读取配置文件中的开关设置：
        - quality_gate.consistency_enabled: 是否启用一致性检验
        - quality_gate.complexity_enabled: 是否启用复杂度检验
        - quality_gate.redundancy_enabled: 是否启用冗余度检验
        """
        # 默认配置
        consistency_enabled = False  # 默认关闭一致性检验
        complexity_enabled = True    # 默认开启复杂度检验
        redundancy_enabled = True    # 默认开启冗余度检验
        
        # 复杂度检验参数默认值
        symbol_length_threshold = 250
        base_features_threshold = 6
        free_args_ratio_threshold = 0.5
        
        # 冗余度检验参数默认值
        duplication_threshold = 5
        factor_zoo_path = None
        
        # 尝试从环境变量读取配置文件路径
        config_path_str = os.environ.get('CONFIG_PATH', '')
        if config_path_str:
            config_path = Path(config_path_str)
        else:
            # 使用默认配置文件
            config_path = Path(__file__).parent.parent.parent / "app" / "qlib_rd_loop" / "run_config.yaml"
        
        # 加载配置文件
        if config_path.exists():
            try:
                config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                
                # 读取质量门控配置
                qg_config = config.get("quality_gate", {})
                consistency_enabled = bool(qg_config.get("consistency_enabled", False))
                complexity_enabled = bool(qg_config.get("complexity_enabled", True))
                redundancy_enabled = bool(qg_config.get("redundancy_enabled", True))
                
                # 读取因子复杂度配置
                factor_config = config.get("factor", {})
                complexity_config = factor_config.get("complexity", {})
                symbol_length_threshold = int(complexity_config.get("symbol_length_threshold", 250))
                base_features_threshold = int(complexity_config.get("base_features_threshold", 6))
                free_args_ratio_threshold = float(complexity_config.get("free_args_ratio_threshold", 0.5))
                
                # 读取因子重复性配置
                duplication_config = factor_config.get("duplication", {})
                duplication_threshold = int(duplication_config.get("threshold", 5))
                factor_zoo_path = duplication_config.get("factor_zoo_path")
                
                logger.info(f"质量门控配置: consistency={consistency_enabled}, complexity={complexity_enabled}, redundancy={redundancy_enabled}")
                
            except Exception as e:
                logger.warning(f"加载质量门控配置失败: {e}，使用默认配置")
        
        # 创建各检验器
        consistency_checker = FactorConsistencyChecker(
            enabled=consistency_enabled,
            max_correction_attempts=3
        )
        
        complexity_checker = ComplexityChecker(
            enabled=complexity_enabled,
            symbol_length_threshold=symbol_length_threshold,
            base_features_threshold=base_features_threshold,
            free_args_ratio_threshold=free_args_ratio_threshold
        )
        
        redundancy_checker = RedundancyChecker(
            enabled=redundancy_enabled,
            duplication_threshold=duplication_threshold,
            factor_zoo_path=factor_zoo_path
        )
        
        return FactorQualityGate(
            consistency_checker=consistency_checker,
            complexity_checker=complexity_checker,
            redundancy_checker=redundancy_checker,
            consistency_enabled=consistency_enabled,
            complexity_enabled=complexity_enabled,
            redundancy_enabled=redundancy_enabled
        )

    @classmethod
    def load(cls, path, use_local: bool = True):
        """加载现有会话"""
        instance = super().load(path)
        instance.use_local = use_local
        logger.info(f"加载QuantaAlphaLoop，使用{'本地环境' if use_local else 'Docker容器'}回测")
        return instance

    @measure_time
    @stop_event_check
    def factor_propose(self, prev_out: dict[str, Any]):
        """
        提出作为构建因子的基础的假设
        """
        with logger.tag("r"):  
            idea = self.hypothesis_generator.gen(self.trace)
            logger.log_object(idea, tag="hypothesis generation")
            # 保存用于轨迹收集
            self._last_hypothesis = idea
        return idea

    @measure_time
    @stop_event_check
    def factor_construct(self, prev_out: dict[str, Any]):
        """
        基于假设构造多个不同的因子，并进行质量门控检验
        
        质量门控包括：
        1. 一致性检验：检验假设、描述、表达式之间的逻辑一致性
        2. 复杂度检验：检验因子表达式的复杂度是否在合理范围
        3. 冗余度检验：检验因子是否与已有因子重复
        
        如果检验不通过，尝试修正因子；如果修正失败，该因子将被标记但仍会继续流程。
        """
        with logger.tag("r"): 
            factor = self.factor_constructor.convert(prev_out["factor_propose"], self.trace)
            logger.log_object(factor.sub_tasks, tag="experiment generation")
            
            # 进行质量门控检验
            if self.quality_gate and hasattr(factor, 'sub_tasks') and factor.sub_tasks:
                hypothesis_text = str(prev_out["factor_propose"]) if prev_out.get("factor_propose") else ""
                
                quality_results = []
                for task in factor.sub_tasks:
                    # 获取因子信息
                    factor_name = getattr(task, 'factor_name', 'Unknown')
                    factor_description = getattr(task, 'factor_description', '')
                    factor_formulation = getattr(task, 'factor_formulation', '')
                    factor_expression = getattr(task, 'factor_expression', '')
                    variables = getattr(task, 'variables', {})
                    
                    if not factor_expression:
                        logger.warning(f"因子 {factor_name} 没有表达式，跳过质量门控")
                        continue
                    
                    # 执行质量门控
                    passed, feedback, results = self.quality_gate.evaluate(
                        hypothesis=hypothesis_text,
                        factor_name=factor_name,
                        factor_description=factor_description,
                        factor_formulation=factor_formulation,
                        factor_expression=factor_expression,
                        variables=variables
                    )
                    
                    quality_results.append({
                        "factor_name": factor_name,
                        "passed": passed,
                        "feedback": feedback,
                        "results": results
                    })
                    
                    # 如果有修正后的表达式，更新任务
                    if results.get("corrected_expression") and results["corrected_expression"] != factor_expression:
                        logger.info(f"更新因子 {factor_name} 的表达式")
                        task.factor_expression = results["corrected_expression"]
                    
                    if results.get("corrected_description") and results["corrected_description"] != factor_description:
                        logger.info(f"更新因子 {factor_name} 的描述")
                        task.factor_description = results["corrected_description"]
                    
                    # 将质量检验结果保存到任务中
                    task.quality_check_result = {
                        "passed": passed,
                        "feedback": feedback
                    }
                
                # 记录质量门控汇总
                passed_count = sum(1 for r in quality_results if r["passed"])
                total_count = len(quality_results)
                logger.info(f"质量门控完成: {passed_count}/{total_count} 因子通过检验")
                
        return factor

    @measure_time
    @stop_event_check
    def factor_calculate(self, prev_out: dict[str, Any]):
        """
        根据因子表达式计算过去的因子表（因子值）
        """
        with logger.tag("d"):  # develop
            factor = self.coder.develop(prev_out["factor_construct"])
            logger.log_object(factor.sub_workspace_list, tag="coder result")
        return factor
    

    @measure_time
    @stop_event_check
    def factor_backtest(self, prev_out: dict[str, Any]):
        """
        回测因子
        """
        with logger.tag("ef"):  # evaluate and feedback
            logger.info(f"Start factor backtest (Local: {self.use_local})")
            exp = self.runner.develop(prev_out["factor_calculate"], use_local=self.use_local)
            if exp is None:
                logger.error(f"Factor extraction failed.")
                raise FactorEmptyError("Factor extraction failed.")
            logger.log_object(exp, tag="runner result")
            # 保存用于轨迹收集
            self._last_experiment = exp
        return exp

    @measure_time
    @stop_event_check
    def feedback(self, prev_out: dict[str, Any]):
        feedback = self.summarizer.generate_feedback(prev_out["factor_backtest"], prev_out["factor_propose"], self.trace)
        with logger.tag("ef"):  # evaluate and feedback
            logger.log_object(feedback, tag="feedback")
        self.trace.hist.append((prev_out["factor_propose"], prev_out["factor_backtest"], feedback))
        
        # 保存用于轨迹收集
        self._last_feedback = feedback

        # 自动保存因子到统一因子库
        try:
            import sys
            from pathlib import Path
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from factor_library_manager import FactorLibraryManager
            
            # 获取实验ID（从session_folder提取）
            experiment_id = "unknown"
            if hasattr(self, 'session_folder') and self.session_folder:
                # session_folder格式: log/2026-01-08_12-13-43-974105/__session__
                # 提取实验ID: 2026-01-08_12-13-43-974105
                parts = Path(self.session_folder).parts
                for part in parts:
                    if part.startswith("202") and len(part) > 10:  # 日期格式
                        experiment_id = part
                        break
            
            # 获取当前轮次（使用进化控制器的 round_idx）
            round_number = self.round_idx
            
            # 获取假设文本
            hypothesis_text = None
            if prev_out.get("factor_propose"):
                hypothesis_text = str(prev_out["factor_propose"])
            
            # 获取初始方向（用户输入 + planning 分支方向）
            planning_direction = getattr(self, 'potential_direction', None)
            user_initial_direction = getattr(self, 'user_initial_direction', None)
            
            # 获取进化相关信息
            evolution_phase = getattr(self, 'evolution_phase', 'original')
            trajectory_id = getattr(self, 'trajectory_id', '')
            parent_trajectory_ids = getattr(self, 'parent_trajectory_ids', [])
            
            # 创建因子库管理器并保存因子
            # 支持通过环境变量 FACTOR_LIBRARY_SUFFIX 自定义输出文件名
            import os
            library_suffix = os.environ.get('FACTOR_LIBRARY_SUFFIX', '')
            if library_suffix:
                library_filename = f"all_factors_library_{library_suffix}.json"
            else:
                library_filename = "all_factors_library.json"
            library_path = project_root / library_filename
            manager = FactorLibraryManager(str(library_path))
            manager.add_factors_from_experiment(
                experiment=prev_out["factor_backtest"],
                experiment_id=experiment_id,
                round_number=round_number,
                hypothesis=hypothesis_text,
                feedback=feedback,
                initial_direction=planning_direction,
                user_initial_direction=user_initial_direction,
                planning_direction=planning_direction,
                evolution_phase=evolution_phase,
                trajectory_id=trajectory_id,
                parent_trajectory_ids=parent_trajectory_ids,
            )
            logger.info(f"已保存因子到统一因子库: {library_path} (phase={evolution_phase})")
        except Exception as e:
            # 如果保存失败，记录警告但不影响主流程
            logger.warning(f"保存因子到库失败: {e}")
    
    def _get_trajectory_data(self) -> dict[str, Any]:
        """
        获取当前轮次的轨迹数据，用于进化控制器收集。
        
        注意：方法名以下划线开头，避免被工作流系统识别为步骤。
        工作流系统会自动将所有非以下划线开头的可调用方法识别为步骤。
        
        Returns:
            包含假设、实验、反馈等信息的字典
        """
        return {
            "hypothesis": self._last_hypothesis,
            "experiment": self._last_experiment,
            "feedback": self._last_feedback,
            "direction_id": self.direction_id,
            "evolution_phase": self.evolution_phase,
            "trajectory_id": self.trajectory_id,
            "parent_trajectory_ids": self.parent_trajectory_ids,
            "loop_idx": self.loop_idx,
            "round_idx": self.round_idx,
        }




class BacktestLoop(LoopBase, metaclass=LoopMeta):
    skip_loop_error = (FactorEmptyError,)
    @measure_time
    def __init__(self, PROP_SETTING: BaseFacSetting, factor_path=None):
        with logger.tag("init"):

            self.factor_path = factor_path

            scen: Scenario = import_class(PROP_SETTING.scen)()
            logger.log_object(scen, tag="scenario")

            self.hypothesis_generator: HypothesisGen = import_class(PROP_SETTING.hypothesis_gen)(scen)
            logger.log_object(self.hypothesis_generator, tag="hypothesis generator")

            self.factor_constructor: Hypothesis2Experiment = import_class(PROP_SETTING.hypothesis2experiment)(factor_path=factor_path)
            logger.log_object(self.factor_constructor, tag="experiment generation")

            self.coder: Developer = import_class(PROP_SETTING.coder)(scen, with_feedback=False, with_knowledge=False, knowledge_self_gen=False)
            logger.log_object(self.coder, tag="coder")
            
            self.runner: Developer = import_class(PROP_SETTING.runner)(scen)
            logger.log_object(self.runner, tag="runner")

            self.summarizer: HypothesisExperiment2Feedback = import_class(PROP_SETTING.summarizer)(scen)
            logger.log_object(self.summarizer, tag="summarizer")
            self.trace = Trace(scen=scen)
            super().__init__()

    def factor_propose(self, prev_out: dict[str, Any]):
        """
        Market hypothesis on which factors are built
        """
        with logger.tag("r"):  
            idea = self.hypothesis_generator.gen(self.trace)
            logger.log_object(idea, tag="hypothesis generation")
        return idea
        

    @measure_time
    def factor_construct(self, prev_out: dict[str, Any]):
        """
        Construct a variety of factors that depend on the hypothesis
        """
        with logger.tag("r"): 
            factor = self.factor_constructor.convert(prev_out["factor_propose"], self.trace)
            logger.log_object(factor.sub_tasks, tag="experiment generation")
        return factor

    @measure_time
    def factor_calculate(self, prev_out: dict[str, Any]):
        """
        Debug factors and calculate their values
        """
        with logger.tag("d"):  # develop
            factor = self.coder.develop(prev_out["factor_construct"])
            logger.log_object(factor.sub_workspace_list, tag="coder result")
        return factor
    

    @measure_time
    def factor_backtest(self, prev_out: dict[str, Any]):
        """
        Conduct Backtesting
        """
        with logger.tag("ef"):  # evaluate and feedback
            exp = self.runner.develop(prev_out["factor_calculate"])
            if exp is None:
                logger.error(f"Factor extraction failed.")
                raise FactorEmptyError("Factor extraction failed.")
            logger.log_object(exp, tag="runner result")
        return exp

    @measure_time
    def stop(self, prev_out: dict[str, Any]):
        exit(0)
