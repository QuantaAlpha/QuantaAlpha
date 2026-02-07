"""
QuantaAlpha 因子实验模块

提供因子实验场景（Scenario）和实验（Experiment）类。
基于 rdagent 框架扩展，增加了 QlibAlphaAgentScenario 等自定义场景。
"""

from copy import deepcopy

from rdagent.scenarios.qlib.experiment.factor_experiment import *  # type: ignore  # noqa: F401,F403
from rdagent.utils.agent.tpl import T


class QlibAlphaAgentScenario(QlibFactorScenario):  # type: ignore[misc]
    """
    AlphaAgent 专用的 Scenario 包装类。

    AlphaAgentLoop 在构造时会传入 `use_local` 参数，但 RD-Agent 原始的
    QlibFactorScenario.__init__ 不接受该参数。这里通过子类包装的方式
    兼容这个签名，同时完全复用父类的行为。

    关键区别：当 use_local=True 时，使用本地版本的 get_data_folder_intro
    避免调用 Docker（rdagent 默认版本会尝试连接 Docker）。
    """

    def __init__(self, use_local: bool = True, *args, **kwargs):
        # 不直接调用 super().__init__()，因为父类会调用 rdagent 的
        # get_data_folder_intro() 从而触发 Docker 连接。
        # 这里手动初始化，用本地版本替换数据准备步骤。
        from rdagent.core.scenario import Scenario
        from rdagent.scenarios.qlib.experiment.factor_experiment import QlibFactorScenario
        from quantaalpha.factors.qlib_utils import get_data_folder_intro as local_get_data_folder_intro

        # 调用 Scenario（祖父类）的 __init__，跳过 QlibFactorScenario 的 __init__
        Scenario.__init__(self)

        # 使用 rdagent 包中的模板（绝对路径引用，避免相对路径找不到 prompts.yaml）
        tpl_prefix = "scenarios.qlib.experiment.prompts"

        self._background = deepcopy(
            T(f"{tpl_prefix}:qlib_factor_background").r(
                runtime_environment=self.get_runtime_environment(),
            )
        )
        # 使用本地版本的 get_data_folder_intro，传入 use_local 参数
        self._source_data = deepcopy(local_get_data_folder_intro(use_local=use_local))
        self._output_format = deepcopy(T(f"{tpl_prefix}:qlib_factor_output_format").r())
        self._interface = deepcopy(T(f"{tpl_prefix}:qlib_factor_interface").r())
        self._strategy = deepcopy(T(f"{tpl_prefix}:qlib_factor_strategy").r())
        self._simulator = deepcopy(T(f"{tpl_prefix}:qlib_factor_simulator").r())
        self._rich_style_description = deepcopy(T(f"{tpl_prefix}:qlib_factor_rich_style_description").r())
        self._experiment_setting = deepcopy(T(f"{tpl_prefix}:qlib_factor_experiment_setting").r())
