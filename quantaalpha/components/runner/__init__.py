import pickle
import shutil
from pathlib import Path
from typing import Any, Tuple

from quantaalpha.core.developer import Developer
from quantaalpha.core.experiment import ASpecificExp, Experiment
from quantaalpha.llm.client import md5_hash


class CachedRunner(Developer[ASpecificExp]):
    def get_cache_key(self, exp: Experiment, **kwargs) -> str:
        all_tasks = []
        for based_exp in exp.based_experiments:
            all_tasks.extend(based_exp.sub_tasks)
        all_tasks.extend(exp.sub_tasks)
        task_info_list = [task.get_task_information() for task in all_tasks]
        task_info_str = "\n".join(task_info_list)
        return md5_hash(task_info_str)

    def assign_cached_result(self, exp: Experiment, cached_res: Experiment) -> Experiment:
        """
        将缓存的实验结果赋值给当前实验对象。
        
        修复：确保所有实验对象都有 running_info 属性（pickle 反序列化时可能缺失）。
        这是因为 Experiment.result 属性依赖于 running_info.result。
        """
        # 动态导入 RunningInfo 类（如果还没有导入）
        try:
            from rdagent.core.experiment import RunningInfo
        except ImportError:
            # 如果无法导入，使用 quantaalpha 的版本
            try:
                from quantaalpha.core.experiment import RunningInfo
            except ImportError:
                RunningInfo = None
        
        def _ensure_running_info(exp_obj):
            """确保实验对象有 running_info 属性"""
            if RunningInfo is not None:
                if not hasattr(exp_obj, 'running_info') or exp_obj.running_info is None:
                    exp_obj.running_info = RunningInfo()
        
        # 修复 cached_res 及其 based_experiments
        _ensure_running_info(cached_res)
        if cached_res.based_experiments:
            for based_exp in cached_res.based_experiments:
                _ensure_running_info(based_exp)
        
        # 修复 exp 及其 based_experiments（以防万一）
        _ensure_running_info(exp)
        if exp.based_experiments:
            for based_exp in exp.based_experiments:
                _ensure_running_info(based_exp)
        
        # 现在可以安全地访问 result 属性了
        if exp.based_experiments and exp.based_experiments[-1].result is None:
            exp.based_experiments[-1].result = cached_res.based_experiments[-1].result
        exp.result = cached_res.result
        return exp
