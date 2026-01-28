from quantaalpha.components.coder.CoSTEER import CoSTEER
from quantaalpha.components.coder.CoSTEER.config import CoSTEER_SETTINGS
from quantaalpha.components.coder.CoSTEER.evaluators import CoSTEERMultiEvaluator
from quantaalpha.components.coder.model_coder.evaluators import ModelCoSTEEREvaluator
from quantaalpha.components.coder.model_coder.evolving_strategy import (
    ModelMultiProcessEvolvingStrategy,
)
from quantaalpha.core.scenario import Scenario


class ModelCoSTEER(CoSTEER):
    def __init__(
        self,
        scen: Scenario,
        *args,
        **kwargs,
    ) -> None:
        eva = CoSTEERMultiEvaluator(ModelCoSTEEREvaluator(scen=scen), scen=scen)
        es = ModelMultiProcessEvolvingStrategy(scen=scen, settings=CoSTEER_SETTINGS)

        super().__init__(*args, settings=CoSTEER_SETTINGS, eva=eva, es=es, evolving_version=2, scen=scen, **kwargs)
