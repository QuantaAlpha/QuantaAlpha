import json
from pathlib import Path
from typing import List, Tuple

from jinja2 import Environment, StrictUndefined

from quantaalpha.components.coder.factor_coder.factor import FactorExperiment, FactorTask
from quantaalpha.components.proposal import FactorHypothesis2Experiment, FactorHypothesisGen
from quantaalpha.core.prompts import Prompts
from quantaalpha.core.proposal import Hypothesis, Scenario, Trace
from quantaalpha.core.experiment import Experiment
from quantaalpha.scenarios.qlib.experiment.factor_experiment import QlibFactorExperiment
from quantaalpha.oai.llm_utils import APIBackend, robust_json_parse
import os
import pandas as pd
from quantaalpha.log import logger
from quantaalpha.scenarios.qlib.regulator.factor_regulator import FactorRegulator

# 默认历史记录数量和最小值
DEFAULT_HISTORY_LIMIT = 6
MIN_HISTORY_LIMIT = 1

def render_hypothesis_and_feedback(prompt_dict, trace: Trace, history_limit: int = DEFAULT_HISTORY_LIMIT) -> str:
    """渲染 hypothesis_and_feedback，支持动态调整历史记录数量"""
    if len(trace.hist) > 0:
        return (
            Environment(undefined=StrictUndefined)
            .from_string(prompt_dict["hypothesis_and_feedback"])
            .render(trace=trace, history_limit=history_limit)
        )
    else:
        return "No previous hypothesis and feedback available since it's the first round."

def is_input_length_error(error_msg: str) -> bool:
    """检查是否是输入长度超限错误"""
    error_indicators = [
        "input length",
        "context length", 
        "maximum context",
        "token limit",
        "InvalidParameter",
        "Range of input length"
    ]
    error_str = str(error_msg).lower()
    return any(indicator.lower() in error_str for indicator in error_indicators)

QlibFactorHypothesis = Hypothesis
quantaalpha_prompt_dict = Prompts(file_path=Path(__file__).parent / "prompts_quantaalpha.yaml")

class QuantaAlphaHypothesis(Hypothesis):
    """
    QuantaAlphaHypothesis extends the Hypothesis class to include a potential_direction,
    which represents the initial idea or starting point for the hypothesis.
    """

    def __init__(
        self,
        hypothesis: str,
        concise_observation: str,
        concise_justification: str,
        concise_knowledge: str,
        concise_specification: str
    ) -> None:
        super().__init__(
            hypothesis,
            "",
            "",
            concise_observation,
            concise_justification,
            concise_knowledge,
        )
        self.concise_specification = concise_specification
        
    def __str__(self) -> str:
        return f"""Hypothesis: {self.hypothesis}
                Concise Observation: {self.concise_observation}
                Concise Justification: {self.concise_justification}
                Concise Knowledge: {self.concise_knowledge}
                concise Specification: {self.concise_specification}
                """

rdagent_prompt_dict = Prompts(file_path=Path(__file__).parent.parent / "prompts_rdagent.yaml")

class QlibFactorHypothesisGen(FactorHypothesisGen):
    def __init__(self, scen: Scenario) -> Tuple[dict, bool]:
        super().__init__(scen)

    def prepare_context(self, trace: Trace, history_limit: int = DEFAULT_HISTORY_LIMIT) -> Tuple[dict, bool]:
        hypothesis_and_feedback = render_hypothesis_and_feedback(
            rdagent_prompt_dict, trace, history_limit
        )
        context_dict = {
            "hypothesis_and_feedback": hypothesis_and_feedback,
            "RAG": None,
            "hypothesis_output_format": rdagent_prompt_dict["hypothesis_output_format"],
            "hypothesis_specification": rdagent_prompt_dict["factor_hypothesis_specification"],
        }
        return context_dict, True

    def convert_response(self, response: str) -> Hypothesis:
        response_dict = robust_json_parse(response)
        hypothesis = QlibFactorHypothesis(
            hypothesis=response_dict.get("hypothesis", ""),
            reason=response_dict.get("reason", ""),
            concise_reason=response_dict.get("concise_reason", ""),
            concise_observation=response_dict.get("concise_observation", ""),
            concise_justification=response_dict.get("concise_justification", ""),
            concise_knowledge=response_dict.get("concise_knowledge", ""),
        )
        return hypothesis


class QlibFactorHypothesis2Experiment(FactorHypothesis2Experiment):
    def prepare_context(self, hypothesis: Hypothesis, trace: Trace, history_limit: int = DEFAULT_HISTORY_LIMIT) -> Tuple[dict | bool]:
        scenario = trace.scen.get_scenario_all_desc()
        experiment_output_format = rdagent_prompt_dict["factor_experiment_output_format"]

        hypothesis_and_feedback = render_hypothesis_and_feedback(
            rdagent_prompt_dict, trace, history_limit
        )

        experiment_list: List[FactorExperiment] = [t[1] for t in trace.hist]

        factor_list = []
        for experiment in experiment_list:
            factor_list.extend(experiment.sub_tasks)

        return {
            "target_hypothesis": str(hypothesis),
            "scenario": scenario,
            "hypothesis_and_feedback": hypothesis_and_feedback,
            "experiment_output_format": experiment_output_format,
            "target_list": factor_list,
            "RAG": None,
        }, True

    def convert_response(self, response: str, trace: Trace) -> FactorExperiment:
        response_dict = robust_json_parse(response)
        tasks = []

        for factor_name in response_dict:
            factor_data = response_dict.get(factor_name, {})
            if not isinstance(factor_data, dict):
                continue
            description = factor_data.get("description", "")
            formulation = factor_data.get("formulation", "")
            # expression = factor_data.get("expression", "")
            variables = factor_data.get("variables", {})
            tasks.append(
                FactorTask(
                    factor_name=factor_name,
                    factor_description=description,
                    factor_formulation=formulation,
                    # factor_expression=expression,
                    variables=variables,
                )
            )

        exp = QlibFactorExperiment(tasks)
        exp.based_experiments = [QlibFactorExperiment(sub_tasks=[])] + [t[1] for t in trace.hist if t[2]]

        unique_tasks = []

        for task in tasks:
            duplicate = False
            for based_exp in exp.based_experiments:
                for sub_task in based_exp.sub_tasks:
                    if task.factor_name == sub_task.factor_name:
                        duplicate = True
                        break
                if duplicate:
                    break
            if not duplicate:
                unique_tasks.append(task)

        exp.tasks = unique_tasks
        return exp



quantaalpha_prompt_dict = Prompts(file_path=Path(__file__).parent.parent / "prompts_quantaalpha.yaml")

# prompt_dict不能作为属性，因为后续整个类的实例要被转为pickle，而prompt_dict不能转
class QuantaAlphaHypothesisGen(FactorHypothesisGen):
    def __init__(self, scen: Scenario, potential_direction: str=None) -> Tuple[dict, bool]:
        super().__init__(scen)
        self.potential_direction = potential_direction

    def prepare_context(self, trace: Trace, history_limit: int = DEFAULT_HISTORY_LIMIT) -> Tuple[dict, bool]:
        
        if len(trace.hist) > 0:
            hypothesis_and_feedback = render_hypothesis_and_feedback(
                quantaalpha_prompt_dict, trace, history_limit
            )
            
        elif self.potential_direction is not None: 
            hypothesis_and_feedback = (
                Environment(undefined=StrictUndefined)
                .from_string(quantaalpha_prompt_dict["potential_direction_transformation"])
                .render(potential_direction=self.potential_direction)
            ) # 
        else:
            hypothesis_and_feedback = "No previous hypothesis and feedback available since it's the first round. You are encouraged to propose an innovative hypothesis that diverges significantly from existing perspectives."
            
        context_dict = {
            "hypothesis_and_feedback": hypothesis_and_feedback,
            "RAG": None,
            "hypothesis_output_format": quantaalpha_prompt_dict["hypothesis_output_format"],
            "hypothesis_specification": quantaalpha_prompt_dict["factor_hypothesis_specification"],
        }
        return context_dict, True

    def convert_response(self, response: str) -> QuantaAlphaHypothesis:
        """
        将大模型返回的 JSON 结果转换为 QuantaAlphaHypothesis。
        为了增强鲁棒性，这里对缺失字段使用默认空字符串，避免 KeyError 中断整个实验流程。
        """
        response_dict = robust_json_parse(response)
        # 使用 get 防止部分字段缺失导致 KeyError
        hypothesis = QuantaAlphaHypothesis(
            hypothesis=response_dict.get("hypothesis", ""),
            concise_observation=response_dict.get("concise_observation", ""),
            concise_knowledge=response_dict.get("concise_knowledge", ""),
            concise_justification=response_dict.get("concise_justification", ""),
            concise_specification=response_dict.get("concise_specification", ""),
        )
        return hypothesis
    
    def gen(self, trace: Trace) -> QuantaAlphaHypothesis:
        """生成假设，支持动态调整历史记录数量以应对输入长度超限"""
        history_limit = DEFAULT_HISTORY_LIMIT
        
        while history_limit >= MIN_HISTORY_LIMIT:
            try:
                context_dict, json_flag = self.prepare_context(trace, history_limit)
                system_prompt = (
                    Environment(undefined=StrictUndefined)
                    .from_string(quantaalpha_prompt_dict["hypothesis_gen"]["system_prompt"])
                    .render(
                        targets=self.targets,
                        scenario=self.scen.get_scenario_all_desc(filtered_tag="hypothesis_and_experiment"),
                        hypothesis_output_format=context_dict["hypothesis_output_format"],
                        hypothesis_specification=context_dict["hypothesis_specification"],
                    )
                )
                user_prompt = (
                    Environment(undefined=StrictUndefined)
                    .from_string(quantaalpha_prompt_dict["hypothesis_gen"]["user_prompt"])
                    .render(
                        targets=self.targets,
                        hypothesis_and_feedback=context_dict["hypothesis_and_feedback"],
                        RAG=context_dict["RAG"],
                        round=len(trace.hist)
                    )
                )

                resp = APIBackend().build_messages_and_create_chat_completion(user_prompt, system_prompt, json_mode=json_flag)
                hypothesis = self.convert_response(resp)
                return hypothesis
                
            except Exception as e:
                if is_input_length_error(str(e)) and history_limit > MIN_HISTORY_LIMIT:
                    history_limit -= 1
                    logger.warning(f"输入长度超限，减少历史记录数量到 {history_limit} 条后重试...")
                else:
                    raise
    
    

class EmptyHypothesisGen(FactorHypothesisGen):
    def __init__(self, scen: Scenario) -> Tuple[dict, bool]:
        super().__init__(scen)
        
    def convert_response(self, *args, **kwargs) -> QuantaAlphaHypothesis: 
        return super().convert_response(*args, **kwargs)  
    
    def prepare_context(self, *args, **kwargs) -> Tuple[dict | bool]:
        return super().prepare_context(*args, **kwargs)

    def gen(self, trace: Trace) -> QuantaAlphaHypothesis:

        hypothesis = QuantaAlphaHypothesis(
            hypothesis="",
            concise_observation="",
            concise_justification="",
            concise_knowledge="",
            concise_specification=""
        )

        return hypothesis




class QuantaAlphaHypothesis2FactorExpression(FactorHypothesis2Experiment):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize FactorRegulator with config settings
        from quantaalpha.components.coder.factor_coder.config import FACTOR_COSTEER_SETTINGS
        self.factor_regulator = FactorRegulator(
            factor_zoo_path=FACTOR_COSTEER_SETTINGS.factor_zoo_path,
            duplication_threshold=FACTOR_COSTEER_SETTINGS.duplication_threshold
        )
        
    def prepare_context(self, hypothesis: Hypothesis, trace: Trace, history_limit: int = DEFAULT_HISTORY_LIMIT) -> Tuple[dict | bool]:
        scenario = trace.scen.get_scenario_all_desc()
        experiment_output_format = quantaalpha_prompt_dict["factor_experiment_output_format"]
        function_lib_description = quantaalpha_prompt_dict['function_lib_description']
        hypothesis_and_feedback = render_hypothesis_and_feedback(
            quantaalpha_prompt_dict, trace, history_limit
        )

        experiment_list: List[FactorExperiment] = [t[1] for t in trace.hist]

        factor_list = []
        for experiment in experiment_list:
            factor_list.extend(experiment.sub_tasks)

        return {
            "target_hypothesis": str(hypothesis),
            "scenario": scenario,
            "hypothesis_and_feedback": hypothesis_and_feedback,
            "function_lib_description": function_lib_description,
            "experiment_output_format": experiment_output_format,
            "target_list": factor_list,
            "RAG": None,
        }, True
        
    def convert(self, hypothesis: Hypothesis, trace: Trace) -> Experiment:
        """转换假设为因子表达式，支持动态调整历史记录数量以应对输入长度超限"""
        history_limit = DEFAULT_HISTORY_LIMIT
        
        while history_limit >= MIN_HISTORY_LIMIT:
            try:
                return self._convert_with_history_limit(hypothesis, trace, history_limit)
            except Exception as e:
                if is_input_length_error(str(e)) and history_limit > MIN_HISTORY_LIMIT:
                    history_limit -= 1
                    logger.warning(f"输入长度超限，减少历史记录数量到 {history_limit} 条后重试...")
                else:
                    raise
        
        # 如果所有重试都失败了，使用最小历史记录数量再尝试一次
        return self._convert_with_history_limit(hypothesis, trace, MIN_HISTORY_LIMIT)
    
    def _convert_with_history_limit(self, hypothesis: Hypothesis, trace: Trace, history_limit: int) -> Experiment:
        """使用指定历史记录数量进行转换"""
        context, json_flag = self.prepare_context(hypothesis, trace, history_limit)
        system_prompt = (
            Environment(undefined=StrictUndefined)
            .from_string(quantaalpha_prompt_dict["hypothesis2experiment"]["system_prompt"])
            .render(
                targets=self.targets,
                scenario=trace.scen.background, # get_scenario_all_desc(filtered_tag="hypothesis_and_experiment"),
                experiment_output_format=context["experiment_output_format"],
            )
        )
        user_prompt = (
            Environment(undefined=StrictUndefined)
            .from_string(quantaalpha_prompt_dict["hypothesis2experiment"]["user_prompt"])
            .render(
                targets=self.targets,
                target_hypothesis=context["target_hypothesis"],
                hypothesis_and_feedback=context["hypothesis_and_feedback"],
                function_lib_description=context["function_lib_description"],
                target_list=context["target_list"],
                RAG=context["RAG"], 
                expression_duplication=None
            )
        )
        
        # Detect duplicated sub-expressions
        flag = False
        expression_duplication_prompt = None
        while True:
            if flag:
                break
                
            resp = APIBackend().build_messages_and_create_chat_completion(user_prompt, system_prompt, json_mode=json_flag)
            try:
                response_dict = robust_json_parse(resp)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 解析失败: {e}, 重试中...")
                continue
            proposed_names = []
            proposed_exprs = []
            
            for i, factor_name in enumerate(response_dict):
                factor_data = response_dict.get(factor_name, {})
                if not isinstance(factor_data, dict):
                    continue
                expr = factor_data.get("expression", "")
                
                # Check if expression is parsable
                if not self.factor_regulator.is_parsable(expr):
                    logger.info(f"Failed to parse expr: {expr}, retrying...")
                    break
                
                success, eval_dict = self.factor_regulator.evaluate(expr)
                if not success:
                    break
                
                # If expression has problems, regenerate with feedback
                if not self.factor_regulator.is_expression_acceptable(eval_dict):
                    # Calculate ratios for feedback
                    num_all_nodes = eval_dict['num_all_nodes']
                    free_args_ratio = float(eval_dict['num_free_args']) / float(num_all_nodes) if num_all_nodes > 0 else 0.0
                    unique_vars_ratio = float(eval_dict['num_unique_vars']) / float(num_all_nodes) if num_all_nodes > 0 else 0.0
                    
                    # Get symbol length and base features count for complexity feedback
                    symbol_length = eval_dict.get('symbol_length', 0)
                    num_base_features = eval_dict.get('num_base_features', 0)
                    symbol_length_threshold = self.factor_regulator.symbol_length_threshold
                    base_features_threshold = self.factor_regulator.base_features_threshold
                    
                    feedback_item = (
                            Environment(undefined=StrictUndefined)
                            .from_string(quantaalpha_prompt_dict["expression_duplication"])
                            .render(
                                prev_expression=expr,
                                duplicated_subtree_size=eval_dict['duplicated_subtree_size'],
                            duplication_threshold=self.factor_regulator.duplication_threshold,
                            duplicated_subtree=eval_dict.get('duplicated_subtree', ''),
                            matched_alpha=eval_dict.get('matched_alpha', ''),
                            free_args_ratio=free_args_ratio,
                            num_free_args=eval_dict['num_free_args'],
                            unique_vars_ratio=unique_vars_ratio,
                            num_unique_vars=eval_dict['num_unique_vars'],
                            num_all_nodes=num_all_nodes,
                            symbol_length=symbol_length,
                            symbol_length_threshold=symbol_length_threshold,
                            num_base_features=num_base_features,
                            base_features_threshold=base_features_threshold
                            )
                        )
                    
                    if expression_duplication_prompt is not None:
                        expression_duplication_prompt = '\n\n'.join([expression_duplication_prompt, feedback_item])
                    else:
                        expression_duplication_prompt = feedback_item
                    
                    user_prompt = (
                        Environment(undefined=StrictUndefined)
                        .from_string(quantaalpha_prompt_dict["hypothesis2experiment"]["user_prompt"])
                        .render(
                            targets=self.targets,
                            target_hypothesis=context["target_hypothesis"],
                            hypothesis_and_feedback=context["hypothesis_and_feedback"],
                            function_lib_description=context["function_lib_description"],
                            target_list=context["target_list"],
                            RAG=context["RAG"], 
                            expression_duplication=expression_duplication_prompt
                        )
                    )
                    break
                else:
                    proposed_names.append(factor_name)
                    proposed_exprs.append(expr)
                    if i == len(response_dict) - 1:
                        flag = True
                    else:
                        continue
        

        # Add valid factors to the factor regulator
        self.factor_regulator.add_factor(proposed_names, proposed_exprs)
                
                
        return self.convert_response(resp, trace)
    

    def convert_response(self, response: str, trace: Trace) -> FactorExperiment:
        response_dict = robust_json_parse(response)
        tasks = []

        for factor_name in response_dict:
            factor_data = response_dict.get(factor_name, {})
            if not isinstance(factor_data, dict):
                continue
            description = factor_data.get("description", "")
            formulation = factor_data.get("formulation", "")
            expression = factor_data.get("expression", "")
            variables = factor_data.get("variables", {})
            tasks.append(
                FactorTask(
                    factor_name=factor_name,
                    factor_description=description,
                    factor_formulation=formulation,
                    factor_expression=expression,
                    variables=variables,
                )
            )
            
        exp = QlibFactorExperiment(tasks)
        exp.based_experiments = [QlibFactorExperiment(sub_tasks=[])] + [t[1] for t in trace.hist if t[2]]

        unique_tasks = []

        for task in tasks:
            duplicate = False
            for based_exp in exp.based_experiments:
                for sub_task in based_exp.sub_tasks:
                    if task.factor_name == sub_task.factor_name:
                        duplicate = True
                        break
                if duplicate:
                    break
            if not duplicate:
                unique_tasks.append(task)

        exp.tasks = unique_tasks
        return exp



class BacktestHypothesis2FactorExpression(FactorHypothesis2Experiment):
    def __init__(self, factor_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.factor_path = factor_path
        
    def convert_response(self, *args, **kwargs) -> FactorExperiment:
        return super().convert_response(*args, **kwargs)
        
    def prepare_context(self, *args, **kwargs) -> Tuple[dict | bool]:
        return super().prepare_context(*args, **kwargs)
        
    def convert(self, hypothesis: Hypothesis, trace: Trace) -> FactorExperiment:
        if os.path.exists(self.factor_path):
            tasks = []
            factor_df = pd.read_csv(self.factor_path, usecols=["factor_name", "factor_expression"], index_col=None)
            for index, row in factor_df.iterrows():
                tasks.append(
                    FactorTask(
                        factor_name=row["factor_name"],
                        factor_description="",
                        factor_formulation="",
                        factor_expression=row["factor_expression"],
                        variables="",
                    )
                )
            
            exp = QlibFactorExperiment(tasks)
            exp.based_experiments = [QlibFactorExperiment(sub_tasks=[])] + [t[1] for t in trace.hist if t[2]]

            unique_tasks = []

            for task in tasks:
                duplicate = False
                for based_exp in exp.based_experiments:
                    for sub_task in based_exp.sub_tasks:
                        if task.factor_name == sub_task.factor_name:
                            duplicate = True
                            break
                    if duplicate:
                        break
                if not duplicate:
                    unique_tasks.append(task)

            exp.tasks = unique_tasks
            return exp
            
        else:
            raise ValueError(f"File {self.factor_csv_path} does not exist. ")
        
    