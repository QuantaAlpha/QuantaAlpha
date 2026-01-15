#!/usr/bin/env python3
"""
验证指数数据是否正确
"""

import qlib
from qlib.data import D
import pandas as pd
import numpy as np

def main():
    qlib.init(provider_uri='/home/tjxy/.qlib/qlib_data/cn_data', region='cn')
    
    print("=" * 70)
    print("指数数据验证")
    print("=" * 70)
    
    # 检查指数数据
    indices = ['SH000300', 'SH000905', 'SH000001']  # 沪深300, 中证500, 上证指数
    names = ['沪深300', '中证500', '上证指数']
    
    for idx, name in zip(indices, names):
        try:
            data = D.features([idx], ['$close', '$open', '$high', '$low'], 
                             start_time='2022-01-01', end_time='2025-12-31', freq='day')
            
            if len(data) > 0:
                data = data.droplevel('instrument')
                
                print(f"\n{name} ({idx}):")
                print(f"  数据条数: {len(data)}")
                
                # 起始和结束价格
                first_close = data['$close'].iloc[0]
                last_close = data['$close'].iloc[-1]
                
                print(f"  起始日期: {data.index[0]}")
                print(f"  结束日期: {data.index[-1]}")
                print(f"  起始收盘价: {first_close:.2f}")
                print(f"  结束收盘价: {last_close:.2f}")
                print(f"  涨跌幅: {(last_close/first_close-1)*100:.2f}%")
                
                # 最近10个交易日
                print(f"\n  最近5个交易日:")
                recent = data.tail(5)
                for date, row in recent.iterrows():
                    date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10]
                    print(f"    {date_str}: C={row['$close']:.2f}")
                    
                # 检查数据是否有问题
                if first_close < 100:
                    print(f"\n  ⚠️ 起始价格{first_close:.2f}异常低，指数数据可能有问题!")
                    
        except Exception as e:
            print(f"\n{name} ({idx}): 获取失败 - {e}")
    
    # 手动验证提示
    print("\n" + "=" * 70)
    print("请手动验证以下数据:")
    print("=" * 70)
    print("""
真实数据参考 (2024年底):
- 沪深300: 约 3900 点左右
- 中证500: 约 5300 点左右
- 上证指数: 约 3300 点左右

如果上面显示的数据与真实数据差异很大，说明qlib数据有问题。

可以访问以下网站验证:
- 东方财富: https://quote.eastmoney.com/zs000300.html
- 新浪财经: https://finance.sina.com.cn/realstock/company/sh000300/nc.shtml
""")
    
    # 检查是否是复权问题
    print("\n" + "=" * 70)
    print("可能的数据问题原因:")
    print("=" * 70)
    print("""
1. qlib数据可能是复权后的价格
   - 前复权会导致历史价格被调整
   - 这可能导致涨跌幅计算出现偏差
   
2. 数据可能没有及时更新
   - 检查数据最后更新日期
   
3. 数据来源问题
   - qlib数据可能来自不同的数据源
""")

if __name__ == '__main__':
    main()

