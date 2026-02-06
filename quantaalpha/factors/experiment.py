"""
QuantaAlpha 因子实验模块

提供因子实验场景（Scenario）和实验（Experiment）类。
基于 rdagent 框架扩展，增加了 QlibAlphaAgentScenario 等自定义场景。
"""

from rdagent.scenarios.qlib.experiment.factor_experiment import *  # type: ignore  # noqa: F401,F403


class QlibAlphaAgentScenario(QlibFactorScenario):  # type: ignore[misc]
    """
    AlphaAgent 专用的 Scenario 包装类。

    AlphaAgentLoop 在构造时会传入 `use_local` 参数，但 RD-Agent 原始的
    QlibFactorScenario.__init__ 不接受该参数。这里通过子类包装的方式
    兼容这个签名，同时完全复用父类的行为。
    """

    def __init__(self, use_local: bool = True, *args, **kwargs):
        # 当前实现中暂时不区分 use_local，直接调用父类构造函数
        super().__init__(*args, **kwargs)




