#!/usr/bin/env python3
"""
生成 daily_pv.h5 文件工具
用于LLM驱动的因子计算

使用方式:
    python backtest_v2/generate_daily_pv.py
    python backtest_v2/generate_daily_pv.py --market csi500 --start 2020-01-01
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import qlib
from qlib.data import D
import pandas as pd


def generate_daily_pv(
    market='csi300',
    start_time='2016-01-01',
    end_time='2025-12-31',
    output_path=None,
    provider_uri='/home/tjxy/.qlib/qlib_data/cn_data'
):
    """
    生成 daily_pv.h5 文件
    
    Args:
        market: 股票池，如 'csi300', 'csi500'
        start_time: 开始时间
        end_time: 结束时间
        output_path: 输出路径，如果为None则使用默认路径
        provider_uri: Qlib数据路径
    """
    
    print("="*70)
    print("生成 daily_pv.h5 文件")
    print("="*70)
    
    # 初始化qlib
    print(f"\n初始化 Qlib: {provider_uri}")
    qlib.init(provider_uri=provider_uri, region='cn')
    
    # 获取股票列表
    print(f"\n获取股票池: {market}")
    instruments = D.instruments(market)
    stock_list = D.list_instruments(
        instruments,
        start_time=start_time,
        end_time=end_time,
        as_list=True
    )
    
    print(f"✓ 股票数量: {len(stock_list)}")
    print(f"  前10只: {stock_list[:10]}")
    
    # 获取数据
    print(f"\n获取价格和成交量数据...")
    print(f"  时间范围: {start_time} 到 {end_time}")
    
    data = D.features(
        stock_list,
        ['$open', '$high', '$low', '$close', '$volume', '$vwap'],
        start_time=start_time,
        end_time=end_time,
        freq='day'
    )
    
    print(f"✓ 数据获取完成")
    print(f"  数据形状: {data.shape}")
    print(f"  列: {list(data.columns)}")
    
    # 检查数据日期范围
    dates = sorted(data.index.get_level_values('datetime').unique())
    print(f"  日期范围: {dates[0].date()} 到 {dates[-1].date()}")
    print(f"  交易日数: {len(dates)}")
    
    # 检查数据质量
    zero_open = (data['$open'] == 0).sum()
    if zero_open > 0:
        print(f"  ⚠️  开盘价为0的记录: {zero_open} 条")
    
    # 确定输出路径
    if output_path is None:
        output_path = project_root / 'git_ignore_folder' / 'factor_implementation_source_data' / 'daily_pv.h5'
    else:
        output_path = Path(output_path)
    
    # 创建目录
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存为H5文件
    print(f"\n保存到: {output_path}")
    data.to_hdf(str(output_path), key='data')
    
    file_size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"✓ 文件生成成功")
    print(f"  文件大小: {file_size_mb:.2f} MB")
    print(f"  文件路径: {output_path.absolute()}")
    
    # 验证文件
    print(f"\n验证文件...")
    test_data = pd.read_hdf(str(output_path), key='data')
    print(f"✓ 文件验证通过")
    print(f"  读取数据形状: {test_data.shape}")
    print(f"  列: {list(test_data.columns)}")
    
    print("\n" + "="*70)
    print("完成！")
    print("="*70)
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description='生成 daily_pv.h5 文件')
    parser.add_argument(
        '--market',
        type=str,
        default='csi300',
        help='股票池 (默认: csi300)'
    )
    parser.add_argument(
        '--start',
        type=str,
        default='2016-01-01',
        help='开始时间 (默认: 2016-01-01)'
    )
    parser.add_argument(
        '--end',
        type=str,
        default='2025-12-31',
        help='结束时间 (默认: 2025-12-31)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='输出路径 (默认: git_ignore_folder/factor_implementation_source_data/daily_pv.h5)'
    )
    parser.add_argument(
        '--provider',
        type=str,
        default='/home/tjxy/.qlib/qlib_data/cn_data',
        help='Qlib数据路径'
    )
    
    args = parser.parse_args()
    
    try:
        generate_daily_pv(
            market=args.market,
            start_time=args.start,
            end_time=args.end,
            output_path=args.output,
            provider_uri=args.provider
        )
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

