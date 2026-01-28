#!/usr/bin/env python3
"""
因子缓存提取器

从主程序的日志和工作空间中提取已计算的因子数据，
转换为 backtest_v2 可直接使用的缓存格式。

功能:
1. 从日志中解析因子 ID 和工作空间 UUID 的对应关系
2. 把 result.h5 文件重命名并保存到缓存目录
3. 生成因子映射索引文件

使用方式:
    python tools/factor_cache_extractor.py --log-dir /path/to/log --output-dir /mnt/DATA/quantagent/QuantaAlpha/factor_cache
    
    # 指定实验 ID
    python tools/factor_cache_extractor.py --exp-id 2026-01-16_17-24-17-907337 --output-dir /mnt/DATA/quantagent/QuantaAlpha/factor_cache
"""

import argparse
import hashlib
import json
import pickle
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

# 默认路径配置 - 数据全部存储到 /mnt/DATA/quantagent
# 日志目录列表（新路径优先，旧路径兼容历史数据）
DEFAULT_LOG_DIRS = [
    "/mnt/DATA/quantagent/QuantaAlpha/log",  # 新路径
    "/home/tjxy/quantagent/QuantaAlpha/log",  # 旧路径（兼容历史数据）
]
DEFAULT_LOG_DIR = DEFAULT_LOG_DIRS[0]  # 主日志目录
# 工作空间基础目录（用于动态发现所有 workspace 目录）
WORKSPACE_BASE_DIRS = [
    "/mnt/DATA/quantagent/QuantaAlpha",  # 新路径基础目录
    "/home/tjxy/quantagent/QuantaAlpha/git_ignore_folder",  # 旧路径基础目录
]
DEFAULT_OUTPUT_DIR = "/mnt/DATA/quantagent/QuantaAlpha/factor_cache"
DEFAULT_INDEX_FILE = "/mnt/DATA/quantagent/QuantaAlpha/factor_cache_index.json"


def get_all_workspace_dirs() -> List[str]:
    """
    动态发现所有工作空间目录
    支持 RD-Agent_workspace 和 RD-Agent_workspace_{EXPERIMENT_ID} 格式
    """
    workspace_dirs = []
    
    for base_dir in WORKSPACE_BASE_DIRS:
        base_path = Path(base_dir)
        if not base_path.exists():
            continue
        
        # 查找所有匹配 RD-Agent_workspace* 的目录
        for ws_dir in base_path.iterdir():
            if ws_dir.is_dir() and ws_dir.name.startswith("RD-Agent_workspace"):
                workspace_dirs.append(str(ws_dir))
    
    # 去重并保持顺序（新路径优先）
    seen = set()
    result = []
    for d in workspace_dirs:
        if d not in seen:
            seen.add(d)
            result.append(d)
    
    return result


# 动态获取工作空间目录列表（兼容新旧格式）
DEFAULT_WORKSPACE_DIRS = get_all_workspace_dirs() or [
    "/mnt/DATA/quantagent/QuantaAlpha/RD-Agent_workspace",  # 默认回退
]


def get_cache_key(expr: str) -> str:
    """
    生成缓存键（与 backtest_v2/factor_calculator.py 中的方法一致）
    """
    return hashlib.md5(expr.encode()).hexdigest()


def find_coder_result_pkls(log_dir: Path, exp_id: Optional[str] = None) -> List[Path]:
    """
    查找所有 coder result 的 pkl 文件
    """
    pkl_files = []
    
    if exp_id:
        # 指定实验 ID
        exp_dirs = [log_dir / exp_id]
    else:
        # 遍历所有实验目录
        exp_dirs = [d for d in log_dir.iterdir() if d.is_dir() and d.name.startswith("2026-")]
    
    for exp_dir in exp_dirs:
        if not exp_dir.exists():
            print(f"⚠️  实验目录不存在: {exp_dir}")
            continue
        
        # 查找所有 "coder result" 目录下的 pkl 文件
        for pkl_file in exp_dir.rglob("*/d/coder result/*/*.pkl"):
            pkl_files.append(pkl_file)
    
    return pkl_files


def extract_factor_info_from_pkl(pkl_path: Path) -> List[Dict[str, Any]]:
    """
    从 pkl 文件中提取因子信息
    支持在多个 workspace 目录中查找 result.h5
    """
    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)
        
        if not isinstance(data, list):
            return []
        
        factors = []
        for item in data:
            if hasattr(item, 'workspace_path') and hasattr(item, 'target_task'):
                task = item.target_task
                original_workspace = Path(item.workspace_path)
                workspace_uuid = original_workspace.name  # UUID 目录名
            
                factor_info = {
                    'workspace_path': str(original_workspace),
                    'factor_name': getattr(task, 'factor_name', ''),
                    'factor_expression': getattr(task, 'factor_expression', ''),
                    'factor_description': getattr(task, 'factor_description', ''),
                    'pkl_source': str(pkl_path),
                }
                
                # 在多个可能的 workspace 目录中查找 result.h5
                result_h5_path = None
                for ws_dir in DEFAULT_WORKSPACE_DIRS:
                    candidate = Path(ws_dir) / workspace_uuid / "result.h5"
                    if candidate.exists():
                        result_h5_path = candidate
                        break
                
                # 也检查原始路径
                if result_h5_path is None:
                    original_h5 = original_workspace / "result.h5"
                    if original_h5.exists():
                        result_h5_path = original_h5
                
                factor_info['result_h5_exists'] = result_h5_path is not None
                factor_info['result_h5_path'] = str(result_h5_path) if result_h5_path else None
                
                if factor_info['factor_expression']:
                    factors.append(factor_info)
        
        return factors
    except Exception as e:
        print(f"⚠️  解析 pkl 文件失败: {pkl_path}, 错误: {e}")
        return []


def copy_result_to_cache(
    factor_info: Dict[str, Any],
    output_dir: Path,
    use_symlink: bool = False
) -> Optional[str]:
    """
    将 result.h5 复制/链接到缓存目录
    
    返回缓存文件名（不含路径）
    """
    if not factor_info.get('result_h5_exists') or not factor_info.get('result_h5_path'):
        return None
    
    result_h5_path = Path(factor_info['result_h5_path'])
    expr = factor_info['factor_expression']
    
    # 生成缓存键
    cache_key = get_cache_key(expr)
    cache_file = output_dir / f"{cache_key}.pkl"
    
    # 如果缓存已存在，跳过
    if cache_file.exists():
        return f"{cache_key}.pkl"
    
    try:
        # 读取 result.h5
        result = pd.read_hdf(result_h5_path, key='data')
        
        # 保存为 pkl（与 backtest_v2 的缓存格式一致）
        result.to_pickle(cache_file)
        
        return f"{cache_key}.pkl"
    except Exception as e:
        print(f"⚠️  处理因子失败: {factor_info['factor_name']}, 错误: {e}")
        return None
    

def extract_factors_to_cache(
    log_dir: Path = None,
    log_dirs: List[Path] = None,
    output_dir: Path = None,
    index_file: Path = None,
    exp_id: Optional[str] = None,
    verbose: bool = True
) -> int:
    """
    提取因子到缓存目录 (可被其他模块调用的 API)
    
    Args:
        log_dir: 日志目录（单个，向后兼容）
        log_dirs: 日志目录列表（多个，优先使用）
        output_dir: 缓存输出目录
        index_file: 索引文件路径
        exp_id: 指定实验 ID (可选)
        verbose: 是否打印详细信息
        
    Returns:
        int: 新增的因子数量
    """
    # 确定要搜索的日志目录列表
    if log_dirs is not None:
        search_log_dirs = [Path(d) for d in log_dirs]
    elif log_dir is not None:
        search_log_dirs = [Path(log_dir)]
    else:
        # 默认搜索新旧两个日志目录
        search_log_dirs = [Path(d) for d in DEFAULT_LOG_DIRS]
    
    output_dir = output_dir or Path(DEFAULT_OUTPUT_DIR)
    index_file = index_file or Path(DEFAULT_INDEX_FILE)
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
        
    # 从所有日志目录查找 pkl 文件
    if verbose:
        print("📂 扫描日志目录中的因子...")
    pkl_files = []
    for search_dir in search_log_dirs:
        if search_dir.exists():
            if verbose:
                print(f"   搜索: {search_dir}")
            pkl_files.extend(find_coder_result_pkls(search_dir, exp_id))
    
    if not pkl_files:
        if verbose:
            print("   未找到任何因子数据")
        return 0
    
    # 提取因子信息
    all_factors = []
    for pkl_file in pkl_files:
        factors = extract_factor_info_from_pkl(pkl_file)
        all_factors.extend(factors)
    
    # 统计有效因子
    valid_factors = [f for f in all_factors if f.get('result_h5_exists')]
    
    if verbose:
        print(f"   找到 {len(valid_factors)} 个有效因子")
    
    if not valid_factors:
        return 0
    
    # 去重
    unique_factors = {}
    for factor in valid_factors:
        expr = factor['factor_expression']
        if expr not in unique_factors:
            unique_factors[expr] = factor
    
    # 加载已有索引
    factor_index = {}
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                factor_index = json.load(f)
        except Exception:
            pass
    
    # 处理每个因子
        success_count = 0
        
    for expr, factor in unique_factors.items():
        cache_key = get_cache_key(expr)
        cache_file = output_dir / f"{cache_key}.pkl"
                
        if cache_file.exists():
            # 更新索引
            if cache_key not in factor_index:
                factor_index[cache_key] = {
                    'factor_name': factor['factor_name'],
                    'factor_expression': expr,
                    'cache_file': f"{cache_key}.pkl",
                    'added_at': datetime.now().isoformat(),
                }
            continue
        
        result_file = copy_result_to_cache(factor, output_dir)
        if result_file:
            success_count += 1
            factor_index[cache_key] = {
                'factor_name': factor['factor_name'],
                'factor_expression': expr,
                'factor_description': factor.get('factor_description', ''),
                'cache_file': result_file,
                'source_workspace': factor['workspace_path'],
                'added_at': datetime.now().isoformat(),
            }
    
    # 保存索引
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(factor_index, f, ensure_ascii=False, indent=2)
        
    if verbose and success_count > 0:
        print(f"   ✓ 新提取 {success_count} 个因子到缓存")
    
    return success_count


def main():
    parser = argparse.ArgumentParser(
        description='因子缓存提取器 - 从主程序日志提取已计算的因子数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 提取所有实验的因子缓存
  python tools/factor_cache_extractor.py
  
  # 指定实验 ID
  python tools/factor_cache_extractor.py --exp-id 2026-01-16_17-24-17-907337
  
  # 指定输出目录
  python tools/factor_cache_extractor.py --output-dir /mnt/DATA/quantagent/QuantaAlpha/factor_cache
        """
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default=DEFAULT_LOG_DIR,
        help=f'日志目录 (默认: {DEFAULT_LOG_DIR})'
    )
    
    parser.add_argument(
        '--exp-id',
        type=str,
        default=None,
        help='指定实验 ID (如: 2026-01-16_17-24-17-907337)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f'缓存输出目录 (默认: {DEFAULT_OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--index-file',
        type=str,
        default=DEFAULT_INDEX_FILE,
        help=f'因子索引文件 (默认: {DEFAULT_INDEX_FILE})'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅扫描，不复制文件'
    )
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    output_dir = Path(args.output_dir)
    index_file = Path(args.index_file)
    
    print("=" * 60)
    print("         因子缓存提取器")
    print("=" * 60)
    print(f"日志目录:     {log_dir}")
    print(f"输出目录:     {output_dir}")
    print(f"索引文件:     {index_file}")
    if args.exp_id:
        print(f"指定实验:     {args.exp_id}")
    if args.dry_run:
        print("模式:         仅扫描 (dry-run)")
    print()
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找所有 pkl 文件
    print("📂 扫描日志目录...")
    pkl_files = find_coder_result_pkls(log_dir, args.exp_id)
    print(f"   找到 {len(pkl_files)} 个 coder result pkl 文件")
    
    # 提取因子信息
    print("\n📊 提取因子信息...")
    all_factors = []
    for pkl_file in pkl_files:
        factors = extract_factor_info_from_pkl(pkl_file)
        all_factors.extend(factors)
    
    print(f"   提取到 {len(all_factors)} 个因子")
    
    # 统计有效因子（有 result.h5 的）
    valid_factors = [f for f in all_factors if f.get('result_h5_exists')]
    print(f"   其中有效因子（有 result.h5）: {len(valid_factors)} 个")
    
    if args.dry_run:
        print("\n🔍 Dry-run 模式，显示前 10 个因子:")
        for i, factor in enumerate(valid_factors[:10]):
            print(f"\n  [{i+1}] {factor['factor_name']}")
            print(f"      表达式: {factor['factor_expression'][:60]}...")
            print(f"      工作空间: {factor['workspace_path']}")
        if len(valid_factors) > 10:
            print(f"\n  ... 还有 {len(valid_factors) - 10} 个因子")
        return
    
    # 复制因子到缓存目录
    print(f"\n📦 复制因子到缓存目录: {output_dir}")
    
    # 去重：同一表达式只保留一个
    unique_factors = {}
    for factor in valid_factors:
        expr = factor['factor_expression']
        if expr not in unique_factors:
            unique_factors[expr] = factor
    
    print(f"   去重后唯一因子: {len(unique_factors)} 个")
    
    # 加载已有索引
    factor_index = {}
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                factor_index = json.load(f)
            print(f"   加载已有索引: {len(factor_index)} 个因子")
        except Exception as e:
            print(f"   ⚠️  加载索引失败: {e}")
    
    # 处理每个因子
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for expr, factor in unique_factors.items():
        cache_key = get_cache_key(expr)
        cache_file = output_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            skip_count += 1
            # 更新索引
            if cache_key not in factor_index:
                factor_index[cache_key] = {
                    'factor_name': factor['factor_name'],
                    'factor_expression': expr,
                    'cache_file': f"{cache_key}.pkl",
                    'added_at': datetime.now().isoformat(),
                }
            continue
        
        result_file = copy_result_to_cache(factor, output_dir)
        if result_file:
            success_count += 1
            # 更新索引
            factor_index[cache_key] = {
                'factor_name': factor['factor_name'],
                'factor_expression': expr,
                'factor_description': factor.get('factor_description', ''),
                'cache_file': result_file,
                'source_workspace': factor['workspace_path'],
                'added_at': datetime.now().isoformat(),
            }
        else:
            fail_count += 1
    
    # 保存索引
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(factor_index, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 提取完成!")
    print(f"   新增: {success_count} 个")
    print(f"   跳过（已存在）: {skip_count} 个")
    print(f"   失败: {fail_count} 个")
    print(f"   索引总数: {len(factor_index)} 个")
    print(f"\n📁 缓存目录: {output_dir}")
    print(f"📋 索引文件: {index_file}")
    
    # 显示缓存目录大小
    try:
        import subprocess
        result = subprocess.run(['du', '-sh', str(output_dir)], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"💾 缓存大小: {result.stdout.split()[0]}")
    except:
        pass


if __name__ == '__main__':
    main()

