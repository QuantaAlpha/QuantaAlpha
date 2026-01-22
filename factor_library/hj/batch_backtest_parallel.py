#!/usr/bin/env python3
"""
并行批量回测脚本 - AA_claude和QA_claude因子库
支持多进程并行执行回测

使用方式:
    python batch_backtest_parallel.py              # 默认并行度4
    python batch_backtest_parallel.py -j 8         # 指定并行度8
    python batch_backtest_parallel.py --sequential # 顺序执行
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# 路径配置
PROJECT_ROOT = Path("/home/tjxy/quantagent/AlphaAgent")
BACKTEST_SCRIPT = PROJECT_ROOT / "backtest_v2" / "run_backtest.py"
CONFIG_FILE = PROJECT_ROOT / "backtest_v2" / "config.yaml"
FACTOR_DIR = PROJECT_ROOT / "factor_library" / "hj"

# 所有需要回测的因子文件
BACKTEST_TASKS = [
    # AA_claude iter1-5
    {"name": "AA_claude_iter1", "file": "AA_claude_iter1_32.json"},
    {"name": "AA_claude_iter2", "file": "AA_claude_iter2_32.json"},
    {"name": "AA_claude_iter3", "file": "AA_claude_iter3_32.json"},
    {"name": "AA_claude_iter4", "file": "AA_claude_iter4_31.json"},
    {"name": "AA_claude_iter5", "file": "AA_claude_iter5_31.json"},
    # QA_claude iter1-5
    {"name": "QA_claude_iter1", "file": "QA_claude_iter1_round_1_2_60.json"},
    {"name": "QA_claude_iter2", "file": "QA_claude_iter2_round_3_4_57.json"},
    {"name": "QA_claude_iter3", "file": "QA_claude_iter3_round_5_6_57.json"},
    {"name": "QA_claude_iter4", "file": "QA_claude_iter4_round_7_8_57.json"},
    {"name": "QA_claude_iter5", "file": "QA_claude_iter5_round_9_10_57.json"},
]


def run_single_backtest(task: dict) -> dict:
    """执行单个回测任务"""
    factor_file = FACTOR_DIR / task["file"]
    task_name = task["name"]
    
    if not factor_file.exists():
        return {
            "name": task_name,
            "success": False,
            "error": f"文件不存在: {factor_file}",
            "duration": 0,
        }
    
    cmd = [
        sys.executable,
        str(BACKTEST_SCRIPT),
        "-c", str(CONFIG_FILE),
        "-s", "custom",
        "-j", str(factor_file),
        "-t", "default",  # 2022-2025
        "-e", task_name,
        # "--ic-only",  # 只计算IC指标
    ]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=3800,  # 30分钟超时
        )
        
        duration = time.time() - start_time
        
        success = result.returncode == 0
        error = None
        if not success:
            # 提取错误信息
            error_lines = result.stderr.split('\n') if result.stderr else []
            error = error_lines[-5:] if len(error_lines) > 5 else error_lines
            error = '\n'.join(error) if error else f"Exit code: {result.returncode}"
        
        return {
            "name": task_name,
            "success": success,
            "error": error,
            "duration": duration,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "name": task_name,
            "success": False,
            "error": "超时 (>30分钟)",
            "duration": 3800,
        }
    except Exception as e:
        return {
            "name": task_name,
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time,
        }


def run_parallel(tasks: list, max_workers: int) -> list:
    """并行执行回测任务"""
    results = []
    
    print(f"\n🚀 启动并行回测 (并行度: {max_workers})")
    print(f"📋 任务总数: {len(tasks)}")
    print("-" * 60)
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_task = {executor.submit(run_single_backtest, task): task for task in tasks}
        
        # 收集结果
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
                
                status = "✅" if result["success"] else "❌"
                print(f"{status} {result['name']:<25} 耗时: {result['duration']:.1f}s")
                
                if not result["success"] and result.get("error"):
                    print(f"   错误: {result['error'][:100]}...")
                    
            except Exception as e:
                print(f"❌ {task['name']:<25} 异常: {e}")
                results.append({
                    "name": task["name"],
                    "success": False,
                    "error": str(e),
                    "duration": 0,
                })
    
    return results


def run_sequential(tasks: list) -> list:
    """顺序执行回测任务"""
    results = []
    
    print(f"\n🔄 顺序执行回测")
    print(f"📋 任务总数: {len(tasks)}")
    print("-" * 60)
    
    for i, task in enumerate(tasks):
        print(f"\n[{i+1}/{len(tasks)}] 开始: {task['name']}")
        result = run_single_backtest(task)
        results.append(result)
        
        status = "✅" if result["success"] else "❌"
        print(f"{status} 完成: {task['name']} 耗时: {result['duration']:.1f}s")
        
        if not result["success"] and result.get("error"):
            print(f"   错误: {result['error'][:200]}")
    
    return results


def print_summary(results: list, total_duration: float):
    """打印汇总结果"""
    print("\n" + "=" * 60)
    print("回测汇总")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    
    # 分组显示
    aa_results = [r for r in results if r["name"].startswith("AA_")]
    qa_results = [r for r in results if r["name"].startswith("QA_")]
    
    print(f"\n{'任务':<25} {'状态':<8} {'耗时':<10}")
    print("-" * 45)
    
    print("\n[AA_claude]")
    for r in sorted(aa_results, key=lambda x: x["name"]):
        status = "✅" if r["success"] else "❌"
        print(f"  {r['name']:<23} {status:<8} {r['duration']:.1f}s")
    
    print("\n[QA_claude]")
    for r in sorted(qa_results, key=lambda x: x["name"]):
        status = "✅" if r["success"] else "❌"
        print(f"  {r['name']:<23} {status:<8} {r['duration']:.1f}s")
    
    print("-" * 45)
    print(f"成功: {success_count}/{len(results)}")
    print(f"总耗时: {total_duration/60:.1f} 分钟")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="并行批量回测脚本")
    parser.add_argument("-j", "--jobs", type=int, default=4,
                        help="并行度 (默认: 4)")
    parser.add_argument("--sequential", action="store_true",
                        help="顺序执行 (不并行)")
    parser.add_argument("--aa-only", action="store_true",
                        help="只回测 AA_claude")
    parser.add_argument("--qa-only", action="store_true",
                        help="只回测 QA_claude")
    
    args = parser.parse_args()
    
    # 筛选任务
    tasks = BACKTEST_TASKS.copy()
    if args.aa_only:
        tasks = [t for t in tasks if t["name"].startswith("AA_")]
    elif args.qa_only:
        tasks = [t for t in tasks if t["name"].startswith("QA_")]
    
    print("=" * 60)
    print("批量回测脚本 - AA_claude & QA_claude 因子库")
    print(f"时间范围: 2022-2025")
    print(f"模式: 完整回测 (IC + 策略指标)")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    total_start = time.time()
    
    if args.sequential:
        results = run_sequential(tasks)
    else:
        # 限制最大并行度
        max_workers = min(args.jobs, len(tasks), multiprocessing.cpu_count())
        results = run_parallel(tasks, max_workers)
    
    total_duration = time.time() - total_start
    
    print_summary(results, total_duration)
    
    success_count = sum(1 for r in results if r["success"])
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

