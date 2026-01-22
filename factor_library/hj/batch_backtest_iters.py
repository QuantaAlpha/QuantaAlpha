#!/usr/bin/env python3
"""
批量回测脚本 - 5个iter的因子文件
时间范围: 2022-2025
只计算因子指标: IC, RankIC, ICIR, RankICIR
"""

import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# 路径配置
PROJECT_ROOT = Path("/home/tjxy/quantagent/AlphaAgent")
BACKTEST_SCRIPT = PROJECT_ROOT / "backtest_v2" / "run_backtest.py"
CONFIG_FILE = PROJECT_ROOT / "backtest_v2" / "config.yaml"
FACTOR_DIR = PROJECT_ROOT / "factor_library" / "hj"

# 5个iter的因子文件配置 (使用清洗后的因子库)
ITER_CONFIGS = [
    {
        "name": "iter1_round_1_2",
        "file": "RANKIC_desc_rounds_1_2_29_QA_round41_best_deepseek_aliyun_all_csi300_clean.json",
        "rounds": "1-2",
    },
    {
        "name": "iter2_round_3_4", 
        "file": "RANKIC_desc_rounds_3_4_42_QA_round41_best_deepseek_aliyun_all_csi300_clean.json",
        "rounds": "3-4",
    },
    {
        "name": "iter3_round_5_6",
        "file": "RANKIC_desc_rounds_5_6_42_QA_round41_best_deepseek_aliyun_all_csi300_clean.json",
        "rounds": "5-6",
    },
    {
        "name": "iter4_round_7_8",
        "file": "RANKIC_desc_rounds_7_8_52_QA_round41_best_deepseek_aliyun_all_csi300_clean.json",
        "rounds": "7-8",
    },
    {
        "name": "iter5_round_9_10",
        "file": "RANKIC_desc_rounds_9_10_52_QA_round41_best_deepseek_aliyun_all_csi300_clean.json",
        "rounds": "9-10",
    },
]


def run_backtest(iter_config: dict) -> dict:
    """执行单个iter的回测"""
    factor_file = FACTOR_DIR / iter_config["file"]
    iter_name = iter_config["name"]
    
    if not factor_file.exists():
        return {
            "name": iter_name,
            "success": False,
            "error": f"因子文件不存在: {factor_file}",
            "duration": 0,
        }
    
    cmd = [
        sys.executable,
        str(BACKTEST_SCRIPT),
        "-c", str(CONFIG_FILE),
        "-s", "custom",
        "-j", str(factor_file),
        "-t", "default",  # 2022-2025
        "-e", iter_name,
        "--ic-only",  # 只计算IC指标
    ]
    
    print(f"\n{'='*60}")
    print(f"开始回测: {iter_name} (rounds {iter_config['rounds']})")
    print(f"因子文件: {factor_file.name}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=False,  # 直接输出到终端
            text=True,
        )
        
        duration = time.time() - start_time
        
        return {
            "name": iter_name,
            "success": result.returncode == 0,
            "error": None if result.returncode == 0 else f"Exit code: {result.returncode}",
            "duration": duration,
        }
        
    except Exception as e:
        duration = time.time() - start_time
        return {
            "name": iter_name,
            "success": False,
            "error": str(e),
            "duration": duration,
        }


def main():
    print("=" * 60)
    print("批量回测脚本 - 5个iter因子")
    print(f"时间范围: 2022-2025")
    print(f"模式: IC-only (仅计算 IC/ICIR/RankIC/RankICIR)")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    total_start = time.time()
    results = []
    
    for i, iter_config in enumerate(ITER_CONFIGS):
        print(f"\n[{i+1}/{len(ITER_CONFIGS)}] 处理 {iter_config['name']}...")
        result = run_backtest(iter_config)
        results.append(result)
        
        status = "✅ 成功" if result["success"] else f"❌ 失败: {result['error']}"
        print(f"{status} (耗时: {result['duration']:.1f}s)")
    
    total_duration = time.time() - total_start
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("回测汇总")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    
    print(f"\n{'Iter':<20} {'Rounds':<10} {'状态':<10} {'耗时':<10}")
    print("-" * 50)
    
    for i, (config, result) in enumerate(zip(ITER_CONFIGS, results)):
        status = "✅" if result["success"] else "❌"
        duration_str = f"{result['duration']:.1f}s"
        print(f"{config['name']:<20} {config['rounds']:<10} {status:<10} {duration_str:<10}")
    
    print("-" * 50)
    print(f"总计: {success_count}/{len(results)} 成功")
    print(f"总耗时: {total_duration/60:.1f} 分钟")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

