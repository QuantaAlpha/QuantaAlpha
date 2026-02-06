"""
QuantaAlpha 流程设置

定义实验流程中各组件的类路径配置。
通过字符串类路径实现组件的动态加载和灵活替换。
"""

from quantaalpha.core.conf import ExtendedBaseSettings, ExtendedSettingsConfigDict


# =============================================================================
# 基础设置类
# =============================================================================

class BasePropSetting(ExtendedBaseSettings):
    """RD Loop 通用配置基类"""

    scen: str = ""
    knowledge_base: str = ""
    knowledge_base_path: str = ""
    hypothesis_gen: str = ""
    hypothesis2experiment: str = ""
    coder: str = ""
    runner: str = ""
    summarizer: str = ""
    evolving_n: int = 10


class BaseFacSetting(ExtendedBaseSettings):
    """Alpha Agent Loop 通用配置基类"""

    scen: str = ""
    knowledge_base: str = ""
    knowledge_base_path: str = ""
    hypothesis_gen: str = ""
    construction: str = ""
    calculation: str = ""
    coder: str = ""
    runner: str = ""
    summarizer: str = ""
    evolving_n: int = 10


# =============================================================================
# 因子挖掘设置（主实验使用）
# =============================================================================

class AlphaAgentFactorBasePropSetting(BasePropSetting):
    """主实验 - LLM 驱动的因子挖掘"""
    model_config = ExtendedSettingsConfigDict(env_prefix="QLIB_FACTOR_", protected_namespaces=())

    scen: str = "quantaalpha.factors.experiment.QlibAlphaAgentScenario"
    hypothesis_gen: str = "quantaalpha.factors.proposal.AlphaAgentHypothesisGen"
    hypothesis2experiment: str = "quantaalpha.factors.proposal.AlphaAgentHypothesis2FactorExpression"
    coder: str = "quantaalpha.factors.qlib_coder.QlibFactorParser"
    runner: str = "quantaalpha.factors.runner.QlibFactorRunner"
    summarizer: str = "quantaalpha.factors.feedback.AlphaAgentQlibFactorHypothesisExperiment2Feedback"
    evolving_n: int = 5


class FactorBasePropSetting(BasePropSetting):
    """基础因子实验（传统 RD Loop 模式）"""
    model_config = ExtendedSettingsConfigDict(env_prefix="QLIB_FACTOR_", protected_namespaces=())

    scen: str = "quantaalpha.factors.experiment.QlibFactorScenario"
    hypothesis_gen: str = "quantaalpha.factors.proposal.QlibFactorHypothesisGen"
    hypothesis2experiment: str = "quantaalpha.factors.proposal.QlibFactorHypothesis2Experiment"
    coder: str = "quantaalpha.factors.qlib_coder.QlibFactorCoSTEER"
    runner: str = "quantaalpha.factors.runner.QlibFactorRunner"
    summarizer: str = "quantaalpha.factors.feedback.QlibFactorHypothesisExperiment2Feedback"
    evolving_n: int = 10


class FactorBackTestBasePropSetting(BasePropSetting):
    """因子回测模式"""
    model_config = ExtendedSettingsConfigDict(env_prefix="QLIB_FACTOR_", protected_namespaces=())

    scen: str = "quantaalpha.factors.experiment.QlibAlphaAgentScenario"
    hypothesis_gen: str = "quantaalpha.factors.proposal.EmptyHypothesisGen"
    hypothesis2experiment: str = "quantaalpha.factors.proposal.BacktestHypothesis2FactorExpression"
    coder: str = "quantaalpha.factors.qlib_coder.QlibFactorCoder"
    runner: str = "quantaalpha.factors.runner.QlibFactorRunner"
    summarizer: str = "quantaalpha.factors.feedback.QlibFactorHypothesisExperiment2Feedback"
    evolving_n: int = 1


class FactorFromReportPropSetting(FactorBasePropSetting):
    """从研报提取因子模式"""
    scen: str = "quantaalpha.factors.experiment.QlibFactorFromReportScenario"
    report_result_json_file_path: str = "git_ignore_folder/report_list.json"
    max_factors_per_exp: int = 10000
    is_report_limit_enabled: bool = False


# =============================================================================
# Model 实验设置（contrib，可选）
# =============================================================================

class ModelBasePropSetting(BasePropSetting):
    """模型实验（扩展功能）"""
    model_config = ExtendedSettingsConfigDict(env_prefix="QLIB_MODEL_", protected_namespaces=())

    scen: str = "quantaalpha.contrib.model.experiment.QlibModelScenario"
    hypothesis_gen: str = "quantaalpha.contrib.model.proposal.QlibModelHypothesisGen"
    hypothesis2experiment: str = "quantaalpha.contrib.model.proposal.QlibModelHypothesis2Experiment"
    coder: str = "quantaalpha.contrib.model.qlib_coder.QlibModelCoSTEER"
    runner: str = "quantaalpha.contrib.model.runner.QlibModelRunner"
    summarizer: str = "quantaalpha.factors.feedback.QlibModelHypothesisExperiment2Feedback"
    evolving_n: int = 10


# =============================================================================
# 单例实例（全局可用）
# =============================================================================

ALPHA_AGENT_FACTOR_PROP_SETTING = AlphaAgentFactorBasePropSetting()
FACTOR_PROP_SETTING = FactorBasePropSetting()
FACTOR_BACK_TEST_PROP_SETTING = FactorBackTestBasePropSetting()
FACTOR_FROM_REPORT_PROP_SETTING = FactorFromReportPropSetting()
MODEL_PROP_SETTING = ModelBasePropSetting()
