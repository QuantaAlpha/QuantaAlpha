import argparse
import json
import random
import os
from pathlib import Path
from datetime import datetime

def load_factors(filepath):
    """加载因子库"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def save_factors(factors_dict, metadata_note, output_path, original_metadata=None):
    """保存因子库"""
    metadata = {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "total_factors": len(factors_dict),
        "version": "1.0",
        "note": metadata_note
    }
    
    # 保留原始 metadata 中的部分信息（如果需要）
    if original_metadata:
        metadata["source_version"] = original_metadata.get("version")
    
    output_data = {
        "metadata": metadata,
        "factors": factors_dict
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(factors_dict)} 个因子到 {output_path}")

def get_metric_value(factor, metric_name):
    """获取因子的指标值"""
    # 尝试多种可能的 metrics 键名
    metrics = factor.get("backtest_metrics") or factor.get("backtest_results")
    if not metrics:
        return None
    
    # 统一指标名称映射 (Key 是用户输入的 method，Value 是可能的 JSON 键列表)
    mapping = {
        "IC": ["IC", "ic"],
        "ICIR": ["ICIR", "icir"],
        "RANKIC": ["RankIC", "Rank IC", "rank_ic", "rankic"],
        "RANKICIR": ["RankICIR", "Rank ICIR", "rank_icir", "rankicir"],
        "ARR": ["annualized_return", "1day.excess_return_without_cost.annualized_return", "Annualized Return"],
        "IR": ["information_ratio", "1day.excess_return_without_cost.information_ratio", "Information Ratio"],
        "MDD": ["max_drawdown", "1day.excess_return_without_cost.max_drawdown", "Max Drawdown"],
    }
    
    # 获取实际值的辅助函数
    def get_val(keys):
        for k in keys:
            if k in metrics:
                return metrics[k]
        return None

    metric_upper = metric_name.upper()

    if metric_upper == "CR":
        # Calmar Ratio = Annualized Return / abs(Max Drawdown)
        arr = get_val(mapping["ARR"])
        mdd = get_val(mapping["MDD"])
        if arr is not None and mdd is not None:
            if mdd == 0:
                return float('inf') if arr >= 0 else -float('inf')
            return arr / abs(mdd)
        return None
    
    if metric_upper == "FITNESS":
        # 自定义 Fitness: RankIC * sqrt(RankICIR)
        rankic = get_val(mapping["RANKIC"])
        rankicir = get_val(mapping["RANKICIR"])
        if rankic is not None and rankicir is not None and rankicir > 0:
            return rankic * (rankicir ** 0.5)
        return None

    target_keys = mapping.get(metric_upper)
    if target_keys:
        return get_val(target_keys)
    
    # 如果没在映射中，直接尝试
    return metrics.get(metric_name)

def generate_output_filename(source_path, method, n, suffix_identifier="all_factors_library", rounds=None, phases=None):
    """生成输出文件名"""
    source_name = Path(source_path).stem
    
    # 提取后缀
    if suffix_identifier in source_name:
        parts = source_name.split(suffix_identifier)
        if len(parts) > 1:
            suffix = parts[1]
            # 如果后缀以 _ 开头，保留它；否则可能需要处理
            if suffix.startswith('_'):
                suffix = suffix[1:]
        else:
            suffix = source_name
    else:
        suffix = source_name
        
    # 构建新文件名
    # 格式: method_n_suffix.json
    method_str = method.replace(" ", "_")
    
    # 如果指定了 rounds，将其加入文件名
    # 格式示例: round_number_rounds_8_9_10_150_suffix.json
    rounds_str = ""
    if rounds:
        # 将列表转换为字符串，例如 [8, 9, 10] -> "8_9_10"
        r_str = "_".join(map(str, sorted(rounds)))
        rounds_str = f"_rounds_{r_str}"
    
    # 如果指定了 phases，将其加入文件名
    phases_str = ""
    if phases:
        # 将列表转换为字符串，例如 ["mutation", "crossover"] -> "mutation_crossover"
        p_str = "_".join(sorted(phases))
        phases_str = f"_phase_{p_str}"
    
    return f"{method_str}{rounds_str}{phases_str}_{n}_{suffix}.json"

def main():
    parser = argparse.ArgumentParser(description="从因子库中抽取因子生成新文件")
    parser.add_argument("--source", "-s", type=str, required=True, help="源因子库JSON文件路径")
    parser.add_argument("--number", "-n", type=int, required=False, default=None, help="抽取数量 (可选，如果不填且方法为round_number，则返回所有匹配的因子)")
    parser.add_argument("--method", "-m", type=str, default="random", 
                        choices=["random", "IC", "ICIR", "RANKIC", "RANKICIR", "ARR", "IR", "CR", "MDD", "FITNESS", "round_number"],
                        help="抽取方法：random, round_number 或 指定指标名称")
    parser.add_argument("--order", "-o", type=str, default="desc", choices=["asc", "desc"],
                        help="排序顺序：asc(从低到高), desc(从高到低)。仅对指标抽取有效。")
    parser.add_argument("--output_dir", "-d", type=str, default=os.path.dirname(os.path.abspath(__file__)),
                        help="输出目录")
    parser.add_argument("--target_rounds", "-r", type=int, nargs='+', help="筛选的 round_number 列表，例如 8 9 10")
    parser.add_argument("--evolution_phase", "-e", type=str, nargs='+', 
                        help="筛选的 evolution_phase 列表，例如 mutation crossover original")
    
    args = parser.parse_args()
    
    source_path = args.source
    n = args.number
    method = args.method
    order = args.order
    output_dir = args.output_dir
    target_rounds = args.target_rounds
    evolution_phase = args.evolution_phase
    
    print(f"正在读取因子库: {source_path}")
    try:
        data = load_factors(source_path)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return

    factors = data.get("factors", {})
    print(f"总因子数量: {len(factors)}")
    
    if len(factors) == 0:
        print("因子库为空，退出。")
        return

    # 1. 如果指定了 target_rounds，先进行筛选
    if target_rounds:
        print(f"正在筛选 round_number 在 {target_rounds} 中的因子...")
        filtered_factors = {}
        for fid, factor in factors.items():
            # round_number 可能在顶层或 metadata 中
            rn = factor.get("round_number")
            if rn is None:
                metadata = factor.get("metadata", {})
                rn = metadata.get("round_number")
            if rn in target_rounds:
                filtered_factors[fid] = factor
        
        print(f"符合 round_number 条件的因子数量: {len(filtered_factors)}")
        factors = filtered_factors
        
        if len(factors) == 0:
            print("没有符合 round_number 条件的因子，退出。")
            return
    
    # 1.5 如果指定了 evolution_phase，进行筛选
    if evolution_phase:
        print(f"正在筛选 evolution_phase 在 {evolution_phase} 中的因子...")
        filtered_factors = {}
        for fid, factor in factors.items():
            # evolution_phase 在 metadata 中
            metadata = factor.get("metadata", {})
            ep = metadata.get("evolution_phase", "")
            if ep in evolution_phase:
                filtered_factors[fid] = factor
        
        print(f"符合 evolution_phase 条件的因子数量: {len(filtered_factors)}")
        factors = filtered_factors
        
        if len(factors) == 0:
            print("没有符合 evolution_phase 条件的因子，退出。")
            return

    # 如果 method 是 round_number，但没有提供 target_rounds，报错或提示
    if method == "round_number" and not target_rounds:
        print("警告: 使用 method='round_number' 但未指定 --target_rounds。将从所有因子中筛选（即无筛选）。")

    selected_factors = {}
    
    # 2. 根据 method 进行抽取
    if method == "random":
        print(f"执行随机抽取...")
        keys = list(factors.keys())
        # 如果 n 未指定，默认全部？或者报错？根据逻辑，random通常需要n
        # 如果 n 为 None，这里假设抽取全部（相当于 shuffle 后全选）
        count = n if n is not None else len(keys)
        
        if len(keys) <= count:
            print(f"可用因子数量 ({len(keys)}) <= 需求数量 ({count})，返回所有可用因子。")
            selected_factors = factors
        else:
            selected_keys = random.sample(keys, count)
            selected_factors = {k: factors[k] for k in selected_keys}
            
    elif method == "round_number":
        # round_number 模式：主要是基于 round 筛选（前面已做）。
        # 如果指定了 n，则随机抽取 n 个；如果没指定 n，则全部保留。
        print(f"执行 round_number 筛选抽取...")
        keys = list(factors.keys())
        
        if n is None:
            print(f"未指定数量，保留所有符合条件的 {len(keys)} 个因子。")
            selected_factors = factors
        else:
            if len(keys) <= n:
                print(f"符合条件的因子数量 ({len(keys)}) <= 需求数量 ({n})，返回所有。")
                selected_factors = factors
            else:
                print(f"从符合条件的 {len(keys)} 个因子中随机抽取 {n} 个。")
                selected_keys = random.sample(keys, n)
                selected_factors = {k: factors[k] for k in selected_keys}

    else:
        # 按指标抽取
        print(f"执行按 {method} 指标排序抽取 ({order})...")
        factor_metrics = []
        for fid, factor in factors.items():
            val = get_metric_value(factor, method)
            if val is not None:
                factor_metrics.append((fid, factor, val))
        
        print(f"拥有有效 {method} 指标的因子数量: {len(factor_metrics)}")
        
        # 排序
        reverse = (order == "desc")
        factor_metrics.sort(key=lambda x: x[2], reverse=reverse)
        
        # 确定抽取数量
        count = n if n is not None else len(factor_metrics)
        
        # 抽取
        top_items = factor_metrics[:count]
        selected_factors = {fid: factor for fid, factor, val in top_items}
        
        if top_items:
            print(f"选中因子的 {method} 范围: {top_items[0][2]} 到 {top_items[-1][2]}")

    # 生成文件名
    method_name = method
    if method not in ["random", "round_number"]:
        method_name = f"{method}_{order}" # 例如 IC_desc
        
    final_count = len(selected_factors)
    filename = generate_output_filename(source_path, method_name, final_count, rounds=target_rounds, phases=evolution_phase)
    output_path = os.path.join(output_dir, filename)
    
    # 保存
    rounds_info = f", rounds={target_rounds}" if target_rounds else ""
    phases_info = f", evolution_phase={evolution_phase}" if evolution_phase else ""
    note = f"Extracted {final_count} factors from {Path(source_path).name} using {method} ({order}){rounds_info}{phases_info}"
    save_factors(selected_factors, note, output_path, data.get("metadata"))

if __name__ == "__main__":
    main()
