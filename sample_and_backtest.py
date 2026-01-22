#!/usr/bin/env python3
"""
按 Rank IC 从高到低抽样因子并运行回测
"""

import json
import subprocess
import sys
from pathlib import Path

# 配置
SOURCE_JSON = "/home/tjxy/quantagent/AlphaAgent/all_factors_library_AA_claude_123_csi300.json"
OUTPUT_DIR = Path("/home/tjxy/quantagent/AlphaAgent/factor_library")
CONFIG_PATH = "/home/tjxy/quantagent/AlphaAgent/backtest_v2/config.yaml"
SUMMARY_PATH = "/home/tjxy/quantagent/AlphaAgent/backtest_v2_results/batch_summary.json"

def load_and_sort_factors():
    """加载因子并按 Rank IC 从高到低排序"""
    print(f"📂 加载因子库: {SOURCE_JSON}")
    
    with open(SOURCE_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    factors = data.get('factors', {})
    print(f"  总因子数: {len(factors)}")
    
    # 过滤并提取 Rank IC
    valid_factors = []
    for factor_id, factor_data in factors.items():
        backtest = factor_data.get('backtest_results', {})
        rank_ic = backtest.get('Rank IC')
        
        # 过滤掉 null 或无效的 Rank IC
        if rank_ic is not None and not (isinstance(rank_ic, float) and (rank_ic != rank_ic)):  # NaN check
            valid_factors.append({
                'factor_id': factor_id,
                'factor_data': factor_data,
                'rank_ic': rank_ic
            })
    
    print(f"  有效因子数 (Rank IC 非空): {len(valid_factors)}")
    
    # 按 Rank IC 从高到低排序
    valid_factors.sort(key=lambda x: x['rank_ic'], reverse=True)
    
    # 显示 Top 5
    print("\n  Top 5 因子 (按 Rank IC):")
    for i, f in enumerate(valid_factors[:5]):
        print(f"    {i+1}. {f['factor_data'].get('factor_name', 'N/A')}: Rank IC = {f['rank_ic']:.6f}")
    
    return valid_factors, data.get('metadata', {})

def create_sample_json(factors, sample_size, output_path, metadata):
    """创建抽样后的 JSON 文件"""
    sampled = factors[:sample_size]
    
    output_data = {
        "metadata": {
            **metadata,
            "total_factors": len(sampled),
            "sampling_method": "Rank IC 降序",
            "source_file": SOURCE_JSON
        },
        "factors": {f['factor_id']: f['factor_data'] for f in sampled}
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 生成: {output_path.name} ({len(sampled)} 个因子)")
    return output_path

def run_backtest(factor_json_path):
    """运行回测"""
    exp_name = factor_json_path.stem
    print(f"\n🚀 运行回测: {exp_name}")
    
    cmd = [
        sys.executable,
        "/home/tjxy/quantagent/AlphaAgent/backtest_v2/run_backtest.py",
        "-c", CONFIG_PATH,
        "--factor-source", "custom",
        "--factor-json", str(factor_json_path),
        "-e", exp_name
    ]
    
    result = subprocess.run(cmd, cwd="/home/tjxy/quantagent/AlphaAgent")
    return result.returncode == 0

def display_results():
    """显示回测结果表格"""
    print("\n" + "="*100)
    print("📊 回测结果汇总 (超额有成本)")
    print("="*100)
    
    with open(SUMMARY_PATH, 'r', encoding='utf-8') as f:
        summary = json.load(f)
    
    # 过滤出本次实验的结果
    target_prefix = "AA_RANKIC_top_"
    results = [r for r in summary if r.get('name', '').startswith(target_prefix)]
    
    if not results:
        print("⚠️ 未找到本次实验结果，显示所有最近结果:")
        results = summary[-6:]
    
    # 按因子数量排序
    results.sort(key=lambda x: x.get('num_factors', 0))
    
    # 打印表头
    headers = ["因子库名称", "因子数", "IC", "ICIR", "Rank IC", "Rank ICIR", 
               "年化收益", "信息比率", "最大回撤", "卡尔玛比率"]
    
    # 计算列宽
    col_widths = [35, 8, 10, 10, 10, 10, 10, 10, 10, 10]
    
    # 打印表头
    header_row = "|"
    for h, w in zip(headers, col_widths):
        header_row += f" {h:^{w}} |"
    print(header_row)
    print("|" + "|".join(["-" * (w + 2) for w in col_widths]) + "|")
    
    # 打印数据行
    for r in results:
        name = r.get('name', 'N/A')[:35]
        row = f"| {name:<35} |"
        row += f" {r.get('num_factors', 'N/A'):>8} |"
        row += f" {r.get('IC', 0):>10.6f} |" if r.get('IC') else " {:>10} |".format('N/A')
        row += f" {r.get('ICIR', 0):>10.6f} |" if r.get('ICIR') else " {:>10} |".format('N/A')
        row += f" {r.get('Rank_IC', 0):>10.6f} |" if r.get('Rank_IC') else " {:>10} |".format('N/A')
        row += f" {r.get('Rank_ICIR', 0):>10.6f} |" if r.get('Rank_ICIR') else " {:>10} |".format('N/A')
        row += f" {r.get('annualized_return', 0):>10.4f} |" if r.get('annualized_return') else " {:>10} |".format('N/A')
        row += f" {r.get('information_ratio', 0):>10.4f} |" if r.get('information_ratio') else " {:>10} |".format('N/A')
        row += f" {r.get('max_drawdown', 0):>10.4f} |" if r.get('max_drawdown') else " {:>10} |".format('N/A')
        row += f" {r.get('calmar_ratio', 0):>10.4f} |" if r.get('calmar_ratio') else " {:>10} |".format('N/A')
        print(row)
    
    print("="*100)
    return results

def main():
    print("="*70)
    print("📊 因子抽样与回测实验")
    print("="*70)
    
    # 1. 加载并排序因子
    valid_factors, metadata = load_and_sort_factors()
    
    # 2. 计算 k
    total = len(valid_factors)
    k = total // 6
    print(f"\n📐 总因子数: {total}, k = {total} // 6 = {k}")
    
    # 3. 生成抽样文件
    print("\n📁 生成抽样因子库文件:")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    sample_files = []
    for i, multiplier in enumerate([1, 2, 3, 4, 5, 6], 1):
        sample_size = min(k * multiplier, total)  # 不超过总数
        output_name = f"AA_RANKIC_top_{sample_size}.json"
        output_path = OUTPUT_DIR / output_name
        create_sample_json(valid_factors, sample_size, output_path, metadata)
        sample_files.append(output_path)
    
    # 4. 运行回测
    print("\n" + "="*70)
    print("🔄 开始运行回测...")
    print("="*70)
    
    for sample_file in sample_files:
        success = run_backtest(sample_file)
        if not success:
            print(f"⚠️ 回测失败: {sample_file.name}")
    
    # 5. 显示结果
    display_results()

if __name__ == "__main__":
    main()

