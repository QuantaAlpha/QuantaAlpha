import re
from pathlib import Path

from quantaalpha.coder.costeer.evaluators import (
    CoSTEEREvaluator,
    CoSTEERMultiFeedback,
    CoSTEERSingleFeedback,
)
from quantaalpha.factors.coder.eva_utils import (
    FactorCodeEvaluator,
    FactorFinalDecisionEvaluator,
    FactorValueEvaluator,
)
from quantaalpha.factors.coder.factor import FactorTask
from quantaalpha.factors.coder.config import FACTOR_COSTEER_SETTINGS
from quantaalpha.core.evolving_framework import QueriedKnowledge
from quantaalpha.core.experiment import Workspace
from quantaalpha.factors.regulator.factor_regulator import FactorRegulator
from quantaalpha.log import logger

FactorSingleFeedback = CoSTEERSingleFeedback
FactorMultiFeedback = CoSTEERMultiFeedback


class FactorEvaluatorForCoder(CoSTEEREvaluator):
    """This class is the v1 version of evaluator for a single factor implementation.
    It calls several evaluators in share modules to evaluate the factor implementation.
    Now includes AST-based regularization checks for factor quality.
    """

    def __init__(self, *args, factor_zoo_path: str = None, duplication_threshold: int = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.value_evaluator = FactorValueEvaluator(self.scen)
        self.code_evaluator = FactorCodeEvaluator(self.scen)
        self.final_decision_evaluator = FactorFinalDecisionEvaluator(self.scen)
        # Initialize FactorRegulator for AST-based regularization checks
        # Use config settings if not explicitly provided
        factor_zoo_path = factor_zoo_path or FACTOR_COSTEER_SETTINGS.factor_zoo_path
        duplication_threshold = duplication_threshold if duplication_threshold is not None else FACTOR_COSTEER_SETTINGS.duplication_threshold
        symbol_length_threshold = getattr(FACTOR_COSTEER_SETTINGS, 'symbol_length_threshold', 300)
        base_features_threshold = getattr(FACTOR_COSTEER_SETTINGS, 'base_features_threshold', 6)
        self.factor_regulator = FactorRegulator(
            factor_zoo_path=factor_zoo_path,
            duplication_threshold=duplication_threshold,
            symbol_length_threshold=symbol_length_threshold,
            base_features_threshold=base_features_threshold
        )
    
    def extract_expr(self, code_str: str) -> str:
        """从代码字符串中提取expr表达式"""
        # 使用正则表达式匹配expr = "xxx"或expr = 'xxx'的模式
        pattern = r'expr\s*=\s*["\']([^"\']*)["\']'
        match = re.search(pattern, code_str)
        if match:
            return match.group(1)
        else:
            return ""
    
    def check_ast_regularization(self, implementation: Workspace) -> tuple[bool, str]:
        """
        检查因子表达式是否符合AST正则化条件
        
        Returns:
            tuple[bool, str]: (是否符合条件, 反馈信息)
        """
        try:
            # 从代码中提取因子表达式
            # Workspace对象通常有code_dict属性，其中包含'factor.py'
            if hasattr(implementation, 'code_dict') and 'factor.py' in implementation.code_dict:
                code = implementation.code_dict['factor.py']
            elif hasattr(implementation, 'code'):
                code = implementation.code
            else:
                return True, "AST Regularization Check Skipped: Cannot extract code from implementation"
            
            expr = self.extract_expr(code)
            
            if not expr:
                return True, ""  # 如果无法提取表达式，跳过正则化检查
            
            # 检查表达式是否可解析
            if not self.factor_regulator.is_parsable(expr):
                return False, f"AST Regularization Check Failed: Expression cannot be parsed: {expr}"
            
            # 评估表达式
            success, eval_dict = self.factor_regulator.evaluate(expr)
            if not success:
                return False, f"AST Regularization Check Failed: Failed to evaluate expression: {expr}"
            
            # 检查表达式是否可接受
            is_acceptable = self.factor_regulator.is_expression_acceptable(eval_dict)
            
            if not is_acceptable:
                # 构建详细的反馈信息
                feedback_parts = []
                
                # 条件1: 新颖性检查（仅在因子库存在时检查）
                dup_size = eval_dict.get('duplicated_subtree_size', 0)
                dup_threshold = self.factor_regulator.duplication_threshold
                has_factor_zoo = self.factor_regulator.factor_zoo_path is not None and len(self.factor_regulator.alphazoo) > 0
                
                if has_factor_zoo and dup_size > dup_threshold:
                    matched_alpha = eval_dict.get('matched_alpha', 'Unknown')
                    duplicated_subtree = eval_dict.get('duplicated_subtree', '')
                    feedback_parts.append(
                        f"Novelty Check Failed: Duplicated subtree size ({dup_size}) exceeds threshold ({dup_threshold}). "
                        f"Matched with: {matched_alpha}. Duplicated subtree: {duplicated_subtree}"
                    )
                elif not has_factor_zoo:
                    # 如果没有因子库，记录但不算失败
                    feedback_parts.append(
                        f"Note: Novelty check skipped (no factor zoo provided). "
                        f"Duplicated subtree size: {dup_size}"
                    )
                
                # 条件2: 自由参数比例检查
                num_free_args = eval_dict.get('num_free_args', 0)
                num_all_nodes = eval_dict.get('num_all_nodes', 0)
                if num_all_nodes > 0:
                    free_args_ratio = num_free_args / num_all_nodes
                    if free_args_ratio >= 0.5:
                        feedback_parts.append(
                            f"Free Arguments Ratio Check Failed: Free arguments ratio ({free_args_ratio:.2%}) >= 50%. "
                            f"Number of free args: {num_free_args}, Total nodes: {num_all_nodes}. "
                            f"This indicates the factor is over-parameterized."
                        )
                
                # 条件3: 唯一变量比例检查
                num_unique_vars = eval_dict.get('num_unique_vars', 0)
                if num_all_nodes > 0:
                    unique_vars_ratio = num_unique_vars / num_all_nodes
                    if unique_vars_ratio >= 0.5:
                        feedback_parts.append(
                            f"Unique Variables Ratio Check Failed: Unique variables ratio ({unique_vars_ratio:.2%}) >= 50%. "
                            f"Number of unique vars: {num_unique_vars}, Total nodes: {num_all_nodes}. "
                            f"This indicates the factor lacks diversity."
                        )
                
                # 条件4: 符号长度检查（SL）
                symbol_length = eval_dict.get('symbol_length', 0)
                symbol_length_threshold = self.factor_regulator.symbol_length_threshold
                if symbol_length > symbol_length_threshold:
                    feedback_parts.append(
                        f"Symbol Length (SL) Check Failed: Symbol length ({symbol_length}) exceeds threshold ({symbol_length_threshold}). "
                        f"The factor expression is too complex and may lead to overfitting. "
                        f"Please simplify the expression to reduce structural complexity."
                    )
                
                # 条件5: 基础特征使用量检查（ER）
                num_base_features = eval_dict.get('num_base_features', 0)
                base_features_threshold = self.factor_regulator.base_features_threshold
                if num_base_features > base_features_threshold:
                    feedback_parts.append(
                        f"Base Features Count (ER) Check Failed: Number of base features ({num_base_features}) exceeds threshold ({base_features_threshold}). "
                        f"The factor uses too many raw features (e.g., $close, $open, $high, $low, $volume), "
                        f"which may indicate over-engineering. Please reduce the number of distinct base features used."
                        )
                
                # 只有当有实际失败的条件时才返回False
                has_failures = (
                    (has_factor_zoo and dup_size > dup_threshold) or
                    (num_all_nodes > 0 and num_free_args / num_all_nodes >= 0.5) or
                    (num_all_nodes > 0 and num_unique_vars / num_all_nodes >= 0.5) or
                    (symbol_length > symbol_length_threshold) or
                    (num_base_features > base_features_threshold)
                )
                
                if has_failures:
                    feedback = "AST Regularization Check Failed:\n" + "\n".join(feedback_parts)
                    return False, feedback
                else:
                    # 只有note信息，不算失败
                    return True, "\n".join(feedback_parts)
            else:
                return True, "AST Regularization Check Passed"
                
        except Exception as e:
            logger.warning(f"AST regularization check failed with exception: {e}")
            # 如果检查过程出错，不阻止因子通过（容错处理）
            return True, f"AST Regularization Check Skipped: {str(e)}"

    def evaluate(
        self,
        target_task: FactorTask,
        implementation: Workspace,
        gt_implementation: Workspace = None,
        queried_knowledge: QueriedKnowledge = None,
        **kwargs,
    ) -> FactorSingleFeedback:
        if implementation is None:
            return None

        target_task_information = target_task.get_task_information()
        if (
            queried_knowledge is not None
            and target_task_information in queried_knowledge.success_task_to_knowledge_dict
        ):
            return queried_knowledge.success_task_to_knowledge_dict[target_task_information].feedback
        elif queried_knowledge is not None and target_task_information in queried_knowledge.failed_task_info_set:
            return FactorSingleFeedback(
                execution_feedback="This task has failed too many times, skip implementation.",
                value_generated_flag=False,
                code_feedback="This task has failed too many times, skip code evaluation.",
                value_feedback="This task has failed too many times, skip value evaluation.",
                final_decision=False,
                final_feedback="This task has failed too many times, skip final decision evaluation.",
                final_decision_based_on_gt=False,
            )
        else:
            factor_feedback = FactorSingleFeedback()

            # 0. AST Regularization Check (before execution)
            ast_check_passed, ast_feedback = self.check_ast_regularization(implementation)
            if not ast_check_passed:
                # If AST regularization check fails, mark as failed and return early
                factor_feedback.execution_feedback = f"AST Regularization Check Failed: {ast_feedback}"
                factor_feedback.value_generated_flag = False
                factor_feedback.value_feedback = "AST Regularization Check Failed, skip value evaluation."
                factor_feedback.code_feedback = ast_feedback
                factor_feedback.final_decision = False
                factor_feedback.final_feedback = f"Factor rejected due to AST regularization violations:\n{ast_feedback}"
                factor_feedback.final_decision_based_on_gt = False
                return factor_feedback

            # 1. Get factor execution feedback to generated implementation and remove the long list of numbers in execution feedback
            (
                execution_feedback,
                gen_df,
            ) = implementation.execute()

            execution_feedback = re.sub(r"(?<=\D)(,\s+-?\d+\.\d+){50,}(?=\D)", ", ", execution_feedback)
            factor_feedback.execution_feedback = "\n".join(
                [line for line in execution_feedback.split("\n") if "warning" not in line.lower()]
            )
            
            # Add AST regularization check result to execution feedback if passed
            if ast_feedback and ast_feedback != "":
                factor_feedback.execution_feedback = f"{ast_feedback}\n\n{factor_feedback.execution_feedback}"

            # 2. Get factor value feedback
            if gen_df is None:
                factor_feedback.value_feedback = "No factor value generated, skip value evaluation."
                factor_feedback.value_generated_flag = False
                decision_from_value_check = None
            else:
                factor_feedback.value_generated_flag = True
                (
                    factor_feedback.value_feedback,
                    decision_from_value_check,
                ) = self.value_evaluator.evaluate(
                    implementation=implementation, gt_implementation=gt_implementation, version=target_task.version
                )

            factor_feedback.final_decision_based_on_gt = gt_implementation is not None
            # import pdb; pdb.set_trace()
            if decision_from_value_check is not None and decision_from_value_check is True:
                # To avoid confusion, when same_value_or_high_correlation is True, we do not need code feedback
                factor_feedback.code_feedback = "Final decision is True and there are no code critics."
                factor_feedback.final_decision = decision_from_value_check
                factor_feedback.final_feedback = "Value evaluation passed, skip final decision evaluation."
            elif decision_from_value_check is not None and decision_from_value_check is False:
                factor_feedback.code_feedback, _ = self.code_evaluator.evaluate(
                    target_task=target_task,
                    implementation=implementation,
                    execution_feedback=factor_feedback.execution_feedback,
                    value_feedback=factor_feedback.value_feedback,
                    gt_implementation=gt_implementation,
                )
                factor_feedback.final_decision = decision_from_value_check
                factor_feedback.final_feedback = "Value evaluation failed, skip final decision evaluation."
            else:
                factor_feedback.code_feedback, _ = self.code_evaluator.evaluate(
                    target_task=target_task,
                    implementation=implementation,
                    execution_feedback=factor_feedback.execution_feedback,
                    value_feedback=factor_feedback.value_feedback,
                    gt_implementation=gt_implementation,
                )
                (
                    factor_feedback.final_decision,
                    factor_feedback.final_feedback,
                ) = self.final_decision_evaluator.evaluate(
                    target_task=target_task,
                    execution_feedback=factor_feedback.execution_feedback,
                    value_feedback=factor_feedback.value_feedback,
                    code_feedback=factor_feedback.code_feedback,
                )
            return factor_feedback


# TODO:
def shorten_prompt(tpl: str, render_kwargs: dict, shorten_key: str, max_trail: int = 10) -> str:
    """When the prompt is too long. We have to shorten it.
    But we should not truncate the prompt directly, so we should find the key we want to shorten and then shorten it.
    """
    # TODO: this should replace most of code in
    # - FactorFinalDecisionEvaluator.evaluate
    # - FactorCodeEvaluator.evaluate
