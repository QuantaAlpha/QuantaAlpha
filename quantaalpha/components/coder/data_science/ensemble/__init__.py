# from quantaalpha.components.coder.CoSTEER import CoSTEER
# from quantaalpha.components.coder.CoSTEER.config import CoSTEER_SETTINGS
# from quantaalpha.components.coder.CoSTEER.evaluators import CoSTEERMultiEvaluator
# from quantaalpha.core.scenario import Scenario


# class ModelEnsembleCoSTEER(CoSTEER):
#     def __init__(
#         self,
#         scen: Scenario,
#         *args,
#         **kwargs,
#     ) -> None:
#         eva = CoSTEERMultiEvaluator(
#             ModelEnsembleCoSTEEREvaluator(scen=scen), scen=scen
#         )  # Please specify whether you agree running your eva in parallel or not
#         es = ModelEnsembleMultiProcessEvolvingStrategy(scen=scen, settings=CoSTEER_SETTINGS)

#         super().__init__(*args, settings=CoSTEER_SETTINGS, eva=eva, es=es, evolving_version=1, scen=scen, **kwargs)
