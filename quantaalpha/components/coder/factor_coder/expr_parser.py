from pyparsing import Word, alphas, alphanums, infixNotation, opAssoc, oneOf, Optional, delimitedList, Forward, Group
from pyparsing import ParseException
from pyparsing import Regex, Combine, Literal
import sys
import re
import numpy as np

# 引入pyparsing自带的cache功能
# 加快function_call = var + '(' + Optional(delimitedList(expr)) + ')'这种嵌套式的pyparsing解析器
from pyparsing import ParserElement
ParserElement.enablePackrat()

sys.setrecursionlimit(5000)  # 设置更高的递归深度限制

# 定义基本元素
var = (
    Combine(Optional(Literal("$")) + Word(alphas, alphanums + "_"))
).setName("variable")
# var = Word(alphas, alphanums + "_")

# 定义数字的正则表达式
# 正则表达式匹配整数和小数，可以有正负号，以及科学计数法
number_pattern = r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?"
number = Regex(number_pattern)

# 定义操作符
mul_div = oneOf("* /", useRegex=True)
add_minus = oneOf("+ -")
comparison_op = oneOf("> < >= <= == !=")
logical_and = oneOf("&& &")
logical_or = oneOf("|| |")
conditional_op = ("?", ":")


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

# 展平嵌套的 ParseResults 为字符串
def flatten_nested_tokens(tokens):
    # import pdb; pdb.set_trace()
    flattened = []
    for token in tokens:
        if isinstance(token, str):
            flattened.append(token)
        elif isinstance(token, list):
            flattened.extend(flatten_nested_tokens(token))
        else:  # ParseResults
            flattened.extend(flatten_nested_tokens(token.asList()))
    return flattened




def parse_arith_op(s, loc, tokens):
    # tokens[0] 包含整个运算表达式的分解
    # 因为操作符定义为左结合，我们可以从左到右递归处理tokens列表
    def recursive_build_expression(tokens):
        if len(tokens) == 3:
            A, op, B = tokens
            # 构建表达式
            return build_expression(A, op, B)
        else:
            left = tokens[:-2]
            op = tokens[-2]
            right = tokens[-1]
            left_expr = recursive_build_expression(left)
            return build_expression(left_expr, op, right)
        
    def build_expression(A, op, B):
        A = ''.join(flatten_nested_tokens([A]))
        B = ''.join(flatten_nested_tokens([B]))
        A_is_number = is_number(A)
        B_is_number = is_number(B)
        
        ## 任意一个操作数都是数字
        if A_is_number or B_is_number:
            return f"{A}{op}{B}"
        
        ## 两个操作数都是pd变量
        else:
            if op == '+':
                return f'ADD({A}, {B})'
                # return f'np.add({A}, {B})'
            elif op == '-':
                return f'SUBTRACT({A}, {B})'
                # return f'np.subtract({A}, {B})'
            elif op == '*':
                return f'MULTIPLY({A}, {B})'
                # return f'np.multiply({A}, {B})'
            elif op == '/':
                return f'DIVIDE({A}, {B})'
                # return f'np.divide({A}, {B})'
            else:
                raise NotImplementedError(f'arith op \'{op}\' is not implemented')
            # 操作数2是BENCHMARKINDEX (pd.Series)，而操作数1不是BENCHMARKINDEX (pd.Series)的情况下，Series必须要放在第二操作数，否则会报错
            # if 'BENCHMARKINDEX' in A and 'BENCHMARKINDEX' not in B:
            #     if op == '+':
            #         return f'({B}).add({A}, axis=0)'
            #     elif op == '-':
            #         return f'(-1*{(B)}).add({A}, axis=0)'
            #     elif op == '*':
            #         return f'({B}).mul({A}, axis=0)'
            #     elif op == '/':
            #         return f'(1/{(B)}).mul({A}, axis=0)'
            #     else:
            #         raise NotImplementedError(f'arith op \'{op}\' is not implemented')
            # else:
            #     if op == '+':
            #         return f'({A}).add({B}, axis=0)'
            #     elif op == '-':
            #         return f'({A}).sub({B}, axis=0)'
            #     elif op == '*':
            #         return f'({A}).mul({B}, axis=0)'
            #     elif op == '/':
            #         return f'({A}).div({B}, axis=0)'
            #     else:
            #         raise NotImplementedError(f'arith op \'{op}\' is not implemented')
    
    return recursive_build_expression(tokens[0])

# def parse_arith_op(s, loc, tokens):
#     A = ''.join(flatten_nested_tokens(tokens[0][0]))
#     op = ''.join(flatten_nested_tokens(tokens[0][1]))
#     B = ''.join(flatten_nested_tokens(tokens[0][2]))

#     # 检查操作数是否存在
#     if A == '' or B == '':
#         raise ParseException(s, loc, f"运算符 '{op}' 缺少操作数")
    
#     # 检查操作数是否为数字
#     A_is_number = is_number(A)
#     B_is_number = is_number(B)
    
#     # 根据操作数类型选择操作
    
#     ## 任意一个操作数都是数字
#     if A_is_number or B_is_number:
#         return f"{A}{op}{B}"
    
#     ## 两个操作数都是pd变量
#     else:
#         # 操作数2是BENCHMARKINDEX (pd.Series)，而操作数1不是BENCHMARKINDEX (pd.Series)的情况下，Series必须要放在第二操作数，否则会报错
#         if 'BENCHMARKINDEX' in A and 'BENCHMARKINDEX' not in B:
#             if op == '+':
#                 return f'({B}).add({A}, axis=0)'
#             elif op == '-':
#                 return f'(-1*{(B)}).add({A}, axis=0)'
#             elif op == '*':
#                 return f'({B}).mul({A}, axis=0)'
#             elif op == '/':
#                 return f'(1/{(B)}).mul({A}, axis=0)'
#             else:
#                 raise NotImplementedError(f'arith op \'{op}\' is not implemented')
#         else:
#             if op == '+':
#                 return f'({A}).add({B}, axis=0)'
#             elif op == '-':
#                 return f'({A}).sub({B}, axis=0)'
#             elif op == '*':
#                 return f'({A}).mul({B}, axis=0)'
#             elif op == '/':
#                 return f'({A}).div({B}, axis=0)'
#             else:
#                 raise NotImplementedError(f'arith op \'{op}\' is not implemented')


# 定义条件表达式的解析函数
def parse_conditional_expression(s, loc, tokens):
    A, B, C = tokens[0][0], tokens[0][2], tokens[0][4]
    # 将 A, B, C 转换为字符串
    A = ''.join(flatten_nested_tokens(A))
    B = ''.join(flatten_nested_tokens(B))
    C = ''.join(flatten_nested_tokens(C))

    # 使用 WHERE 函数处理索引对齐
    # 优先使用条件 A 的索引，如果 A 不是 DataFrame/Series，则使用 B 或 C 的索引
    return f"WHERE({A}, {B}, {C})"

# 定义比较运算符的解析函数
def parse_comparison_op(s, loc, tokens):
    """解析比较操作符，转换为函数调用以处理索引对齐"""
    def recursive_build_comparison(tokens):
        if len(tokens) == 3:
            A, op, B = tokens
            return build_comparison(A, op, B)
        else:
            left = tokens[:-2]
            op = tokens[-2]
            right = tokens[-1]
            left_expr = recursive_build_comparison(left)
            return build_comparison(left_expr, op, right)
    
    def build_comparison(A, op, B):
        A = ''.join(flatten_nested_tokens([A]))
        B = ''.join(flatten_nested_tokens([B]))
        A_is_number = is_number(A)
        B_is_number = is_number(B)
        
        # 如果都是数字，直接比较
        if A_is_number and B_is_number:
            return f"{A}{op}{B}"
        
        # 映射操作符到函数名
        op_map = {
            '>': 'GT',
            '<': 'LT',
            '>=': 'GE',
            '<=': 'LE',
            '==': 'EQ',
            '!=': 'NE'
        }
        
        func_name = op_map.get(op)
        if func_name:
            return f"{func_name}({A}, {B})"
        else:
            raise NotImplementedError(f"比较操作符 '{op}' 未实现")
    
    return recursive_build_comparison(tokens[0])

# 定义逻辑运算符的解析函数
def parse_logical_expression(s, loc, tokens):
    # tokens[0] 包含整个表达式的分解，可能包括嵌套的列表
    # 由于操作符定义为左结合，我们可以递归地展开tokens列表
    def recursive_flatten(tokens):
        if len(tokens) == 1:
            return ''.join(flatten_nested_tokens([tokens[0]]))
        else:
            left = tokens[0]
            operator = tokens[1]
            # right = tokens[2]
            left_str = ''.join(flatten_nested_tokens([left]))
            right_str = recursive_flatten(tokens[2:])
            if operator in ["||", "|"]: 
                return f"OR({left_str}, {right_str})"
                # return f"({left_str}) | ({right_str})"
            elif operator in ["&&", "&"]:
                return f"AND({left_str}, {right_str})"
                # return f"({left_str}) & ({right_str})"
    
    return recursive_flatten(tokens[0])


# 定义函数调用解析函数
def parse_function_call(s, loc, tokens):
    # unary_operator = tokens[0]
    function_name = tokens[0]
    arguments = tokens[2:-1] 
    # import pdb; pdb.set_trace()


    # 处理参数列表中的每个参数
    arguments_flat = []
    # import pdb; pdb.set_trace()
    for arg in arguments:
        if isinstance(arg, str):
            arguments_flat.append(arg)
        else:
            # 如果参数是嵌套的表达式或函数调用，递归处理
            flattened_arg = ''.join(flatten_nested_tokens(arg))
            arguments_flat.append(flattened_arg)
    arguments_str = ','.join(arguments_flat)
    return f"{function_name}({arguments_str})"

# 先定义一个 Forward 对象以便在定义 function_call 时引用
expr = Forward()

# 定义函数调用
## 定义可选的一元操作符，这里使用 oneOf 选择器来匹配 "+" 或 "-"
unary_op = Optional(oneOf("+ -")).setParseAction(lambda t: t[0] if t else '')
function_call = var + '(' + Optional(delimitedList(expr)) + ')'  # 使用 expr
function_call.setParseAction(parse_function_call)
nested_expr = Group('(' + expr + ')')
# sign_var = unary_op + var

# 更新操作数，以包含函数调用
operand =  Group(unary_op + (function_call | var | number | nested_expr | expr))

# unary_operand = oneOf("+ -") + operand
# unary_operand.setParseAction(lambda tokens: ''.join(tokens))
# operand = (unary_operand | function_call | var | number )

# 使用新的 flatten_nested_tokens 函数
def parse_entire_expression(s, loc, tokens):
    # import pdb; pdb.set_trace()
    return ''.join(flatten_nested_tokens(tokens))


def check_for_invalid_operators(expression):
    valid_operators = {"(", ")", ",", "+", "-", "*", "/", "&&", "||", "&", "|", ">", "<", ">=", "<=", "==", "!=", "?", ":", "."}
    # 使用正则表达式查找所有的运算符
    pattern = r'([+\-*/,><?:.]{2,})|([><=!&|^`~@#%\\;{}[\]"\'\\]+)' # ([|&=]{3,})|
    found_operators_tuples = re.findall(pattern, expression)
    found_operators = [operator for tup in found_operators_tuples for operator in tup if operator]
    invalid_operators = set(found_operators) - valid_operators
    
    if invalid_operators:
        raise Exception(f"无效的运算符: \"{''.join(invalid_operators)}\"")


# 现在更新 expr 的定义
expr <<= infixNotation(operand, 
    [
        (mul_div, 2, opAssoc.LEFT, parse_arith_op),
        (add_minus, 2, opAssoc.LEFT, parse_arith_op),
        (comparison_op, 2, opAssoc.LEFT, parse_comparison_op),
        (logical_and, 2, opAssoc.LEFT, parse_logical_expression),
        (logical_or, 2, opAssoc.LEFT, parse_logical_expression),
        (conditional_op, 3, opAssoc.RIGHT, parse_conditional_expression)
    ])

    
def check_parentheses_balance(expr):
    if expr.count('(') != expr.count(')'):
        raise ParseException(f"表达式括号未闭合")

# 定义整个表达式的解析规则
expr.setParseAction(parse_entire_expression) # check_parentheses_balance, 
# expr.setDebug()

def preprocess_unary_minus(factor_expression):
    """
    预处理表达式中的一元负号，将其转换为 (-1 * ...) 的形式。
    
    处理模式：
    - "A * -B" -> "A * (-1 * B)"
    - "A * -(B)" -> "A * (-1 * (B))"
    - "A / -B" -> "A / (-1 * B)"
    
    这样可以让解析器正确处理一元负号。
    """
    import re
    
    # 模式1: 处理 "* -(" 或 "/ -(" -> "* (-1 * (" 或 "/ (-1 * ("
    # 例如: "A * -(B + C)" -> "A * (-1 * (B + C))"
    factor_expression = re.sub(
        r'(\*\s*)-(\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    factor_expression = re.sub(
        r'(/\s*)-(\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    
    # 模式2: 处理 "* -函数名(" 或 "/ -函数名("
    # 例如: "A * -DELAY($close, 1)" -> "A * (-1 * DELAY($close, 1))"
    factor_expression = re.sub(
        r'(\*\s*)-(\s*[A-Za-z_][A-Za-z0-9_]*\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    factor_expression = re.sub(
        r'(/\s*)-(\s*[A-Za-z_][A-Za-z0-9_]*\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    
    # 模式3: 处理 "* -$变量" 或 "/ -$变量"
    # 例如: "A * -$close" -> "A * (-1 * $close)"
    factor_expression = re.sub(
        r'(\*\s*)-(\s*\$[A-Za-z_][A-Za-z0-9_]*)',
        r'\1(-1 * \2)',
        factor_expression
    )
    factor_expression = re.sub(
        r'(/\s*)-(\s*\$[A-Za-z_][A-Za-z0-9_]*)',
        r'\1(-1 * \2)',
        factor_expression
    )
    
    # 模式4: 处理 "+ -(" 或 "- -(" (加减法后的一元负号)
    factor_expression = re.sub(
        r'(\+\s*)-(\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    factor_expression = re.sub(
        r'(-\s*)-(\s*\()',
        r'\1(-1 * \2',
        factor_expression
    )
    
    # 确保括号平衡：为上面添加的 (-1 * 补充闭合括号
    # 统计添加的开括号数量
    # 这里采用简单方法：检查是否有未闭合的括号
    open_count = factor_expression.count('(')
    close_count = factor_expression.count(')')
    if open_count > close_count:
        factor_expression += ')' * (open_count - close_count)
    
    return factor_expression


def parse_expression(factor_expression):
    check_parentheses_balance(factor_expression)
    check_for_invalid_operators(factor_expression)
    
    # 预处理一元负号
    factor_expression = preprocess_unary_minus(factor_expression)
    
    print("factor_expression: ", factor_expression)
    
    parsed_data_function = expr.parseString(factor_expression)[0]
    return parsed_data_function



def parse_symbol(expr, columns):
    replace_map = {}
    replace_map.update({
        "TRUE": "True",
        "true": "True",
        "FALSE": "False",
        "false": "False",
        "NAN": "np.nan",
        "NaN": "np.nan",
        "nan": "np.nan",
        "NULL": "np.nan",
        "null": "np.nan"
    })
    for col in columns:
        replace_map.update({col: col.replace('$', '')})
        # replace_map.update({col.replace('$', '').upper(): col.replace('$', '')})

    for var, var_df in replace_map.items():
        expr = expr.replace(var, var_df)
    return expr

if __name__ == '__main__':
    parse_expression("RANK(DELTA($open, 1) - DELTA($open, 1)) / (1e-8 + 1)")