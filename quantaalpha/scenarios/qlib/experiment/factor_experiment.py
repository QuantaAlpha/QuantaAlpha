"""
QuantaAlpha 兼容层：factor_experiment

项目中大量配置引用路径:
- quantaalpha.scenarios.qlib.experiment.factor_experiment.QlibFactorScenario
- quantaalpha.scenarios.qlib.experiment.factor_experiment.QlibFactorExperiment
- quantaalpha.scenarios.qlib.experiment.factor_experiment.QlibQuantaAlphaScenario

原始实现已经存在于本仓库的 RD-Agent 子目录:
- wuyinze/RD-Agent/rdagent/scenarios/qlib/experiment/factor_experiment.py

由于在 quantaalpha.scenarios.qlib.experiment.__init__ 中已经将 RD-Agent 根目录
加入了 sys.path，这里可以直接从 rdagent 对应模块导入并整体导出，保证路径兼容。
"""

from rdagent.scenarios.qlib.experiment.factor_experiment import *  # type: ignore  # noqa: F401,F403


class QlibQuantaAlphaScenario(QlibFactorScenario):  # type: ignore[misc]
    """
    QuantaAlpha 专用的 Scenario 包装类。

    QuantaAlphaLoop 在构造时会传入 `use_local` 参数，但 RD-Agent 原始的
    QlibFactorScenario.__init__ 不接受该参数。这里通过子类包装的方式
    兼容这个签名，同时完全复用父类的行为。
    """

    def __init__(self, use_local: bool = True, *args, **kwargs):
        # 当前实现中暂时不区分 use_local，直接调用父类构造函数
        super().__init__(*args, **kwargs)




