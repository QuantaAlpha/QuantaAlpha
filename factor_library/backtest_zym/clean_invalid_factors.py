#!/usr/bin/env python3
"""
清洗因子库中不合规的因子表达式

不合规的情况：
1. 包含注释符号 // 或 #
2. 包含分号 ; (多行赋值语句)
3. 使用未定义的函数如 IF(), DOWN_RETURN() 等
4. 包含未定义的变量如 RESI5, THRESHOLD 等
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime

# 已知的无效模式
INVALID_PATTERNS = [
    r'//',           # 注释
    r';',            # 分号（多行语句）
    r'\bIF\s*\(',    # IF 函数
    r'\bELSE\b',     # ELSE 关键字
    r'\bTHEN\b',     # THEN 关键字
    r'\bFOR\b',      # FOR 循环
    r'\bWHILE\b',    # WHILE 循环
    r'\b=\s*[^=]',   # 赋值语句 (但不是 ==)
    r'\bDOWN_RETURN\b',
    r'\bUP_RETURN\b',
    r'\bMARKET_STRESS_INDICATOR\b',
    r'\bTHRESHOLD\b',
    r'\bRESI\d+\b',  # RESI5, RESI10 等未定义变量
]

# 编译正则表达式
INVALID_REGEX = [re.compile(p, re.IGNORECASE) for p in INVALID_PATTERNS]


def is_valid_expression(expr: str) -> tuple[bool, list[str]]:
    """
    检查因子表达式是否合规
    返回: (是否合规, 发现的问题列表)
    """
    if not expr or not isinstance(expr, str):
        return False, ["表达式为空"]
    
    issues = []
    
    for i, regex in enumerate(INVALID_REGEX):
        if regex.search(expr):
            issues.append(f"匹配到无效模式: {INVALID_PATTERNS[i]}")
    
    return len(issues) == 0, issues


def clean_factors(input_path: str, output_path: str = None, verbose: bool = False):
    """
    清洗因子库，移除不合规的因子
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return
    
    # 加载因子库
    print(f"📂 加载因子库: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    factors = data.get("factors", {})
    print(f"   总因子数: {len(factors)}")
    
    # 统计
    valid_factors = {}
    invalid_factors = {}
    issue_summary = {}
    
    for fid, factor in factors.items():
        expr = factor.get("factor_expression", "")
        is_valid, issues = is_valid_expression(expr)
        
        if is_valid:
            valid_factors[fid] = factor
        else:
            invalid_factors[fid] = {
                "factor": factor,
                "issues": issues
            }
            for issue in issues:
                issue_summary[issue] = issue_summary.get(issue, 0) + 1
    
    print(f"\n📊 清洗结果:")
    print(f"   ✅ 合规因子: {len(valid_factors)}")
    print(f"   ❌ 不合规因子: {len(invalid_factors)}")
    
    if issue_summary:
        print(f"\n📋 问题汇总:")
        for issue, count in sorted(issue_summary.items(), key=lambda x: -x[1]):
            print(f"   - {issue}: {count} 个")
    
    if verbose and invalid_factors:
        print(f"\n🔍 不合规因子详情:")
        for fid, info in list(invalid_factors.items())[:10]:
            factor = info["factor"]
            print(f"\n   [{fid}] {factor.get('factor_name', 'unknown')}")
            print(f"   问题: {', '.join(info['issues'])}")
            expr = factor.get('factor_expression', '')[:200]
            print(f"   表达式: {expr}...")
        
        if len(invalid_factors) > 10:
            print(f"\n   ... 还有 {len(invalid_factors) - 10} 个不合规因子")
    
    # 保存清洗后的因子库
    if output_path:
        output_path = Path(output_path)
    else:
        # 默认在原文件名后加 _clean
        output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
    
    output_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_factors": len(valid_factors),
            "version": "1.0",
            "note": f"Cleaned from {input_path.name}, removed {len(invalid_factors)} invalid factors"
        },
        "factors": valid_factors
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 已保存清洗后的因子库: {output_path}")
    print(f"   保留因子数: {len(valid_factors)}")
    
    return valid_factors, invalid_factors


def main():
    parser = argparse.ArgumentParser(description="清洗因子库中不合规的因子表达式")
    parser.add_argument("input", type=str, help="输入因子库 JSON 文件路径")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认: 原文件名_clean.json)")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    
    args = parser.parse_args()
    
    clean_factors(args.input, args.output, args.verbose)


if __name__ == "__main__":
    main()

