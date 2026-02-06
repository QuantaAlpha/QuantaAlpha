import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from quantaalpha.core.evaluation import Evaluator
from quantaalpha.log import logger
from quantaalpha.core.scenario import Scenario
from quantaalpha.factors.coder.factor_ast import (
    match_alphazoo, count_free_args, count_unique_vars, count_all_nodes,
    calculate_symbol_length, count_base_features
)
from quantaalpha.factors.coder.expr_parser import parse_expression

class FactorRegulator(Evaluator):
    """
    FactorRegulator class to evaluate expressions for duplication and manage the factor zoo database.
    This class provides functionality to detect duplicated subtrees in factor expressions
    and ensure new factors maintain appropriate originality.
    """
    
    def __init__(self, factor_zoo_path: str = None, duplication_threshold: int = 8,
                 symbol_length_threshold: int = 300, base_features_threshold: int = 6):
        """
        Initialize the FactorRegulator with a reference to the factor zoo.
        
        Args:
            factor_zoo_path (str): Path to the CSV file containing the factor zoo database.
            duplication_threshold (int): Threshold for duplication detection.
            symbol_length_threshold (int): Maximum allowed symbol length (SL) for expressions.
            base_features_threshold (int): Maximum allowed number of unique base features (ER).
        """
        super().__init__(None)
        self.factor_zoo_path = factor_zoo_path
        if factor_zoo_path:
            self.alphazoo = pd.read_csv(factor_zoo_path, index_col=None)
        else:
            self.alphazoo = pd.DataFrame()
        self.duplication_threshold = duplication_threshold
        self.symbol_length_threshold = symbol_length_threshold
        self.base_features_threshold = base_features_threshold
        self.new_factors = []
        
    
        
    def is_parsable(self, expression: str) -> bool:
        """
        Checks if an expression can be successfully parsed.
        
        Args:
            expression (str): The factor expression to check.
            
        Returns:
            bool: True if the expression can be parsed, False otherwise.
        """
        try:
            parse_expression(expression)
            return True
        except Exception as e:
            logger.error(f"Failed to parse expression: {expression}. Error: {str(e)}")
            return False
        
    def evaluate(self, expression: str) -> Tuple[int, str, Optional[str]]:
        """
        Evaluates an expression for duplication with existing factors in the factor zoo.
        
        Args:
            expression (str): The factor expression to evaluate.
            
        Returns:
            Tuple containing:
                - duplicated_subtree_size (int): Size of the duplicated subtree
                - duplicated_subtree (str): The duplicated subtree expression
                - matched_alpha (str or None): Name of the matched alpha if available
        """
        try:
            # Check for duplication
            duplicated_subtree_size, duplicated_subtree, matched_alpha = match_alphazoo(
                expression, self.alphazoo
            )
            
            num_free_args = count_free_args(expression)
            num_unique_vars = count_unique_vars(expression)
            num_all_nodes = count_all_nodes(expression)
            symbol_length = calculate_symbol_length(expression)
            num_base_features = count_base_features(expression)
            
            logger.info(f"""
                        Evaluated expr: {expression}
                        Duplicated Size: {duplicated_subtree_size}
                        Duplicated Subtree: {duplicated_subtree}
                        # Free Args: {num_free_args}
                        # Unique Vars: {num_unique_vars}
                        Symbol Length (SL): {symbol_length}
                        # Base Features (ER): {num_base_features}
                        """)
            
            eval_dict = {
                "expr": expression,
                "duplicated_subtree_size": duplicated_subtree_size, 
                "duplicated_subtree": duplicated_subtree,
                "matched_alpha": matched_alpha,
                "num_free_args": num_free_args,
                "num_unique_vars": num_unique_vars,
                "num_all_nodes": num_all_nodes,
                "symbol_length": symbol_length,
                "num_base_features": num_base_features
                }
            
            return True, eval_dict
            
        except Exception as e:
            logger.error(f"Failed to evaluate expression: {expression}. Error: {str(e)}")
            return False, None
    
    
    def is_expression_acceptable(self, eval_dict) -> bool:
        """
        Determines if an expression is acceptable based on the duplication threshold,
        the ratio of num_free_args and num_unique_vars to the total number of nodes,
        symbol length (SL), and base features count (ER).
        
        This implements the complexity regularization R_g(f, h) from the paper:
        R_g(f, h) = α₁·SL(f) + α₂·PC(f) + α₃·ER(f, h)
        
        Args:
            eval_dict (dict): Dictionary containing evaluation results of the expression.
            
        Returns:
            bool: True if the expression is acceptable, False otherwise.
        """
        # Condition 1: Check if the duplicated subtree size is within the threshold
        cond1 = eval_dict['duplicated_subtree_size'] <= self.duplication_threshold
        
        # Get the number of free arguments, unique variables, and total nodes
        num_free_args = eval_dict['num_free_args']
        num_unique_vars = eval_dict['num_unique_vars']
        num_all_nodes = eval_dict['num_all_nodes']
        symbol_length = eval_dict.get('symbol_length', 0)
        num_base_features = eval_dict.get('num_base_features', 0)
        
        # Avoid division by zero and invalid ratios
        if num_all_nodes == 0:
            logger.warning(f"Expression has no nodes: {eval_dict['expr']}")
            return False
        
        # Calculate ratios
        free_args_ratio = float(num_free_args) / float(num_all_nodes)
        unique_vars_ratio = float(num_unique_vars) / float(num_all_nodes)
        
        # Ensure ratios are within valid range (0 <= ratio < 1)
        if free_args_ratio >= 1 or unique_vars_ratio >= 1:
            logger.warning(f"Invalid ratio detected: free_args_ratio={free_args_ratio}, unique_vars_ratio={unique_vars_ratio}")
            return False
        
        # Condition 2: Ensure the ratio of num_free_args to total nodes is not too high using -log(1 - ratio)
        # -log(1 - x) increases as x increases, so we set a threshold (e.g., -log(1 - 0.5) ≈ 0.693)
        # This ensures the ratio is not too high (e.g., x < 0.5)
        cond2 = -np.log(1 - free_args_ratio) < 0.693  # Threshold for x < 0.5
        
        # Condition 3: Ensure the ratio of num_unique_vars to total nodes is not too high using -log(1 - ratio)
        cond3 = -np.log(1 - unique_vars_ratio) < 0.693  # Threshold for x < 0.5
        
        # Condition 4: Check symbol length (SL) - expression should not be too long
        cond4 = symbol_length <= self.symbol_length_threshold
        
        # Condition 5: Check base features count (ER) - should not use too many raw features
        # Using log(1 + |F_f|) penalty as in the paper
        cond5 = num_base_features <= self.base_features_threshold
        
        # The expression is acceptable if all conditions are met
        return cond1 and cond2 and cond3 and cond4 and cond5
    
            
    def add_factor(self, factor_name: str, factor_expression: str) -> bool:
        """
        Adds a new factor to the in-memory factor zoo if it passes the duplication check.
        
        Args:
            factor_name (str): Name of the new factor.
            factor_expression (str): Expression of the new factor.
            
        Returns:
            bool: True if the factor was added, False otherwise.
        """
        new_factor = pd.DataFrame({
                'factor_name': factor_name,
                'factor_expression': factor_expression
                })
            
        self.alphazoo = pd.concat([self.alphazoo, new_factor])
        self.new_factors.append((factor_name, factor_expression))
        logger.info(f"Added new factor: {factor_name} with expression: {factor_expression}")
            
    def save_factor_zoo(self, output_path: Optional[str] = None) -> None:
        """
        Saves the updated factor zoo to a CSV file.
        
        Args:
            output_path (str, optional): Path to save the updated factor zoo.
                                         If None, updates the original file.
        """
        save_path = output_path if output_path else self.factor_zoo_path
        self.alphazoo.to_csv(save_path, index=False)
        logger.info(f"Saved updated factor zoo to {save_path}")
        
    def get_new_factors(self) -> List[Tuple[str, str]]:
        """
        Returns the list of new factors added during this session.
        
        Returns:
            List[Tuple[str, str]]: List of (factor_name, factor_expression) tuples.
        """
        return self.new_factors