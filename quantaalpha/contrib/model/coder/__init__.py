from quantaalpha.coder.costeer import CoSTEER
from quantaalpha.coder.costeer.config import CoSTEER_SETTINGS
from quantaalpha.coder.costeer.evaluators import CoSTEERMultiEvaluator
from quantaalpha.contrib.model.coder.evaluators import ModelCoSTEEREvaluator
from quantaalpha.contrib.model.coder.evolving_strategy import (
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
