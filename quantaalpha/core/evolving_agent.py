from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from tqdm import tqdm

if TYPE_CHECKING:
    from quantaalpha.core.evaluation import Evaluator
    from quantaalpha.core.evolving_framework import EvolvableSubjects

from quantaalpha.core.evaluation import Feedback
from quantaalpha.core.evolving_framework import EvolvingStrategy, EvoStep
from quantaalpha.log import logger


class EvoAgent(ABC):
    def __init__(self, max_loop: int, evolving_strategy: EvolvingStrategy) -> None:
        self.max_loop = max_loop
        self.evolving_strategy = evolving_strategy

    @abstractmethod
    def multistep_evolve(
        self,
        evo: EvolvableSubjects,
        eva: Evaluator | Feedback,
        filter_final_evo: bool = False,
    ) -> EvolvableSubjects: ...

    @abstractmethod
    def filter_evolvable_subjects_by_feedback(
        self,
        evo: EvolvableSubjects,
        feedback: Feedback | None,
    ) -> EvolvableSubjects: ...


class RAGEvoAgent(EvoAgent):
    def __init__(
        self,
        max_loop: int,
        evolving_strategy: EvolvingStrategy,
        rag: Any,
        with_knowledge: bool = False,
        with_feedback: bool = True,
        knowledge_self_gen: bool = False,
    ) -> None:
        super().__init__(max_loop, evolving_strategy)
        self.rag = rag
        self.evolving_trace: list[EvoStep] = []
        self.with_knowledge = with_knowledge
        self.with_feedback = with_feedback
        self.knowledge_self_gen = knowledge_self_gen

    def multistep_evolve(
        self,
        evo: EvolvableSubjects,
        eva: Evaluator | Feedback,
        filter_final_evo: bool = False,
    ) -> EvolvableSubjects:
        """多步进化方法，实现了完整的进化循环流程
        
        Args:
            evo (EvolvableSubjects): 可进化的主体对象
            eva (Evaluator | Feedback): 评估器或反馈对象
            filter_final_evo (bool, optional): 是否在最终结果中过滤进化主体. Defaults to False.
            
        Returns:
            EvolvableSubjects: 进化后的主体对象
            
        进化流程包含以下步骤：
        1. 知识自进化：如果启用，根据进化轨迹生成新知识
        2. RAG查询：如果启用，使用RAG检索相关知识
        3. 进化：使用进化策略对主体进行进化
        4. 打包进化结果：将进化结果和查询到的知识打包
        5. 评估：如果启用反馈，对进化结果进行评估
        6. 更新轨迹：将本次进化步骤添加到进化轨迹中
        """
        for loop_i in tqdm(range(self.max_loop), "Debugging"):
            # 1. 知识自进化 - 如果启用了知识自生成且RAG可用，根据进化轨迹生成新知识
            if self.knowledge_self_gen and self.rag is not None:
                self.rag.generate_knowledge(self.evolving_trace)
                
            # 2. RAG查询 - 如果启用了知识检索且RAG可用，查询相关知识
            queried_knowledge = None
            if self.with_knowledge and self.rag is not None:
                # TODO: 将进化轨迹放在这里实际上并不起作用
                queried_knowledge = self.rag.query(evo, self.evolving_trace)

            # 3. 进化 - 使用进化策略对主体进行进化
            evo = self.evolving_strategy.evolve(
                evo=evo,
                evolving_trace=self.evolving_trace,
                queried_knowledge=queried_knowledge,
            )
            
            # 记录进化后的代码工作区（仅第一轮打印详情，避免重复日志刷屏）
            # TODO: 由于设计问题，我们选择忽略这个mypy错误
            logger.log_object(evo.sub_workspace_list, tag="evolving code")  # type: ignore[attr-defined]
            if loop_i == 0:
                for sw in evo.sub_workspace_list:  # type: ignore[attr-defined]
                    logger.info(f"evolving code workspace: {sw}")

            # 4. 打包进化结果 - 将进化结果和查询到的知识打包成进化步骤
            es = EvoStep(evo, queried_knowledge)

            # 5. 评估 - 如果启用了反馈，对进化结果进行评估
            if self.with_feedback:
                es.feedback = (
                    # TODO: 由于rdagent.core.evaluation.Evaluator的不规则设计，
                    # 这里未能通过mypy的测试，暂时忽略这个错误
                    eva
                    if isinstance(eva, Feedback)
                    else eva.evaluate(evo, queried_knowledge=queried_knowledge)  # type: ignore[arg-type, call-arg]
                )
                logger.log_object(es.feedback, tag="evolving feedback")

            # 6. 更新轨迹 - 将本次进化步骤添加到进化轨迹中
            self.evolving_trace.append(es)
            
        # 如果启用了反馈且需要过滤，根据最后一次反馈过滤进化主体
        if self.with_feedback and filter_final_evo:
            evo = self.filter_evolvable_subjects_by_feedback(evo, self.evolving_trace[-1].feedback)
        return evo

    def filter_evolvable_subjects_by_feedback(
        self,
        evo: EvolvableSubjects,
        feedback: Feedback | None,
    ) -> EvolvableSubjects:
        # Implementation of filter_evolvable_subjects_by_feedback method
        pass
