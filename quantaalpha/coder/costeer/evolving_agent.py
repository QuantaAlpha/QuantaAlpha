from quantaalpha.coder.costeer.evaluators import CoSTEERSingleFeedback
from quantaalpha.coder.costeer.evolvable_subjects import EvolvingItem
from quantaalpha.core.evolving_agent import RAGEvoAgent
from quantaalpha.core.evolving_framework import EvolvableSubjects


class FilterFailedRAGEvoAgent(RAGEvoAgent):
    def filter_evolvable_subjects_by_feedback(
        self, evo: EvolvableSubjects, feedback: CoSTEERSingleFeedback
    ) -> EvolvableSubjects:
        assert isinstance(evo, EvolvingItem)
        assert isinstance(feedback, list)
        assert len(evo.sub_workspace_list) == len(feedback)

        for index in range(len(evo.sub_workspace_list)):
            if evo.sub_workspace_list[index] is not None and feedback[index] and not feedback[index].final_decision:
                evo.sub_workspace_list[index].clear()
        return evo
