from pyparsing import Word, alphas, alphanums, infixNotation, opAssoc, oneOf, Optional, delimitedList, Forward, Group
from pyparsing import ParserElement, ParseException, ParseResults
from pyparsing import Regex, Combine, Literal
from dataclasses import dataclass
from typing import List, Union, Optional as Opt
from collections import defaultdict
import sys
import pandas as pd

# Enable packrat parsing for better performance
ParserElement.enablePackrat()

# Set higher recursion limit for complex expressions
sys.setrecursionlimit(4000)

# AST Node classes
@dataclass
class Node:
    def tree_str(self, level: int = 0) -> str:
        """Return a tree-like string representation with given indent level."""
        indent = "  " * level
        return f"{indent}{self._node_str()}"
    
    def _node_str(self) -> str:
        """Basic string representation of the node for tree view."""
        return str(self)
        
    def print_tree(self):
        """Print the AST in a tree structure."""
        print(self.tree_str())

@dataclass
class VarNode(Node):
    name: str
    
    def __str__(self):
        return self.name
        
    def _node_str(self):
        return f"VAR({self.name})"

@dataclass
class NumberNode(Node):
    value: float
    
    def __str__(self):
        return str(self.value)
        
    def _node_str(self):
        return f"NUM({self.value})"

@dataclass
class FunctionNode(Node):
    name: str
    args: List[Node]
    
    def __str__(self):
        args_str = ", ".join(str(arg) for arg in self.args)
        return f"{self.name}({args_str})"
        
    def _node_str(self):
        return f"FUNC({self.name})"
        
    def tree_str(self, level: int = 0) -> str:
        indent = "  " * level
        result = [f"{indent}{self._node_str()}"]
        for arg in self.args:
            result.append(arg.tree_str(level + 1))
        return "\n".join(result)

@dataclass
class BinaryOpNode(Node):
    op: str
    left: Node
    right: Node
    
    def __str__(self):
        return f"({str(self.left)} {self.op} {str(self.right)})"
        
    def _node_str(self):
        return f"OP({self.op})"
        
    def tree_str(self, level: int = 0) -> str:
        indent = "  " * level
        result = [f"{indent}{self._node_str()}"]
        result.append(self.left.tree_str(level + 1))
        result.append(self.right.tree_str(level + 1))
        return "\n".join(result)

@dataclass
class ConditionalNode(Node):
    condition: Node
    true_expr: Node
    false_expr: Node
    
    def __str__(self):
        return f"({str(self.condition)} ? {str(self.true_expr)} : {str(self.false_expr)})"
        
    def _node_str(self):
        return "CONDITIONAL"
        
    def tree_str(self, level: int = 0) -> str:
        indent = "  " * level
        result = [f"{indent}{self._node_str()}"]
        result.append(self.condition.tree_str(level + 1))
        result.append(self.true_expr.tree_str(level + 1))
        result.append(self.false_expr.tree_str(level + 1))
        return "\n".join(result)

@dataclass
class UnaryOpNode(Node):
    """一元运算符节点，支持 -x 这样的表达式"""
    op: str
    operand: Node
    
    def __str__(self):
        return f"({self.op}{str(self.operand)})"
        
    def _node_str(self):
        return f"UNARY({self.op})"
        
    def tree_str(self, level: int = 0) -> str:
        indent = "  " * level
        result = [f"{indent}{self._node_str()}"]
        result.append(self.operand.tree_str(level + 1))
        return "\n".join(result)

# Basic elements definition
var = Combine(Optional(Literal("$")) + Word(alphas, alphanums + "_"))
number = Regex(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")

# Operators definition
mul_div = oneOf("* /")
add_sub = oneOf("+ -")
comparison = oneOf("> < >= <= == !=")
logical_and = oneOf("&& &")
logical_or = oneOf("|| |")
conditional = ("?", ":")

def create_var_node(tokens):
    return VarNode(tokens[0])

def create_number_node(tokens):
    return NumberNode(float(tokens[0]))

def create_function_node(tokens):
    name = tokens[0]  # function name
    args = tokens[2:-1]  # skip parentheses
    
    def unwrap(arg):
        if isinstance(arg, (list, ParseResults)):
            if len(arg) == 1:
                return unwrap(arg[0])
            return [unwrap(x) for x in arg][0]  # first element
        return arg
    
    processed_args = [unwrap(arg) for arg in args]
    # All args should be Node classes
    assert all(isinstance(arg, Node) for arg in processed_args), f"Invalid args: {processed_args}"
    return FunctionNode(name, processed_args)

def create_binary_op_node(tokens):
    tokens = tokens[0]
    def unwrap(arg):
        if isinstance(arg, (list, ParseResults)):
            if len(arg) == 1:
                return unwrap(arg[0])
            return [unwrap(x) for x in arg]
        return arg
    
    if len(tokens) == 3:
        return BinaryOpNode(tokens[1], unwrap(tokens[0]), unwrap(tokens[2]))
    
    result = unwrap(tokens[0])
    for i in range(1, len(tokens)-1, 2):
        result = BinaryOpNode(tokens[i], result, unwrap(tokens[i+1]))
    return result

def create_conditional_node(tokens):
    tokens = tokens[0]
    def unwrap(arg):
        if isinstance(arg, (list, ParseResults)):
            if len(arg) == 1:
                return unwrap(arg[0])
            return [unwrap(x) for x in arg]
        return arg
    
    return ConditionalNode(
        unwrap(tokens[0]),
        unwrap(tokens[2]),
        unwrap(tokens[4])
    )

def create_unary_op_node(tokens):
    """创建一元运算符节点，处理 -x 这样的表达式"""
    tokens = tokens[0]
    def unwrap(arg):
        if isinstance(arg, (list, ParseResults)):
            if len(arg) == 1:
                return unwrap(arg[0])
            return [unwrap(x) for x in arg]
        return arg
    
    # tokens 格式: ['-', operand]
    op = tokens[0]
    operand = unwrap(tokens[1])
    return UnaryOpNode(op, operand)

# Expression parser definition
expr = Forward()

# Basic elements
var.setParseAction(create_var_node)
number.setParseAction(create_number_node)

# Function call
function_call = var + "(" + Optional(delimitedList(expr)) + ")"
function_call.setParseAction(create_function_node)

# Operands
operand = function_call | var | number | ("(" + expr + ")").setParseAction(lambda tokens: tokens[1])

# Unary operators (highest precedence)
unary_minus = Literal("-")

# Complete expression
expr <<= infixNotation(
    operand,
    [
        (unary_minus, 1, opAssoc.RIGHT, create_unary_op_node),  # 一元负号，最高优先级
        (mul_div, 2, opAssoc.LEFT, create_binary_op_node),
        (add_sub, 2, opAssoc.LEFT, create_binary_op_node),
        (comparison, 2, opAssoc.LEFT, create_binary_op_node),
        (logical_and, 2, opAssoc.LEFT, create_binary_op_node),
        (logical_or, 2, opAssoc.LEFT, create_binary_op_node),
        (conditional, 3, opAssoc.RIGHT, create_conditional_node),
    ]
)

def parse_expression(text: str) -> Node:
    """Parse an expression and return its AST."""
    try:
        result = expr.parseString(text, parseAll=True)
        return result[0]  # Extract the first element from ParseResults
    except ParseException as e:
        raise ValueError(f"Failed to parse expression: {str(e)}")
    
    
    
    
    
    
def are_nodes_equal(node1: Node, node2: Node) -> bool:
    """比较两个节点是否相等"""
    if type(node1) != type(node2):
        return False
        
    if isinstance(node1, NumberNode):
        return node1.value == node2.value
    elif isinstance(node1, VarNode):
        return node1.name == node2.name
    elif isinstance(node1, FunctionNode):
        return node1.name == node2.name and len(node1.args) == len(node2.args)
    elif isinstance(node1, BinaryOpNode):
        return node1.op == node2.op
    elif isinstance(node1, ConditionalNode):
        return True  # 条件节点本身相等，子节点会在递归中比较
    return False

@dataclass
class SubtreeMatch:
    root1: Node  # 第一个树中的子树根节点
    root2: Node  # 第二个树中的子树根节点
    size: int    # 子树大小（节点数）
    
    def __str__(self):
        return f"Match(size={self.size}):\n  Tree1: {str(root1)}\n  Tree2: {str(root2)}"

def find_largest_common_subtree(root1: Node, root2: Node) -> Opt[SubtreeMatch]:
    """查找两棵树之间的最大公共子树"""
    
    def get_subtree_size(node: Node) -> int:
        """计算以给定节点为根的子树大小"""
        if isinstance(node, (NumberNode, VarNode)):
            return 1
        elif isinstance(node, FunctionNode):
            return 1 + sum(get_subtree_size(arg) for arg in node.args)
        elif isinstance(node, BinaryOpNode):
            return 1 + get_subtree_size(node.left) + get_subtree_size(node.right)
        elif isinstance(node, ConditionalNode):
            return 1 + get_subtree_size(node.condition) + \
                   get_subtree_size(node.true_expr) + \
                   get_subtree_size(node.false_expr)
        return 0

    def get_all_subtrees(root: Node) -> List[Node]:
        """获取树中的所有子树根节点"""
        result = [root]
        if isinstance(root, FunctionNode):
            for arg in root.args:
                result.extend(get_all_subtrees(arg))
        elif isinstance(root, BinaryOpNode):
            result.extend(get_all_subtrees(root.left))
            result.extend(get_all_subtrees(root.right))
        elif isinstance(root, ConditionalNode):
            result.extend(get_all_subtrees(root.condition))
            result.extend(get_all_subtrees(root.true_expr))
            result.extend(get_all_subtrees(root.false_expr))
        return result

    def is_commutative_op(op: str) -> bool:
        """判断是否为可交换操作符"""
        return op in {'+', '*', '==', '!=', '&', '&&', '|', '||'}

    def are_subtrees_equal(node1: Node, node2: Node) -> bool:
        """递归比较两个子树是否完全相等，考虑可交换操作"""
        if not are_nodes_equal(node1, node2):
            return False
            
        if isinstance(node1, (NumberNode, VarNode)):
            return True
        elif isinstance(node1, FunctionNode):
            return all(are_subtrees_equal(arg1, arg2) 
                      for arg1, arg2 in zip(node1.args, node2.args))
        elif isinstance(node1, BinaryOpNode):
            # 对于可交换操作符，尝试两种顺序
            if is_commutative_op(node1.op):
                return (are_subtrees_equal(node1.left, node2.left) and 
                        are_subtrees_equal(node1.right, node2.right)) or \
                       (are_subtrees_equal(node1.left, node2.right) and 
                        are_subtrees_equal(node1.right, node2.left))
            else:
                return are_subtrees_equal(node1.left, node2.left) and \
                       are_subtrees_equal(node1.right, node2.right)
        elif isinstance(node1, ConditionalNode):
            return are_subtrees_equal(node1.condition, node2.condition) and \
                   are_subtrees_equal(node1.true_expr, node2.true_expr) and \
                   are_subtrees_equal(node1.false_expr, node2.false_expr)
        return False

    # 获取所有可能的子树
    subtrees1 = get_all_subtrees(root1)
    subtrees2 = get_all_subtrees(root2)
    
    # 找到最大的公共子树
    max_match = None
    max_size = 0
    
    for st1 in subtrees1:
        size1 = get_subtree_size(st1)
        if size1 <= max_size:
            continue
            
        for st2 in subtrees2:
            size2 = get_subtree_size(st2)
            if size2 != size1 or size2 <= max_size:
                continue
                
            if are_subtrees_equal(st1, st2):
                max_size = size1
                max_match = SubtreeMatch(st1, st2, size1)
    
    return max_match

def compare_expressions(expr1: str, expr2: str) -> Opt[SubtreeMatch]:
    """Compare two expressions and return their largest common subtree"""
    tree1 = parse_expression(expr1)
    tree2 = parse_expression(expr2)
    return find_largest_common_subtree(tree1, tree2)
    
    
    
def match_alphazoo(prop_expr, factor_df):
    max_size = 0
    matched_subtree = None
    matched_alpha = None
    for index, (name, alpha_expr) in factor_df.iterrows():
        try:
            match = compare_expressions(prop_expr, alpha_expr)
            if match is not None and match.size > max_size:
                 max_size = match.size
                 matched_subtree = match.root1
                 matched_alpha = alpha_expr
        except Exception as e:
            print(f"Error comparing alpha \"{alpha_expr}\": \n {e}")
    return max_size, matched_subtree, matched_alpha
    


def count_free_args(expr: str) -> int:
    """
    Count the number of NumberNode instances (numeric constants) in the given expression.
    
    Args:
        expr: A string representing a mathematical expression
        
    Returns:
        int: The number of numeric constants in the expression
    """
    tree = parse_expression(expr)
    return count_number_nodes(tree)

def count_number_nodes(node: Node) -> int:
    """
    Recursively count the number of NumberNode instances in an AST.
    
    Args:
        node: The root node of the AST or sub-tree
        
    Returns:
        int: The number of NumberNode instances in the tree
    """
    if isinstance(node, NumberNode):
        return 1
    elif isinstance(node, VarNode):
        return 0
    elif isinstance(node, FunctionNode):
        return sum(count_number_nodes(arg) for arg in node.args)
    elif isinstance(node, BinaryOpNode):
        return count_number_nodes(node.left) + count_number_nodes(node.right)
    elif isinstance(node, ConditionalNode):
        return (count_number_nodes(node.condition) + 
                count_number_nodes(node.true_expr) + 
                count_number_nodes(node.false_expr))
    return 0



def count_unique_vars(expr: str) -> int:
    """
    Count the number of unique variable names in the given expression.
    
    Args:
        expr: A string representing a mathematical expression
        
    Returns:
        int: The number of unique variable names in the expression
    """
    tree = parse_expression(expr)
    unique_vars = set()
    collect_unique_vars(tree, unique_vars)
    return len(unique_vars)

def collect_unique_vars(node: Node, unique_vars: set) -> None:
    """
    Recursively collect unique variable names from an AST.
    
    Args:
        node: The root node of the AST or sub-tree
        unique_vars: A set to collect unique variable names
    """
    if isinstance(node, VarNode):
        # Only add actual data variables, not function names
        if node.name.startswith('$'):
            unique_vars.add(node.name)
    elif isinstance(node, NumberNode):
        pass  # No variables in number nodes
    elif isinstance(node, FunctionNode):
        # Don't add the function name itself as a variable
        for arg in node.args:
            collect_unique_vars(arg, unique_vars)
    elif isinstance(node, BinaryOpNode):
        collect_unique_vars(node.left, unique_vars)
        collect_unique_vars(node.right, unique_vars)
    elif isinstance(node, ConditionalNode):
        collect_unique_vars(node.condition, unique_vars)
        collect_unique_vars(node.true_expr, unique_vars)
        collect_unique_vars(node.false_expr, unique_vars)


def count_all_nodes(expr: str) -> int:
    """
    Count the number of Node instances (numeric constants) in the given expression.
    
    Args:
        expr: A string representing a mathematical expression
        
    Returns:
        int: The number of numeric constants in the expression
    """
    tree = parse_expression(expr)
    return count_nodes(tree)


def calculate_symbol_length(expr: str) -> int:
    """
    Calculate the symbol length (SL) of an expression.
    Symbol length is the length of the expression string, which measures structural complexity.
    
    Args:
        expr: A string representing a mathematical expression
        
    Returns:
        int: The symbol length of the expression
    """
    return len(expr.strip())


def count_base_features(expr: str) -> int:
    """
    Count the number of unique base features (raw variables starting with $) used in the expression.
    This corresponds to ER(f, h) in the paper - the feature usage penalty.
    
    Args:
        expr: A string representing a mathematical expression
        
    Returns:
        int: The number of unique base features (e.g., $close, $open, $high, $low, $volume)
    """
    tree = parse_expression(expr)
    base_features = set()
    collect_base_features(tree, base_features)
    return len(base_features)


def collect_base_features(node: Node, base_features: set) -> None:
    """
    Recursively collect base feature names (variables starting with $) from an AST.
    
    Args:
        node: The root node of the AST or sub-tree
        base_features: A set to collect unique base feature names
    """
    if isinstance(node, VarNode):
        # Only add base features (raw variables starting with $)
        if node.name.startswith('$'):
            base_features.add(node.name)
    elif isinstance(node, NumberNode):
        pass  # No features in number nodes
    elif isinstance(node, FunctionNode):
        # Don't add the function name itself as a feature
        for arg in node.args:
            collect_base_features(arg, base_features)
    elif isinstance(node, BinaryOpNode):
        collect_base_features(node.left, base_features)
        collect_base_features(node.right, base_features)
    elif isinstance(node, ConditionalNode):
        collect_base_features(node.condition, base_features)
        collect_base_features(node.true_expr, base_features)
        collect_base_features(node.false_expr, base_features)


def count_nodes(node: Node) -> int:
    """
    Recursively count the number of Node instances in an AST.
    
    Args:
        node: The root node of the AST or sub-tree
        
    Returns:
        int: The number of Node instances in the tree
    """
    if isinstance(node, (NumberNode, VarNode)):
        return 1
    elif isinstance(node, FunctionNode):
        return 1 + sum(count_nodes(arg) for arg in node.args)
    elif isinstance(node, BinaryOpNode):
        return 1 + count_nodes(node.left) + count_nodes(node.right)
    elif isinstance(node, ConditionalNode):
        return 1 + (count_nodes(node.condition) + 
                    count_nodes(node.true_expr) + 
                    count_nodes(node.false_expr))
    return 0


# Example usage:
if __name__ == "__main__":
    expr1 = "(($close - TS_MIN($low, 14)) / (TS_MAX($high, 14) - TS_MIN($low, 14) + 1e-8))"
    count = count_free_args(expr1)
    print(f"Number of NumberNode instances in expression: {count}")  # Should print 3 (14, 1e-8, and 100)
    count = count_unique_vars(expr1)
    print(f"Number of unique variables in expression: {count}")  
    count = count_all_nodes(expr1)
    print(f"Number of Node instances in expression: {count}") 

# if __name__ == "__main__":
#     # Test cases
#     expr1 = "(($close - TS_MIN($low, 14)) / (TS_MAX($high, 14) - TS_MIN($low, 14) + 1e-8)) * 100"
#     expr2 = "(TS_MAX($high, 14) - TS_MIN($low, 14)) * STD($close, 20) / MEAN($volume, 10)"
#     match = compare_expressions(expr1, expr2)
#     factor_df = pd.read_csv("factor_zoo/alpha101.csv", index_col=None)
    
    
#     max_size = 0
#     matched_subtree = None
#     matched_alpha = None
#     for index, (name, alpha_expr) in factor_df.iterrows():
#         try:
#             match = compare_expressions(expr1, alpha_expr)
#             if match is not None and match.size > max_size:
#                  max_size = match.size
#                  matched_subtree = match.root1
#                  matched_alpha = alpha_expr
#         except Exception as e:
#             print(f"Error comparing alpha \"{alpha_expr}\": \n {e}")
            

                 
#     print(max_size)
#     print(matched_subtree)
#     print(matched_alpha)