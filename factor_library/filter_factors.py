#!/usr/bin/env python3
"""
因子筛选脚本
1. 筛选 RankIC 最大的 50 个因子
2. 从 high_quality 中随机筛选 50 个因子
3. 从 round_number = 1、2、3、4、5、8 中各随机筛选 30 个因子（不足则全放）
"""

import json
import random
from datetime import datetime
from pathlib import Path

# 设置随机种子以便复现
random.seed(42)

# 路径配置
INPUT_FILE = Path("/home/tjxy/quantagent/AlphaAgent/factor_library/all_factors_library_AA.json")
OUTPUT_DIR = Path("/home/tjxy/quantagent/AlphaAgent/factor_library")

def load_factors(filepath):
    """加载因子库"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_factors(factors_dict, metadata_note, output_path):
    """保存因子库"""
    output_data = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_factors": len(factors_dict),
            "version": "1.0",
            "note": metadata_note
        },
        "factors": factors_dict
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(factors_dict)} 个因子到 {output_path}")

def filter_top_rankic(factors, n=50):
    """筛选 RankIC 最大的 n 个因子"""
    # 提取所有有 RankIC 的因子
    factors_with_rankic = []
    for fid, factor in factors.items():
        if factor.get("backtest_metrics") and factor["backtest_metrics"].get("RankIC") is not None:
            factors_with_rankic.append((fid, factor, factor["backtest_metrics"]["RankIC"]))
    
    # 按 RankIC 降序排序
    factors_with_rankic.sort(key=lambda x: x[2], reverse=True)
    
    # 取前 n 个
    top_n = factors_with_rankic[:n]
    
    result = {fid: factor for fid, factor, _ in top_n}
    print(f"\n=== 筛选 RankIC 最大的 {n} 个因子 ===")
    print(f"总共有 {len(factors_with_rankic)} 个因子有 RankIC")
    print(f"筛选出 {len(result)} 个因子")
    if top_n:
        print(f"RankIC 范围: {top_n[-1][2]:.6f} ~ {top_n[0][2]:.6f}")
    
    return result

def filter_high_quality_random(factors, n=50):
    """从 high_quality 中随机筛选 n 个因子"""
    # 筛选出所有 high_quality 因子
    high_quality_factors = {fid: factor for fid, factor in factors.items() 
                           if factor.get("quality") == "high_quality"}
    
    print(f"\n=== 从 high_quality 中随机筛选 {n} 个因子 ===")
    print(f"总共有 {len(high_quality_factors)} 个 high_quality 因子")
    
    # 随机筛选
    if len(high_quality_factors) <= n:
        result = high_quality_factors
        print(f"high_quality 因子不足 {n} 个，全部放入")
    else:
        selected_ids = random.sample(list(high_quality_factors.keys()), n)
        result = {fid: high_quality_factors[fid] for fid in selected_ids}
    
    print(f"筛选出 {len(result)} 个因子")
    return result

def filter_by_round_random(factors, rounds=[1, 2, 3, 4, 5, 8], n_per_round=30):
    """从指定 round_number 中各随机筛选 n 个因子（不足则全放），返回每个轮次的结果字典"""
    print(f"\n=== 从 round_number = {rounds} 中各随机筛选 {n_per_round} 个因子 ===")
    
    # 按 round_number 分组
    round_groups = {r: {} for r in rounds}
    for fid, factor in factors.items():
        rn = factor.get("round_number")
        if rn in rounds:
            round_groups[rn][fid] = factor
    
    # 打印各 round 的因子数量
    for r in rounds:
        print(f"  Round {r}: {len(round_groups[r])} 个因子")
    
    # 从每个 round 随机筛选，分别存储
    results = {}
    total_count = 0
    for r in rounds:
        group = round_groups[r]
        if len(group) <= n_per_round:
            # 不足 n 个，全部放入
            selected = group
            print(f"  Round {r}: 不足 {n_per_round} 个，全部放入 ({len(group)} 个)")
        else:
            selected_ids = random.sample(list(group.keys()), n_per_round)
            selected = {fid: group[fid] for fid in selected_ids}
            print(f"  Round {r}: 随机筛选 {n_per_round} 个")
        results[r] = selected
        total_count += len(selected)
    
    print(f"总共筛选出 {total_count} 个因子")
    return results

def main():
    print("=" * 60)
    print("因子筛选脚本")
    print("=" * 60)
    
    # 加载因子库
    data = load_factors(INPUT_FILE)
    factors = data["factors"]
    print(f"加载因子库: {INPUT_FILE}")
    print(f"总因子数: {len(factors)}")
    
    # 1. 筛选 RankIC 最大的 50 个因子
    top_rankic = filter_top_rankic(factors, n=50)
    save_factors(
        top_rankic,
        "Top 50 factors by RankIC from all_factors_library_AA.json",
        OUTPUT_DIR / "top50_rankic.json"
    )
    
    # 2. 从 high_quality 中随机筛选 50 个因子
    high_quality_random = filter_high_quality_random(factors, n=50)
    save_factors(
        high_quality_random,
        "Random 50 high_quality factors from all_factors_library_AA.json",
        OUTPUT_DIR / "random50_high_quality.json"
    )
    
    # 3. 从 round_number = 1、2、3、4、5、8 中各随机筛选 30 个因子（每个轮次单独保存）
    rounds = [1, 2, 3, 4, 5, 8]
    round_results = filter_by_round_random(factors, rounds=rounds, n_per_round=30)
    
    round_files = []
    for r in rounds:
        output_path = OUTPUT_DIR / f"random30_round{r}.json"
        save_factors(
            round_results[r],
            f"Random 30 factors from round {r} (from all_factors_library_AA.json)",
            output_path
        )
        round_files.append(output_path)
    
    print("\n" + "=" * 60)
    print("所有筛选任务完成！")
    print("=" * 60)
    print(f"\n生成的文件:")
    print(f"  1. {OUTPUT_DIR /'top50_rankic.json'}")
    print(f"  2. {OUTPUT_DIR / 'random50_high_quality.json'}")
    for r, f in zip(rounds, round_files):
        print(f"  3-{r}. {f}")

if __name__ == "__main__":
    main()

