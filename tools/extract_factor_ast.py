#!/usr/bin/env python3
"""
因子AST提取工具

该工具用于将因子库中的因子表达式解析为AST结构并保存。
可以用于：
1. 分析因子的结构复杂度
2. 计算因子之间的冗余度
3. 因子表达式的相似度比较

使用方式：
    python tools/extract_factor_ast.py all_factors_library_QA_round41_best_deepseek_aliyun_all_csi300.json --ast-only factor_ast_data.json
    python extract_factor_ast.py input.json output.json
    python extract_factor_ast.py input.json  # 原地更新（添加AST字段）
"""

import json
import sys
import os
from pathlib import Path
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict

# 添加项目路径以导入 factor_ast 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from alphaagent.components.coder.factor_coder.factor_ast import (
    parse_expression,
    Node, VarNode, NumberNode, FunctionNode, BinaryOpNode, 
    ConditionalNode, UnaryOpNode,
    count_all_nodes, count_free_args, count_unique_vars,
    calculate_symbol_length, count_base_features
)


@dataclass
class ASTNodeSerialized:
    """序列化的AST节点结构"""
    type: str  # VAR, NUM, FUNC, BINOP, UNARY, COND
    value: Optional[Any] = None  # 节点的值（变量名、数字、运算符等）
    children: List['ASTNodeSerialized'] = field(default_factory=list)


def serialize_ast(node: Node) -> Dict[str, Any]:
    """
    将AST节点序列化为可JSON化的字典
    
    Args:
        node: AST节点
        
    Returns:
        可序列化的字典
    """
    if isinstance(node, VarNode):
        return {
            "type": "VAR",
            "name": node.name
        }
    elif isinstance(node, NumberNode):
        return {
            "type": "NUM",
            "value": node.value
        }
    elif isinstance(node, FunctionNode):
        # 注意：node.name 可能是 VarNode 对象，需要提取其字符串名称
        func_name = get_node_name(node.name)
        return {
            "type": "FUNC",
            "name": func_name,
            "args": [serialize_ast(arg) for arg in node.args]
        }
    elif isinstance(node, BinaryOpNode):
        return {
            "type": "BINOP",
            "op": node.op,
            "left": serialize_ast(node.left),
            "right": serialize_ast(node.right)
        }
    elif isinstance(node, UnaryOpNode):
        return {
            "type": "UNARY",
            "op": node.op,
            "operand": serialize_ast(node.operand)
        }
    elif isinstance(node, ConditionalNode):
        return {
            "type": "COND",
            "condition": serialize_ast(node.condition),
            "true_expr": serialize_ast(node.true_expr),
            "false_expr": serialize_ast(node.false_expr)
        }
    else:
        return {"type": "UNKNOWN", "repr": str(node)}


def deserialize_ast(data: Dict[str, Any]) -> Node:
    """
    从序列化的字典还原AST节点
    
    Args:
        data: 序列化的字典
        
    Returns:
        AST节点
    """
    node_type = data.get("type")
    
    if node_type == "VAR":
        return VarNode(name=data["name"])
    elif node_type == "NUM":
        return NumberNode(value=data["value"])
    elif node_type == "FUNC":
        args = [deserialize_ast(arg) for arg in data.get("args", [])]
        return FunctionNode(name=data["name"], args=args)
    elif node_type == "BINOP":
        return BinaryOpNode(
            op=data["op"],
            left=deserialize_ast(data["left"]),
            right=deserialize_ast(data["right"])
        )
    elif node_type == "UNARY":
        return UnaryOpNode(
            op=data["op"],
            operand=deserialize_ast(data["operand"])
        )
    elif node_type == "COND":
        return ConditionalNode(
            condition=deserialize_ast(data["condition"]),
            true_expr=deserialize_ast(data["true_expr"]),
            false_expr=deserialize_ast(data["false_expr"])
        )
    else:
        raise ValueError(f"Unknown node type: {node_type}")


def get_node_name(node) -> str:
    """
    获取节点的名称字符串
    
    Args:
        node: AST节点或字符串
        
    Returns:
        名称字符串
    """
    if isinstance(node, str):
        return node
    elif isinstance(node, VarNode):
        return node.name
    elif hasattr(node, 'name'):
        # 递归处理可能嵌套的VarNode
        return get_node_name(node.name)
    else:
        return str(node)


def collect_functions(node: Node) -> List[str]:
    """
    收集表达式中使用的所有函数名
    
    Args:
        node: AST节点
        
    Returns:
        函数名列表
    """
    functions = []
    
    if isinstance(node, FunctionNode):
        # 注意：node.name 可能是 VarNode 对象，需要提取其字符串名称
        func_name = get_node_name(node.name)
        functions.append(func_name)
        for arg in node.args:
            functions.extend(collect_functions(arg))
    elif isinstance(node, BinaryOpNode):
        functions.extend(collect_functions(node.left))
        functions.extend(collect_functions(node.right))
    elif isinstance(node, UnaryOpNode):
        functions.extend(collect_functions(node.operand))
    elif isinstance(node, ConditionalNode):
        functions.extend(collect_functions(node.condition))
        functions.extend(collect_functions(node.true_expr))
        functions.extend(collect_functions(node.false_expr))
    
    return functions


def collect_variables(node: Node) -> List[str]:
    """
    收集表达式中使用的所有变量名
    
    Args:
        node: AST节点
        
    Returns:
        变量名列表
    """
    variables = []
    
    if isinstance(node, VarNode):
        variables.append(node.name)
    elif isinstance(node, FunctionNode):
        for arg in node.args:
            variables.extend(collect_variables(arg))
    elif isinstance(node, BinaryOpNode):
        variables.extend(collect_variables(node.left))
        variables.extend(collect_variables(node.right))
    elif isinstance(node, UnaryOpNode):
        variables.extend(collect_variables(node.operand))
    elif isinstance(node, ConditionalNode):
        variables.extend(collect_variables(node.condition))
        variables.extend(collect_variables(node.true_expr))
        variables.extend(collect_variables(node.false_expr))
    
    return variables


def compute_tree_depth(node: Node) -> int:
    """
    计算AST树的深度
    
    Args:
        node: AST节点
        
    Returns:
        树的深度
    """
    if isinstance(node, (VarNode, NumberNode)):
        return 1
    elif isinstance(node, FunctionNode):
        if not node.args:
            return 1
        return 1 + max(compute_tree_depth(arg) for arg in node.args)
    elif isinstance(node, BinaryOpNode):
        return 1 + max(compute_tree_depth(node.left), compute_tree_depth(node.right))
    elif isinstance(node, UnaryOpNode):
        return 1 + compute_tree_depth(node.operand)
    elif isinstance(node, ConditionalNode):
        return 1 + max(
            compute_tree_depth(node.condition),
            compute_tree_depth(node.true_expr),
            compute_tree_depth(node.false_expr)
        )
    return 1


def extract_ast_for_factor(factor_expression: str) -> Dict[str, Any]:
    """
    为单个因子表达式提取AST及相关统计信息
    
    Args:
        factor_expression: 因子表达式字符串
        
    Returns:
        包含AST结构和统计信息的字典
    """
    try:
        # 解析表达式
        ast_root = parse_expression(factor_expression)
        
        # 序列化AST
        ast_serialized = serialize_ast(ast_root)
        
        # 收集函数和变量
        functions = collect_functions(ast_root)
        variables = collect_variables(ast_root)
        
        # 计算统计信息
        result = {
            "ast_tree": ast_serialized,
            "ast_tree_string": ast_root.tree_str(),  # 可读的树形字符串
            "statistics": {
                "total_nodes": count_all_nodes(factor_expression),
                "tree_depth": compute_tree_depth(ast_root),
                "num_free_args": count_free_args(factor_expression),
                "num_unique_vars": count_unique_vars(factor_expression),
                "symbol_length": calculate_symbol_length(factor_expression),
                "num_base_features": count_base_features(factor_expression),
                "functions_used": list(set(functions)),
                "variables_used": list(set(variables)),
                "function_count": len(functions),
                "variable_count": len(variables),
            },
            "parse_success": True,
            "parse_error": None
        }
        
        return result
        
    except Exception as e:
        return {
            "ast_tree": None,
            "ast_tree_string": None,
            "statistics": None,
            "parse_success": False,
            "parse_error": str(e)
        }


def process_factor_library(input_path: str, output_path: Optional[str] = None, 
                           add_to_existing: bool = True) -> Dict[str, Any]:
    """
    处理整个因子库，为所有因子提取AST
    
    Args:
        input_path: 输入因子库JSON路径
        output_path: 输出路径，如果为None则原地更新
        add_to_existing: 是否添加到现有因子记录中
        
    Returns:
        处理统计信息
    """
    print(f"📖 加载因子库: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    factors = data.get('factors', {})
    total = len(factors)
    success_count = 0
    error_count = 0
    errors = []
    
    print(f"📊 开始处理 {total} 个因子...")
    
    for idx, (factor_id, factor_data) in enumerate(factors.items()):
        factor_expression = factor_data.get('factor_expression', '')
        factor_name = factor_data.get('factor_name', factor_id)
        
        if not factor_expression:
            print(f"  ⚠️ [{idx+1}/{total}] {factor_name}: 表达式为空，跳过")
            continue
        
        # 提取AST
        ast_result = extract_ast_for_factor(factor_expression)
        
        if ast_result['parse_success']:
            success_count += 1
            status = "✅"
        else:
            error_count += 1
            errors.append({
                "factor_id": factor_id,
                "factor_name": factor_name,
                "expression": factor_expression,
                "error": ast_result['parse_error']
            })
            status = "❌"
        
        # 添加AST信息到因子记录
        if add_to_existing:
            factor_data['factor_ast'] = ast_result
        
        # 打印进度
        if (idx + 1) % 50 == 0 or idx == total - 1:
            print(f"  {status} [{idx+1}/{total}] 处理中... (成功: {success_count}, 失败: {error_count})")
    
    # 更新元数据
    data['metadata']['ast_extraction_time'] = datetime.now().isoformat()
    data['metadata']['ast_extraction_stats'] = {
        "total_processed": total,
        "success": success_count,
        "failed": error_count
    }
    
    # 保存结果
    save_path = output_path or input_path
    print(f"\n💾 保存结果到: {save_path}")
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 打印统计信息
    print(f"\n{'='*50}")
    print(f"📈 处理完成!")
    print(f"   总因子数: {total}")
    print(f"   成功解析: {success_count}")
    print(f"   解析失败: {error_count}")
    
    if errors:
        print(f"\n❌ 解析失败的因子:")
        for err in errors[:10]:  # 只显示前10个
            print(f"   - {err['factor_name']}: {err['error'][:100]}...")
        if len(errors) > 10:
            print(f"   ... 还有 {len(errors)-10} 个失败")
    
    return {
        "total": total,
        "success": success_count,
        "failed": error_count,
        "errors": errors,
        "output_path": save_path
    }


def extract_ast_only(input_path: str, output_path: str) -> Dict[str, Any]:
    """
    仅提取AST信息，保存为独立的JSON文件（不修改原因子库）
    
    Args:
        input_path: 输入因子库JSON路径
        output_path: AST输出路径
        
    Returns:
        处理统计信息
    """
    print(f"📖 加载因子库: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    factors = data.get('factors', {})
    total = len(factors)
    
    ast_data = OrderedDict()
    ast_data['metadata'] = {
        "source_file": str(input_path),
        "extraction_time": datetime.now().isoformat(),
        "total_factors": total
    }
    ast_data['factor_asts'] = OrderedDict()
    
    success_count = 0
    error_count = 0
    
    print(f"📊 开始提取 {total} 个因子的AST...")
    
    for idx, (factor_id, factor_data) in enumerate(factors.items()):
        factor_expression = factor_data.get('factor_expression', '')
        factor_name = factor_data.get('factor_name', factor_id)
        
        if not factor_expression:
            continue
        
        ast_result = extract_ast_for_factor(factor_expression)
        
        ast_data['factor_asts'][factor_id] = {
            "factor_name": factor_name,
            "factor_expression": factor_expression,
            **ast_result
        }
        
        if ast_result['parse_success']:
            success_count += 1
        else:
            error_count += 1
        
        if (idx + 1) % 50 == 0 or idx == total - 1:
            print(f"  [{idx+1}/{total}] 处理中... (成功: {success_count}, 失败: {error_count})")
    
    ast_data['metadata']['success_count'] = success_count
    ast_data['metadata']['error_count'] = error_count
    
    print(f"\n💾 保存AST数据到: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ast_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 完成! 成功: {success_count}, 失败: {error_count}")
    
    return {
        "total": total,
        "success": success_count,
        "failed": error_count,
        "output_path": output_path
    }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法:")
        print("  python extract_factor_ast.py <input.json> [output.json]")
        print("")
        print("参数:")
        print("  input.json   - 因子库JSON文件路径")
        print("  output.json  - (可选) 输出文件路径，不指定则原地更新")
        print("")
        print("示例:")
        print("  # 原地更新，添加AST字段到每个因子")
        print("  python extract_factor_ast.py all_factors_library.json")
        print("")
        print("  # 输出到新文件")
        print("  python extract_factor_ast.py all_factors_library.json factors_with_ast.json")
        print("")
        print("  # 仅提取AST，不修改原文件")
        print("  python extract_factor_ast.py all_factors_library.json --ast-only ast_output.json")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if not os.path.exists(input_path):
        print(f"❌ 错误: 文件不存在 {input_path}")
        sys.exit(1)
    
    # 检查是否是 --ast-only 模式
    if len(sys.argv) >= 4 and sys.argv[2] == '--ast-only':
        output_path = sys.argv[3]
        extract_ast_only(input_path, output_path)
    else:
        output_path = sys.argv[2] if len(sys.argv) >= 3 else None
        process_factor_library(input_path, output_path)


if __name__ == '__main__':
    main()

