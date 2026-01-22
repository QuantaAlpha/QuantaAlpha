#!/usr/bin/env python3
"""
过滤可回测的因子

从因子库中筛选出可以进行回测的因子：
1. 有缓存文件 (result.h5) 的因子 - 直接加载计算好的值
2. 有规范 factor_expression 的因子 - 可以重新计算

用法:
    # 导出可回测的因子
    python tools/filter_backtestable_factors.py \
        --input all_factors_library.json \
        --output filtered_factors.json
    
    # 只显示统计信息
    python tools/filter_backtestable_factors.py \
        --input all_factors_library.json \
        --stats-only
"""

import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from collections import OrderedDict


# 不规范表达式的模式
INVALID_PATTERNS = [
    r'LET\s*\(',          # LET(...) 变量定义
    r'\bIF\s*\(',         # IF(...) 条件
    r'//',                # // 注释
    r';\s*\n',            # 分号换行（多语句）
    r'\b[a-z_]+\s*=\s*[^=]',  # 变量赋值 (如 roc60 = ...)
    r'#\s+[A-Za-z]',      # # 注释
    r'\bAND\b',           # AND 关键字
    r'\bOR\b',            # OR 关键字
    r'\bNULL\b',          # NULL 关键字
]


def is_valid_expression(expr: str) -> tuple:
    """
    检查因子表达式是否规范
    
    Returns:
        (is_valid, issues_list)
    """
    if not expr or not isinstance(expr, str):
        return False, ["表达式为空"]
    
    issues = []
    for pattern in INVALID_PATTERNS:
        if re.search(pattern, expr, re.MULTILINE | re.IGNORECASE):
            issues.append(f"匹配到不规范模式: {pattern}")
    
    return len(issues) == 0, issues


def check_cache_exists(cache_location: dict) -> bool:
    """检查缓存文件是否存在"""
    if not cache_location:
        return False
    
    h5_path = cache_location.get("result_h5_path", "")
    if not h5_path:
        return False
    
    return Path(h5_path).exists()


def analyze_factors(data: dict) -> dict:
    """分析因子库"""
    factors = data.get("factors", {})
    
    stats = {
        "total": len(factors),
        "has_cache": 0,
        "valid_expr_only": 0,
        "both": 0,  # 有缓存且表达式有效
        "backtestable": 0,  # 可回测 = has_cache OR valid_expr
        "not_backtestable": 0,
        "invalid_expr_with_cache": 0,  # 表达式无效但有缓存
        "invalid_expr_no_cache": 0,  # 表达式无效且无缓存
        "factors": {
            "backtestable": [],
            "not_backtestable": [],
        }
    }
    
    for fid, factor in factors.items():
        expr = factor.get("factor_expression", "")
        cache = factor.get("cache_location")
        
        has_cache = check_cache_exists(cache)
        is_valid, issues = is_valid_expression(expr)
        
        if has_cache:
            stats["has_cache"] += 1
        if is_valid:
            stats["valid_expr_only"] += 1
        if has_cache and is_valid:
            stats["both"] += 1
        
        # 可回测条件：有缓存 OR 表达式有效
        if has_cache or is_valid:
            stats["backtestable"] += 1
            stats["factors"]["backtestable"].append({
                "factor_id": fid,
                "factor_name": factor.get("factor_name", ""),
                "has_cache": has_cache,
                "valid_expr": is_valid,
                "source": "cache" if has_cache else "expr",
                "factor": factor,
            })
        else:
            stats["not_backtestable"] += 1
            stats["factors"]["not_backtestable"].append({
                "factor_id": fid,
                "factor_name": factor.get("factor_name", ""),
                "issues": issues,
                "factor": factor,
            })
        
        if not is_valid:
            if has_cache:
                stats["invalid_expr_with_cache"] += 1
            else:
                stats["invalid_expr_no_cache"] += 1
    
    return stats


def export_backtestable_factors(stats: dict, output_path: str, input_path: str):
    """导出可回测的因子"""
    backtestable = stats["factors"]["backtestable"]
    
    new_factors = OrderedDict()
    for item in backtestable:
        fid = item["factor_id"]
        new_factors[fid] = item["factor"]
    
    output_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_factors": len(new_factors),
            "source": str(input_path),
            "note": f"Filtered backtestable factors: {stats['has_cache']} from cache, {stats['valid_expr_only']} from valid expression",
            "version": "1.0"
        },
        "factors": new_factors
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 已导出 {len(new_factors)} 个可回测因子到: {output_path}")


def print_stats(stats: dict):
    """打印统计信息"""
    print(f"\n{'='*60}")
    print("因子库分析报告")
    print('='*60)
    
    print(f"\n📊 总体统计:")
    print(f"  总因子数: {stats['total']}")
    print(f"  ✅ 可回测: {stats['backtestable']} ({stats['backtestable']/stats['total']*100:.1f}%)")
    print(f"  ❌ 不可回测: {stats['not_backtestable']} ({stats['not_backtestable']/stats['total']*100:.1f}%)")
    
    print(f"\n📁 缓存状态:")
    print(f"  有缓存文件: {stats['has_cache']}")
    print(f"  表达式有效: {stats['valid_expr_only']}")
    print(f"  两者都有: {stats['both']}")
    
    print(f"\n⚠️ 问题因子:")
    print(f"  表达式无效但有缓存(可回测): {stats['invalid_expr_with_cache']}")
    print(f"  表达式无效且无缓存(不可回测): {stats['invalid_expr_no_cache']}")
    
    # 显示不可回测因子
    not_backtestable = stats["factors"]["not_backtestable"]
    if not_backtestable:
        print(f"\n❌ 不可回测的因子 ({len(not_backtestable)} 个):")
        for item in not_backtestable[:10]:
            print(f"  - {item['factor_name']}: {', '.join(item['issues'][:2])}")
        if len(not_backtestable) > 10:
            print(f"  ... 还有 {len(not_backtestable) - 10} 个")
    
    print('='*60)


def main():
    parser = argparse.ArgumentParser(description='过滤可回测的因子')
    parser.add_argument('--input', '-i', type=str, required=True, help='输入因子库JSON路径')
    parser.add_argument('--output', '-o', type=str, help='输出文件路径')
    parser.add_argument('--stats-only', action='store_true', help='只显示统计信息')
    
    args = parser.parse_args()
    
    print(f"📂 加载因子库: {args.input}")
    
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f, object_pairs_hook=OrderedDict)
    
    stats = analyze_factors(data)
    print_stats(stats)
    
    if not args.stats_only and args.output:
        export_backtestable_factors(stats, args.output, args.input)
    elif not args.stats_only:
        # 自动生成输出文件名
        input_path = Path(args.input)
        output_path = input_path.parent / f"{input_path.stem}_backtestable{input_path.suffix}"
        export_backtestable_factors(stats, str(output_path), args.input)


if __name__ == '__main__':
    main()

