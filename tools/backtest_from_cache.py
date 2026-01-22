#!/usr/bin/env python3
"""
从缓存直接加载因子值进行回测

当 factor_expression 不规范时，可以直接使用缓存的 result.h5 文件。
这些文件包含已计算好的因子值。

用法:
    # 回测单个因子库中所有有缓存的因子
    python tools/backtest_from_cache.py --input all_factors_library.json --output results.json
    
    # 只检查缓存状态，不回测
    python tools/backtest_from_cache.py --input all_factors_library.json --check-only
    
    # 导出有缓存的因子到新的JSON（用于后续回测）
    python tools/backtest_from_cache.py --input all_factors_library.json --export-cached factors_with_cache.json
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import OrderedDict
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_factor_library(filepath: str) -> dict:
    """加载因子库"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def check_cache_status(data: dict) -> dict:
    """检查因子库中的缓存状态"""
    factors = data.get("factors", {})
    
    stats = {
        "total": len(factors),
        "has_cache_path": 0,
        "cache_exists": 0,
        "cache_missing": 0,
        "no_cache_info": 0,
        "factors_with_cache": [],
        "factors_without_cache": [],
    }
    
    for fid, factor in factors.items():
        cache = factor.get("cache_location")
        if not cache:
            stats["no_cache_info"] += 1
            stats["factors_without_cache"].append(fid)
            continue
        
        h5_path = cache.get("result_h5_path", "")
        if not h5_path:
            stats["no_cache_info"] += 1
            stats["factors_without_cache"].append(fid)
            continue
        
        stats["has_cache_path"] += 1
        
        if Path(h5_path).exists():
            stats["cache_exists"] += 1
            stats["factors_with_cache"].append({
                "factor_id": fid,
                "factor_name": factor.get("factor_name", ""),
                "h5_path": h5_path,
                "factor": factor,
            })
        else:
            stats["cache_missing"] += 1
            stats["factors_without_cache"].append(fid)
    
    return stats


def load_factor_from_cache(h5_path: str) -> pd.DataFrame:
    """从缓存加载因子值"""
    try:
        df = pd.read_hdf(h5_path, key='data')
        return df
    except Exception as e:
        print(f"  ⚠️ 加载失败 {h5_path}: {e}")
        return None


def export_factors_with_cache(data: dict, stats: dict, output_path: str):
    """导出有缓存的因子到新的JSON"""
    factors_with_cache = stats["factors_with_cache"]
    
    new_factors = OrderedDict()
    for item in factors_with_cache:
        fid = item["factor_id"]
        new_factors[fid] = item["factor"]
    
    output_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_factors": len(new_factors),
            "note": f"Factors with valid cache from {Path(output_path).stem}",
            "version": "1.0"
        },
        "factors": new_factors
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已导出 {len(new_factors)} 个有缓存的因子到: {output_path}")


def create_factor_value_index(stats: dict, output_path: str = None):
    """
    创建因子值索引，用于快速查找因子对应的缓存文件
    
    输出格式:
    {
        "factor_id": {
            "factor_name": "...",
            "h5_path": "...",
            "factor_dir": "..."
        }
    }
    """
    index = {}
    
    for item in stats["factors_with_cache"]:
        fid = item["factor_id"]
        factor = item["factor"]
        cache = factor.get("cache_location", {})
        
        index[fid] = {
            "factor_name": item["factor_name"],
            "h5_path": item["h5_path"],
            "factor_dir": cache.get("factor_dir", ""),
            "factor_workspace_path": cache.get("factor_workspace_path", ""),
        }
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        print(f"✅ 已创建因子缓存索引: {output_path}")
    
    return index


def main():
    parser = argparse.ArgumentParser(description='从缓存加载因子进行回测')
    parser.add_argument('--input', '-i', type=str, required=True, help='输入因子库JSON路径')
    parser.add_argument('--output', '-o', type=str, help='输出结果路径')
    parser.add_argument('--check-only', action='store_true', help='只检查缓存状态')
    parser.add_argument('--export-cached', type=str, help='导出有缓存的因子到新JSON')
    parser.add_argument('--create-index', type=str, help='创建因子缓存索引文件')
    
    args = parser.parse_args()
    
    print(f"📂 加载因子库: {args.input}")
    data = load_factor_library(args.input)
    
    print(f"\n🔍 检查缓存状态...")
    stats = check_cache_status(data)
    
    print(f"\n📊 缓存统计:")
    print(f"  总因子数: {stats['total']}")
    print(f"  有缓存路径: {stats['has_cache_path']}")
    print(f"  缓存文件存在: {stats['cache_exists']}")
    print(f"  缓存文件缺失: {stats['cache_missing']}")
    print(f"  无缓存信息: {stats['no_cache_info']}")
    
    if args.check_only:
        print("\n✅ 检查完成 (--check-only 模式)")
        return
    
    if args.export_cached:
        export_factors_with_cache(data, stats, args.export_cached)
    
    if args.create_index:
        create_factor_value_index(stats, args.create_index)
    
    if not args.export_cached and not args.create_index:
        print("\n提示: 使用以下选项进行进一步操作:")
        print("  --export-cached <path>  导出有缓存的因子")
        print("  --create-index <path>   创建因子缓存索引")


if __name__ == '__main__':
    main()

