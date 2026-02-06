"""
Factor Consistency Checker Module
因子一致性检验模块

This module provides semantic consistency checking between:
- Hypothesis (假设)
- Factor Description (因子描述)
- Factor Formulation (数学公式)
- Factor Expression (符号表达式)
- Factor Code (因子代码)

该模块提供以下内容之间的语义一致性检验：
- 假设
- 因子描述
- 数学公式
- 符号表达式
- 因子代码
"""

import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass
from jinja2 import Environment, StrictUndefined

from quantaalpha.core.prompts import Prompts
from quantaalpha.llm.client import APIBackend, robust_json_parse
from quantaalpha.log import logger


# 加载一致性检验提示词
consistency_prompts = Prompts(file_path=Path(__file__).parent / "consistency_prompts.yaml")


@dataclass
class ConsistencyCheckResult:
    """
    一致性检验结果
    
    Attributes:
        is_consistent: 是否通过一致性检验
        hypothesis_to_description: 假设→描述 一致性分析
        description_to_formulation: 描述→公式 一致性分析
        formulation_to_expression: 公式→表达式 一致性分析
        overall_feedback: 总体反馈
        corrected_expression: 修正后的表达式（如果需要修正）
        corrected_description: 修正后的描述（如果需要修正）
        severity: 问题严重程度 (none, minor, major, critical)
    """
    is_consistent: bool
    hypothesis_to_description: str
    description_to_formulation: str
    formulation_to_expression: str
    overall_feedback: str
    corrected_expression: Optional[str] = None
    corrected_description: Optional[str] = None
    severity: str = "none"  # none, minor, major, critical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_consistent": self.is_consistent,
            "hypothesis_to_description": self.hypothesis_to_description,
            "description_to_formulation": self.description_to_formulation,
            "formulation_to_expression": self.formulation_to_expression,
            "overall_feedback": self.overall_feedback,
            "corrected_expression": self.corrected_expression,
            "corrected_description": self.corrected_description,
            "severity": self.severity
        }


class FactorConsistencyChecker:
    """
    因子一致性检验器
    
    检验假设、描述、公式、表达式之间的逻辑一致性。
    如果发现不一致，尝试修正表达式或描述。
    
    Checks logical consistency between hypothesis, description, formulation, and expression.
    If inconsistencies are found, attempts to correct the expression or description.
    """
    
    def __init__(
        self, 
        scen=None, 
        max_correction_attempts: int = 3,
        enabled: bool = True,
        strict_mode: bool = False
    ):
        """
        初始化一致性检验器
        
        Args:
            scen: 场景对象
            max_correction_attempts: 最大修正尝试次数
            enabled: 是否启用一致性检验
            strict_mode: 严格模式，任何不一致都会拒绝因子
        """
        self.scen = scen
        self.max_correction_attempts = max_correction_attempts
        self.enabled = enabled
        self.strict_mode = strict_mode
    
    def check_consistency(
        self,
        hypothesis: str,
        factor_name: str,
        factor_description: str,
        factor_formulation: str,
        factor_expression: str,
        variables: Dict[str, str] = None
    ) -> ConsistencyCheckResult:
        """
        检查因子的一致性
        
        Args:
            hypothesis: 假设文本
            factor_name: 因子名称
            factor_description: 因子描述
            factor_formulation: 数学公式 (LaTeX)
            factor_expression: 符号表达式
            variables: 使用的变量字典
        
        Returns:
            ConsistencyCheckResult: 一致性检验结果
        """
        if not self.enabled:
            return ConsistencyCheckResult(
                is_consistent=True,
                hypothesis_to_description="Consistency check disabled",
                description_to_formulation="Consistency check disabled",
                formulation_to_expression="Consistency check disabled",
                overall_feedback="Consistency check is disabled, skipping.",
                severity="none"
            )
        
        logger.info(f"开始一致性检验: {factor_name}")
        
        try:
            # 构建系统提示词
            system_prompt = (
                Environment(undefined=StrictUndefined)
                .from_string(consistency_prompts["consistency_check_system"])
                .render()
            )
            
            # 构建用户提示词
            user_prompt = (
                Environment(undefined=StrictUndefined)
                .from_string(consistency_prompts["consistency_check_user"])
                .render(
                    hypothesis=hypothesis,
                    factor_name=factor_name,
                    factor_description=factor_description,
                    factor_formulation=factor_formulation,
                    factor_expression=factor_expression,
                    variables=variables or {}
                )
            )
            
            # 调用LLM进行一致性检验
            response = APIBackend().build_messages_and_create_chat_completion(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                json_mode=True
            )
            
            # 解析响应
            result_dict = robust_json_parse(response)
            
            is_consistent = result_dict.get("is_consistent", False)
            severity = result_dict.get("severity", "none")
            
            result = ConsistencyCheckResult(
                is_consistent=is_consistent,
                hypothesis_to_description=result_dict.get("hypothesis_to_description", ""),
                description_to_formulation=result_dict.get("description_to_formulation", ""),
                formulation_to_expression=result_dict.get("formulation_to_expression", ""),
                overall_feedback=result_dict.get("overall_feedback", ""),
                corrected_expression=result_dict.get("corrected_expression"),
                corrected_description=result_dict.get("corrected_description"),
                severity=severity
            )
            
            # 记录检验结果
            if is_consistent:
                logger.info(f"一致性检验通过: {factor_name}")
            else:
                logger.warning(f"一致性检验失败: {factor_name}, 严重程度: {severity}")
                logger.warning(f"反馈: {result.overall_feedback}")
            
            return result
        
        except Exception as e:
            logger.error(f"一致性检验出错: {e}")
            # 出错时默认通过（容错处理）
            return ConsistencyCheckResult(
                is_consistent=True,
                hypothesis_to_description=f"Error during check: {str(e)}",
                description_to_formulation="",
                formulation_to_expression="",
                overall_feedback=f"Consistency check failed with error: {str(e)}. Skipping check.",
                severity="none"
            )
    
    def check_and_correct(
        self,
        hypothesis: str,
        factor_name: str,
        factor_description: str,
        factor_formulation: str,
        factor_expression: str,
        variables: Dict[str, str] = None
    ) -> Tuple[ConsistencyCheckResult, str, str]:
        """
        检查一致性并尝试修正
        
        Args:
            hypothesis: 假设文本
            factor_name: 因子名称
            factor_description: 因子描述
            factor_formulation: 数学公式
            factor_expression: 符号表达式
            variables: 使用的变量
        
        Returns:
            Tuple[ConsistencyCheckResult, str, str]: (检验结果, 最终表达式, 最终描述)
        """
        current_expression = factor_expression
        current_description = factor_description
        
        for attempt in range(self.max_correction_attempts):
            result = self.check_consistency(
                hypothesis=hypothesis,
                factor_name=factor_name,
                factor_description=current_description,
                factor_formulation=factor_formulation,
                factor_expression=current_expression,
                variables=variables
            )
            
            if result.is_consistent:
                return result, current_expression, current_description
            
            # 严格模式下不尝试修正
            if self.strict_mode:
                logger.warning(f"严格模式：因子 {factor_name} 一致性检验失败，不进行修正")
                return result, current_expression, current_description
            
            # 尝试应用修正
            if result.corrected_expression and result.corrected_expression != current_expression:
                logger.info(f"尝试修正表达式 (尝试 {attempt + 1}/{self.max_correction_attempts})")
                logger.info(f"原表达式: {current_expression}")
                logger.info(f"修正后: {result.corrected_expression}")
                current_expression = result.corrected_expression
            elif result.corrected_description and result.corrected_description != current_description:
                logger.info(f"尝试修正描述 (尝试 {attempt + 1}/{self.max_correction_attempts})")
                current_description = result.corrected_description
            else:
                # 无法修正，退出循环
                logger.warning(f"无法修正因子 {factor_name}，放弃修正尝试")
                break
        
        # 最终检验
        final_result = self.check_consistency(
            hypothesis=hypothesis,
            factor_name=factor_name,
            factor_description=current_description,
            factor_formulation=factor_formulation,
            factor_expression=current_expression,
            variables=variables
        )
        
        return final_result, current_expression, current_description
    
    def batch_check(
        self,
        hypothesis: str,
        factors: List[Dict[str, Any]]
    ) -> List[Tuple[Dict[str, Any], ConsistencyCheckResult]]:
        """
        批量检查多个因子的一致性
        
        Args:
            hypothesis: 假设文本
            factors: 因子列表，每个因子是一个字典包含 name, description, formulation, expression, variables
        
        Returns:
            List[Tuple[Dict, ConsistencyCheckResult]]: 每个因子及其检验结果
        """
        results = []
        
        for factor in factors:
            result, corrected_expr, corrected_desc = self.check_and_correct(
                hypothesis=hypothesis,
                factor_name=factor.get("name", "Unknown"),
                factor_description=factor.get("description", ""),
                factor_formulation=factor.get("formulation", ""),
                factor_expression=factor.get("expression", ""),
                variables=factor.get("variables", {})
            )
            
            # 更新因子信息
            updated_factor = factor.copy()
            updated_factor["expression"] = corrected_expr
            updated_factor["description"] = corrected_desc
            updated_factor["consistency_check"] = result.to_dict()
            
            results.append((updated_factor, result))
        
        return results
    
    def should_proceed_to_backtest(self, result: ConsistencyCheckResult) -> bool:
        """
        判断是否应该进入回测阶段
        
        Args:
            result: 一致性检验结果
        
        Returns:
            bool: 是否应该进入回测
        """
        if not self.enabled:
            return True
        
        if result.is_consistent:
            return True
        
        # 根据严重程度判断
        if self.strict_mode:
            return False  # 严格模式下任何不一致都不进入回测
        
        # 非严格模式下，minor问题可以进入回测
        if result.severity in ["none", "minor"]:
            return True
        
        return False


class ComplexityChecker:
    """
    因子复杂度检验器
    
    检查因子表达式的复杂度是否在合理范围内。
    """
    
    def __init__(
        self,
        enabled: bool = True,
        symbol_length_threshold: int = 250,
        base_features_threshold: int = 6,
        free_args_ratio_threshold: float = 0.5
    ):
        """
        初始化复杂度检验器
        
        Args:
            enabled: 是否启用复杂度检验
            symbol_length_threshold: 符号长度阈值
            base_features_threshold: 基础特征数量阈值
            free_args_ratio_threshold: 自由参数比例阈值
        """
        self.enabled = enabled
        self.symbol_length_threshold = symbol_length_threshold
        self.base_features_threshold = base_features_threshold
        self.free_args_ratio_threshold = free_args_ratio_threshold
    
    def check(self, expression: str) -> Tuple[bool, str]:
        """
        检查表达式复杂度
        
        Args:
            expression: 因子表达式
        
        Returns:
            Tuple[bool, str]: (是否通过, 反馈信息)
        """
        if not self.enabled:
            return True, "Complexity check disabled"
        
        try:
            from quantaalpha.factors.coder.factor_ast import (
                calculate_symbol_length, 
                count_base_features,
                count_free_args,
                count_all_nodes
            )
            
            feedback_parts = []
            passed = True
            
            # 符号长度检查
            symbol_length = calculate_symbol_length(expression)
            if symbol_length > self.symbol_length_threshold:
                passed = False
                feedback_parts.append(
                    f"Symbol Length (SL) Check Failed: {symbol_length} > {self.symbol_length_threshold}. "
                    f"Expression is too complex and may lead to overfitting."
                )
            
            # 基础特征检查
            num_base_features = count_base_features(expression)
            if num_base_features > self.base_features_threshold:
                passed = False
                feedback_parts.append(
                    f"Base Features (ER) Check Failed: {num_base_features} > {self.base_features_threshold}. "
                    f"Using too many raw features."
                )
            
            # 自由参数比例检查
            num_free_args = count_free_args(expression)
            num_all_nodes = count_all_nodes(expression)
            if num_all_nodes > 0:
                free_args_ratio = num_free_args / num_all_nodes
                if free_args_ratio > self.free_args_ratio_threshold:
                    passed = False
                    feedback_parts.append(
                        f"Free Args Ratio Check Failed: {free_args_ratio:.2%} > {self.free_args_ratio_threshold:.2%}. "
                        f"Factor is over-parameterized."
                    )
            
            if passed:
                return True, "Complexity check passed"
            else:
                return False, "\n".join(feedback_parts)
        
        except Exception as e:
            logger.warning(f"Complexity check failed with error: {e}")
            return True, f"Complexity check skipped due to error: {e}"


class RedundancyChecker:
    """
    因子冗余度检验器
    
    检查因子表达式是否与已有因子重复。
    """
    
    def __init__(
        self,
        enabled: bool = True,
        duplication_threshold: int = 5,
        factor_zoo_path: str = None
    ):
        """
        初始化冗余度检验器
        
        Args:
            enabled: 是否启用冗余度检验
            duplication_threshold: 重复子树阈值
            factor_zoo_path: 因子库路径
        """
        self.enabled = enabled
        self.duplication_threshold = duplication_threshold
        self.factor_zoo_path = factor_zoo_path
        self._factor_regulator = None
    
    @property
    def factor_regulator(self):
        """延迟加载FactorRegulator"""
        if self._factor_regulator is None:
            from quantaalpha.factors.regulator.factor_regulator import FactorRegulator
            self._factor_regulator = FactorRegulator(
                factor_zoo_path=self.factor_zoo_path,
                duplication_threshold=self.duplication_threshold
            )
        return self._factor_regulator
    
    def check(self, expression: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查表达式冗余度
        
        Args:
            expression: 因子表达式
        
        Returns:
            Tuple[bool, str, Dict]: (是否通过, 反馈信息, 详细信息)
        """
        if not self.enabled:
            return True, "Redundancy check disabled", {}
        
        try:
            # 检查是否可解析
            if not self.factor_regulator.is_parsable(expression):
                return False, f"Expression cannot be parsed: {expression}", {}
            
            # 评估表达式
            success, eval_dict = self.factor_regulator.evaluate(expression)
            if not success:
                return False, f"Failed to evaluate expression", {}
            
            # 检查重复性
            duplicated_size = eval_dict.get('duplicated_subtree_size', 0)
            if duplicated_size > self.duplication_threshold:
                matched_alpha = eval_dict.get('matched_alpha', 'Unknown')
                duplicated_subtree = eval_dict.get('duplicated_subtree', '')
                return False, (
                    f"Redundancy Check Failed: Duplicated subtree size ({duplicated_size}) "
                    f"exceeds threshold ({self.duplication_threshold}). "
                    f"Matched with: {matched_alpha}. Duplicated subtree: {duplicated_subtree}"
                ), eval_dict
            
            return True, "Redundancy check passed", eval_dict
        
        except Exception as e:
            logger.warning(f"Redundancy check failed with error: {e}")
            return True, f"Redundancy check skipped due to error: {e}", {}


class FactorQualityGate:
    """
    因子质量门控
    
    整合一致性检验、复杂度检验、冗余度检验，
    决定因子是否可以进入回测阶段。
    
    Integrates consistency check, complexity check, and redundancy check
    to determine if a factor can proceed to backtesting.
    """
    
    def __init__(
        self,
        consistency_checker: FactorConsistencyChecker = None,
        complexity_checker: ComplexityChecker = None,
        redundancy_checker: RedundancyChecker = None,
        consistency_enabled: bool = False,
        complexity_enabled: bool = True,
        redundancy_enabled: bool = True
    ):
        """
        初始化质量门控
        
        Args:
            consistency_checker: 一致性检验器实例
            complexity_checker: 复杂度检验器实例
            redundancy_checker: 冗余度检验器实例
            consistency_enabled: 是否启用一致性检验
            complexity_enabled: 是否启用复杂度检验
            redundancy_enabled: 是否启用冗余度检验
        """
        self.consistency_checker = consistency_checker or FactorConsistencyChecker(enabled=consistency_enabled)
        self.complexity_checker = complexity_checker or ComplexityChecker(enabled=complexity_enabled)
        self.redundancy_checker = redundancy_checker or RedundancyChecker(enabled=redundancy_enabled)
        
        # 更新启用状态
        self.consistency_checker.enabled = consistency_enabled
        self.complexity_checker.enabled = complexity_enabled
        self.redundancy_checker.enabled = redundancy_enabled
    
    def evaluate(
        self,
        hypothesis: str,
        factor_name: str,
        factor_description: str,
        factor_formulation: str,
        factor_expression: str,
        variables: Dict[str, str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        评估因子是否通过质量门控
        
        Args:
            hypothesis: 假设
            factor_name: 因子名称
            factor_description: 因子描述
            factor_formulation: 数学公式
            factor_expression: 符号表达式
            variables: 变量字典
        
        Returns:
            Tuple[bool, str, Dict]: (是否通过, 综合反馈, 详细结果)
        """
        results = {
            "consistency": None,
            "complexity": None,
            "redundancy": None,
            "corrected_expression": factor_expression,
            "corrected_description": factor_description
        }
        feedbacks = []
        all_passed = True
        
        # 1. 一致性检验
        if self.consistency_checker.enabled:
            consistency_result, corrected_expr, corrected_desc = self.consistency_checker.check_and_correct(
                hypothesis=hypothesis,
                factor_name=factor_name,
                factor_description=factor_description,
                factor_formulation=factor_formulation,
                factor_expression=factor_expression,
                variables=variables
            )
            results["consistency"] = consistency_result.to_dict()
            results["corrected_expression"] = corrected_expr
            results["corrected_description"] = corrected_desc
            
            if not self.consistency_checker.should_proceed_to_backtest(consistency_result):
                all_passed = False
                feedbacks.append(f"[Consistency] {consistency_result.overall_feedback}")
            
            # 使用修正后的表达式继续检验
            factor_expression = corrected_expr
        
        # 2. 复杂度检验
        if self.complexity_checker.enabled:
            complexity_passed, complexity_feedback = self.complexity_checker.check(factor_expression)
            results["complexity"] = {
                "passed": complexity_passed,
                "feedback": complexity_feedback
            }
            
            if not complexity_passed:
                all_passed = False
                feedbacks.append(f"[Complexity] {complexity_feedback}")
        
        # 3. 冗余度检验
        if self.redundancy_checker.enabled:
            redundancy_passed, redundancy_feedback, redundancy_details = self.redundancy_checker.check(factor_expression)
            results["redundancy"] = {
                "passed": redundancy_passed,
                "feedback": redundancy_feedback,
                "details": redundancy_details
            }
            
            if not redundancy_passed:
                all_passed = False
                feedbacks.append(f"[Redundancy] {redundancy_feedback}")
        
        # 综合反馈
        if all_passed:
            overall_feedback = f"Factor '{factor_name}' passed all quality gates."
            logger.info(overall_feedback)
        else:
            overall_feedback = f"Factor '{factor_name}' failed quality gates:\n" + "\n".join(feedbacks)
            logger.warning(overall_feedback)
        
        return all_passed, overall_feedback, results
