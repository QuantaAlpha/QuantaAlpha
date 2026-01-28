from quantaalpha.core.conf import ExtendedBaseSettings


class BasePropSetting(ExtendedBaseSettings):
    """
    The common part of the config for RD Loop to propose and development
    You can add following config in the subclass to distinguish the environment variables.
    """

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
    """
    The common part of the config for Alpha Agent Loop to propose and development
    You can add following config in the subclass to distinguish the environment variables.
    """

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
