"""
QuantaAlpha 因子实验模块

提供因子实验场景（Scenario）和实验（Experiment）类。
基于 rdagent 框架扩展，增加了 QlibAlphaAgentScenario 等自定义场景。

重要覆盖：
- QlibFactorExperiment：使用项目自定义 QlibFBWorkspace（含项目级配置模板），
  解决 rdagent 默认模板中 ProcessInf 与 pandas 1.5.x 不兼容等问题
"""

from copy import deepcopy
from pathlib import Path

# 先导入 rdagent 原始的所有导出（QlibFactorScenario 等）
from rdagent.scenarios.qlib.experiment.factor_experiment import (  # type: ignore
    QlibFactorScenario,
    FactorExperiment,
    FactorTask,
    FactorFBWorkspace,
)
from rdagent.utils.agent.tpl import T

# 导入项目自定义的 QlibFBWorkspace（会自动覆盖 rdagent 默认配置）
from quantaalpha.factors.workspace import QlibFBWorkspace

# 保留对 rdagent 原始类的引用
from rdagent.scenarios.qlib.experiment.factor_experiment import (
    QlibFactorExperiment as _OrigQlibFactorExperiment,
)


class QlibFactorExperiment(_OrigQlibFactorExperiment):
    """
    覆盖 rdagent 的 QlibFactorExperiment。

    关键改进：使用项目自定义的 QlibFBWorkspace 替代 rdagent 默认版本，
    从而确保使用正确的配置模板（无 ProcessInf，稳健模型参数等）。
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # 用项目自定义的 QlibFBWorkspace 重新创建 experiment_workspace
        # template_folder_path 仍指向 rdagent 包的 factor_template/（获取 read_exp_res.py 等基础文件）
        # 项目自定义的 YAML 配置会在 QlibFBWorkspace.__init__ 中自动覆盖
        rdagent_template_path = Path(_OrigQlibFactorExperiment.__module__.replace(".", "/")).parent
        # 直接用 rdagent 包的实际路径
        import rdagent.scenarios.qlib.experiment.factor_experiment as _fe_mod

        rdagent_template_path = Path(_fe_mod.__file__).parent / "factor_template"
        self.experiment_workspace = QlibFBWorkspace(
            template_folder_path=rdagent_template_path
        )


class QlibAlphaAgentScenario(QlibFactorScenario):
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
