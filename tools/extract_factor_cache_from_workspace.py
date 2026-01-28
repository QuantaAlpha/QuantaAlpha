#!/usr/bin/env python3
"""
从 QuantaAlpha 工作空间提取因子计算缓存到 backtest_v2 格式

使用方法:
    # 提取指定工作空间的所有因子
    python extract_factor_cache_from_workspace.py --workspace /path/to/RD-Agent_workspace_xxx
    
    # 只提取指定因子库 JSON 中的因子
    python extract_factor_cache_from_workspace.py \
        --workspace /path/to/RD-Agent_workspace_xxx \
        --factor-json /path/to/factor_library.json
    
    # 指定输出缓存目录
    python extract_factor_cache_from_workspace.py \
        --workspace /path/to/RD-Agent_workspace_xxx \
        --cache-dir /path/to/factor_cache
"""

import os
import re
import json
import hashlib
import pickle
import argparse
import pandas as pd
from pathlib import Path
from typing import Optional, Set


def get_cache_key(expression: str) -> str:
    """计算 backtest_v2 使用的缓存 key"""
    return hashlib.md5(expression.encode()).hexdigest()


def extract_expression_from_factor_py(factor_py_path: str) -> Optional[str]:
    """从 factor.py 文件中提取因子表达式"""
    try:
        with open(factor_py_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 匹配 expr = "..." 或 expr = '...'
        match = re.search(r'expr\s*=\s*["\'](.+?)["\']', code, re.DOTALL)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def load_factor_expressions_from_json(json_path: str) -> Set[str]:
    """从因子库 JSON 中加载所有因子表达式"""
    expressions = set()
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for factor in data.get('factors', {}).values():
            expr = factor.get('factor_expression', '')
            if expr:
                expressions.add(expr)
    except Exception as e:
        print(f"警告: 无法加载 JSON 文件: {e}")
    
    return expressions


def extract_cache(
    workspace_path: str,
    cache_dir: str,
    factor_json: Optional[str] = None,
    overwrite: bool = False
) -> dict:
    """
    从工作空间提取因子缓存
    
    Args:
        workspace_path: QuantaAlpha 工作空间路径
        cache_dir: 目标缓存目录
        factor_json: 可选，只提取该 JSON 中存在的因子
        overwrite: 是否覆盖已有缓存
    
    Returns:
        统计信息字典
    """
    # 确保缓存目录存在
    os.makedirs(cache_dir, exist_ok=True)
    
    # 获取已有缓存
    existing_cache = set()
    if not overwrite:
        for f in os.listdir(cache_dir):
            if f.endswith('.pkl'):
                existing_cache.add(f.replace('.pkl', ''))
    
    # 加载目标因子表达式（如果指定了 JSON）
    target_expressions = None
    if factor_json:
        target_expressions = load_factor_expressions_from_json(factor_json)
        print(f"从 JSON 加载 {len(target_expressions)} 个目标因子表达式")
    
    # 统计
    stats = {
        'found': 0,
        'extracted': 0,
        'skipped_exists': 0,
        'skipped_no_match': 0,
        'errors': 0
    }
    
    # 遍历工作空间
    workspace = Path(workspace_path)
    print(f"扫描工作空间: {workspace}")
    
    for subdir in workspace.iterdir():
        if not subdir.is_dir():
            continue
        
        result_h5 = subdir / 'result.h5'
        factor_py = subdir / 'factor.py'
        
        if not result_h5.exists() or not factor_py.exists():
            continue
        
        stats['found'] += 1
        
        # 提取表达式
        expr = extract_expression_from_factor_py(str(factor_py))
        if not expr:
            stats['errors'] += 1
            continue
        
        # 检查是否在目标列表中
        if target_expressions is not None and expr not in target_expressions:
            stats['skipped_no_match'] += 1
            continue
        
        # 计算缓存 key
        cache_key = get_cache_key(expr)
        
        # 检查是否已存在
        if cache_key in existing_cache:
            stats['skipped_exists'] += 1
            continue
        
        # 读取因子数据
        try:
            factor_data = pd.read_hdf(str(result_h5))
            
            # 保存为 backtest_v2 格式
            cache_path = os.path.join(cache_dir, f"{cache_key}.pkl")
            with open(cache_path, 'wb') as f:
                pickle.dump(factor_data, f)
            
            stats['extracted'] += 1
            existing_cache.add(cache_key)
            
        except Exception as e:
            stats['errors'] += 1
            print(f"警告: 读取 {result_h5} 失败: {e}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='从 QuantaAlpha 工作空间提取因子缓存')
    parser.add_argument('--workspace', '-w', required=True, help='工作空间路径')
    parser.add_argument('--cache-dir', '-c', 
                       default='/mnt/DATA/quantagent/QuantaAlpha/factor_cache',
                       help='目标缓存目录')
    parser.add_argument('--factor-json', '-j', help='只提取该 JSON 中的因子')
    parser.add_argument('--overwrite', action='store_true', help='覆盖已有缓存')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("因子缓存提取工具")
    print("=" * 60)
    print(f"工作空间: {args.workspace}")
    print(f"缓存目录: {args.cache_dir}")
    if args.factor_json:
        print(f"因子 JSON: {args.factor_json}")
    print()
    
    stats = extract_cache(
        workspace_path=args.workspace,
        cache_dir=args.cache_dir,
        factor_json=args.factor_json,
        overwrite=args.overwrite
    )
    
    print()
    print("=" * 60)
    print("提取结果")
    print("=" * 60)
    print(f"扫描到的因子目录: {stats['found']}")
    print(f"成功提取: {stats['extracted']}")
    print(f"跳过(已有缓存): {stats['skipped_exists']}")
    if args.factor_json:
        print(f"跳过(不在 JSON 中): {stats['skipped_no_match']}")
    print(f"错误: {stats['errors']}")


if __name__ == '__main__':
    main()

