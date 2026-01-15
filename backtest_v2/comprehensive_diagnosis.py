#!/usr/bin/env python3
"""
综合诊断脚本 - 系统检查回测数据和代码问题
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_header(title):
    print(f"\n{'='*70}")
    print(f"📊 {title}")
    print(f"{'='*70}")

def print_section(title):
    print(f"\n{'─'*50}")
    print(f"  {title}")
    print(f"{'─'*50}")

class ComprehensiveDiagnosis:
    def __init__(self):
        self.provider_uri = '/home/tjxy/.qlib/qlib_data/cn_data'
        self.issues = []
        self.warnings = []
        
    def run_all_checks(self):
        """运行所有检查"""
        print_header("回测系统综合诊断")
        print(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"数据源: {self.provider_uri}")
        
        # 1. 检查数据格式和读取方式
        self.check_data_format()
        
        # 2. 检查缺失值处理
        self.check_missing_values()
        
        # 3. 检查数据完整性
        self.check_data_integrity()
        
        # 4. 检查异常值
        self.check_abnormal_values()
        
        # 5. 抽样验证数据正确性
        self.verify_sample_data()
        
        # 6. 检查潜在数据泄露
        self.check_data_leakage()
        
        # 7. 对比标准结果
        self.compare_benchmark()
        
        # 输出总结
        self.print_summary()
        
    def check_data_format(self):
        """检查数据格式"""
        print_section("1. 数据格式检查")
        
        try:
            import qlib
            qlib.init(provider_uri=self.provider_uri, region='cn')
            from qlib.data import D
            
            # 检查数据目录结构
            features_path = Path(self.provider_uri) / 'features'
            instruments_path = Path(self.provider_uri) / 'instruments'
            calendars_path = Path(self.provider_uri) / 'calendars'
            
            print(f"✓ 数据目录存在:")
            print(f"   - features: {features_path.exists()}")
            print(f"   - instruments: {instruments_path.exists()}")
            print(f"   - calendars: {calendars_path.exists()}")
            
            # 检查数据格式 (qlib bin format)
            if features_path.exists():
                sample_stocks = list(features_path.iterdir())[:3]
                print(f"\n  样本股票目录: {[s.name for s in sample_stocks]}")
                
                if sample_stocks:
                    first_stock = sample_stocks[0]
                    data_files = list(first_stock.iterdir())[:5]
                    print(f"  数据文件格式: {[f.name for f in data_files]}")
                    
                    # qlib使用.bin格式存储数据，不是h5
                    if any('.bin' in str(f) for f in data_files):
                        print(f"  ✓ 数据格式: Qlib原生bin格式 (直接读取，非H5)")
                    else:
                        print(f"  ⚠ 数据文件列表: {data_files}")
            
            self.qlib_inited = True
            print("✓ Qlib初始化成功")
            
        except Exception as e:
            print(f"✗ Qlib初始化失败: {e}")
            self.issues.append(f"Qlib初始化失败: {e}")
            self.qlib_inited = False
            
    def check_missing_values(self):
        """检查缺失值处理"""
        print_section("2. 缺失值处理检查")
        
        if not self.qlib_inited:
            print("⚠ Qlib未初始化，跳过此检查")
            return
            
        try:
            from qlib.data import D
            
            # 获取CSI300股票数据
            instruments = D.instruments('csi300')
            stock_list = D.list_instruments(instruments, start_time='2022-01-01', 
                                           end_time='2025-12-26', as_list=True)
            
            print(f"CSI300股票池大小: {len(stock_list)}")
            
            # 抽取部分股票检查
            sample_stocks = stock_list[:20]
            
            fields = ['$open', '$high', '$low', '$close', '$volume', '$vwap']
            data = D.features(sample_stocks, fields, start_time='2022-01-01', 
                             end_time='2025-12-26', freq='day')
            
            print(f"\n缺失值统计:")
            print(f"  总记录数: {len(data)}")
            
            for col in fields:
                if col in data.columns:
                    null_count = data[col].isna().sum()
                    zero_count = (data[col] == 0).sum()
                    null_pct = null_count / len(data) * 100
                    zero_pct = zero_count / len(data) * 100
                    print(f"  {col}:")
                    print(f"    - NaN值: {null_count} ({null_pct:.2f}%)")
                    print(f"    - 零值: {zero_count} ({zero_pct:.2f}%)")
                    
                    if zero_pct > 1 and col in ['$open', '$close']:
                        self.warnings.append(f"{col}有{zero_pct:.2f}%的零值，可能是数据问题")
            
            # 检查Fillna的实际行为
            print(f"\n⚠ 重要: Qlib Fillna处理器默认使用 fillna(0)，而非保留NaN")
            print(f"  如果原始数据有NaN，会被填充为0，这可能导致:")
            print(f"    - 停牌股票的价格变为0")
            print(f"    - 异常低的收益率计算")
            
        except Exception as e:
            print(f"✗ 缺失值检查失败: {e}")
            self.issues.append(f"缺失值检查失败: {e}")
            
    def check_data_integrity(self):
        """检查数据完整性"""
        print_section("3. 数据完整性检查")
        
        if not self.qlib_inited:
            return
            
        try:
            from qlib.data import D
            
            # 获取交易日历
            instruments = D.instruments('csi300')
            stock_list = D.list_instruments(instruments, start_time='2022-01-01', 
                                           end_time='2025-12-26', as_list=True)
            
            data = D.features(stock_list[:10], ['$close'], start_time='2022-01-01', 
                             end_time='2025-12-26', freq='day')
            
            # 获取日期列表
            dates = sorted(data.index.get_level_values('datetime').unique())
            
            print(f"数据日期范围: {dates[0]} 到 {dates[-1]}")
            print(f"总交易日数: {len(dates)}")
            
            # 按年统计
            date_series = pd.Series(dates)
            yearly_counts = {}
            for year in [2022, 2023, 2024, 2025]:
                year_dates = date_series[date_series.dt.year == year]
                yearly_counts[year] = len(year_dates)
                print(f"  {year}年: {len(year_dates)} 个交易日")
            
            # A股一年通常有约242个交易日
            for year, count in yearly_counts.items():
                if year < 2025:  # 2025年还没结束
                    if count < 200:
                        self.warnings.append(f"{year}年交易日数({count})偏少，正常约242天")
                    elif count > 250:
                        self.warnings.append(f"{year}年交易日数({count})偏多，可能数据有问题")
                        
        except Exception as e:
            print(f"✗ 完整性检查失败: {e}")
            
    def check_abnormal_values(self):
        """检查异常值"""
        print_section("4. 异常值检查")
        
        if not self.qlib_inited:
            return
            
        try:
            from qlib.data import D
            
            instruments = D.instruments('csi300')
            stock_list = D.list_instruments(instruments, start_time='2022-01-01', 
                                           end_time='2025-12-26', as_list=True)
            
            data = D.features(stock_list[:30], ['$open', '$close', '$high', '$low', '$volume'], 
                             start_time='2022-01-01', end_time='2025-12-26', freq='day')
            
            print(f"\n异常值统计:")
            
            # 开盘价为0
            zero_open = data[data['$open'] == 0]
            print(f"  开盘价=0: {len(zero_open)} 条")
            
            # 收盘价为0
            zero_close = data[data['$close'] == 0]
            print(f"  收盘价=0: {len(zero_close)} 条")
            
            # 高价低于收盘价
            invalid_high = data[data['$high'] < data['$close']]
            print(f"  高价<收盘价: {len(invalid_high)} 条")
            
            # 低价高于收盘价
            invalid_low = data[data['$low'] > data['$close']]
            print(f"  低价>收盘价: {len(invalid_low)} 条")
            
            # 单日涨跌幅超过20%
            data['return'] = data.groupby(level='instrument')['$close'].pct_change()
            extreme_returns = data[abs(data['return']) > 0.20]
            print(f"  单日涨跌>20%: {len(extreme_returns)} 条")
            
            if len(zero_open) > 100:
                self.issues.append(f"发现{len(zero_open)}条开盘价为0的记录，会影响回测准确性")
                
            if len(zero_close) > 0:
                self.issues.append(f"发现{len(zero_close)}条收盘价为0的记录，严重数据问题")
                
        except Exception as e:
            print(f"✗ 异常值检查失败: {e}")
            
    def verify_sample_data(self):
        """抽样验证数据正确性"""
        print_section("5. 抽样数据验证 (与公开数据对比)")
        
        if not self.qlib_inited:
            return
            
        try:
            from qlib.data import D
            
            # 选择几只大盘股进行验证
            test_stocks = ['SH600519', 'SH601318', 'SZ000858', 'SH600036', 'SZ000001']
            
            print("抽取CSI300成分股数据与实际行情对比:")
            print("(建议手动到东方财富/新浪财经核对以下数据)\n")
            
            for stock in test_stocks:
                try:
                    data = D.features([stock], ['$open', '$close', '$high', '$low', '$volume'], 
                                     start_time='2024-01-02', end_time='2024-01-05', freq='day')
                    
                    if len(data) > 0:
                        print(f"\n{stock}:")
                        latest = data.head(3)
                        for idx, row in latest.iterrows():
                            date = idx[0].strftime('%Y-%m-%d')
                            print(f"  {date}: O={row['$open']:.2f}, C={row['$close']:.2f}, H={row['$high']:.2f}, L={row['$low']:.2f}")
                    else:
                        print(f"\n{stock}: 无数据")
                        
                except Exception as e:
                    print(f"\n{stock}: 获取失败 - {e}")
                    
            print("\n📝 请手动验证上述数据是否与公开行情一致")
            print("   可参考: https://quote.eastmoney.com/")
            
        except Exception as e:
            print(f"✗ 抽样验证失败: {e}")
            
    def check_data_leakage(self):
        """检查数据泄露"""
        print_section("6. 数据泄露检查")
        
        print("检查配置中的数据泄露风险:\n")
        
        # 读取配置
        config_path = Path(__file__).parent / 'config.yaml'
        if config_path.exists():
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # 检查Label定义
            label = config.get('dataset', {}).get('label', '')
            print(f"1. Label定义: {label}")
            
            if 'Ref' in label:
                # 解析Ref的参数
                import re
                refs = re.findall(r'Ref\(\$\w+,\s*(-?\d+)\)', label)
                refs = [int(r) for r in refs]
                print(f"   Ref偏移量: {refs}")
                
                if any(r >= 0 for r in refs):
                    self.issues.append("Label使用了Ref(x, >=0)，可能存在数据泄露！")
                    print(f"   ✗ 警告: 可能存在数据泄露！正向Ref使用了未来数据")
                else:
                    print(f"   ✓ Label使用负向Ref，无未来数据泄露")
            
            # 检查数据集划分
            segments = config.get('dataset', {}).get('segments', {})
            train = segments.get('train', [])
            valid = segments.get('valid', [])
            test = segments.get('test', [])
            
            print(f"\n2. 数据集划分:")
            print(f"   训练集: {train[0]} ~ {train[1]}")
            print(f"   验证集: {valid[0]} ~ {valid[1]}")
            print(f"   测试集: {test[0]} ~ {test[1]}")
            
            # 检查时间顺序
            if train[1] >= valid[0] or valid[1] >= test[0]:
                self.issues.append("数据集划分有时间重叠，可能导致数据泄露")
                print(f"   ✗ 警告: 数据集可能有时间重叠!")
            else:
                print(f"   ✓ 数据集时间划分正确，无重叠")
            
            # 检查因子计算
            print(f"\n3. 因子表达式检查:")
            from backtest_v2.factor_loader import FactorLoader
            loader = FactorLoader(config)
            factors, _ = loader.load_factors()
            
            future_data_patterns = ['Ref($close, -', 'Ref($open, -', 'Ref($high, -', 'Ref($low, -']
            for name, expr in list(factors.items())[:5]:
                print(f"   {name}: {expr[:50]}...")
                
            # 注意：Ref(x, -n) 在qlib中表示未来数据
            has_future = False
            for name, expr in factors.items():
                if 'Ref' in expr and ', -' in expr:
                    # qlib中Ref($close, -1)表示未来1天的数据
                    has_future = True
                    
            if has_future:
                print(f"\n   ⚠ 注意: 因子中使用了Ref(x, -n)，这在qlib中表示未来数据")
                print(f"   但这通常用于Label定义，因子本身不应使用未来数据")
                
        else:
            print(f"⚠ 未找到配置文件: {config_path}")
            
    def compare_benchmark(self):
        """对比标准结果"""
        print_section("7. 结果合理性分析")
        
        # 读取当前结果
        results_path = Path(__file__).parent.parent / 'backtest_v2_results' / 'backtest_metrics.json'
        
        if results_path.exists():
            with open(results_path, 'r') as f:
                results = json.load(f)
                
            metrics = results.get('metrics', {})
            
            print("当前回测结果:")
            print(f"  IC: {metrics.get('IC', 'N/A'):.4f}")
            print(f"  ICIR: {metrics.get('ICIR', 'N/A'):.4f}")
            print(f"  Rank IC: {metrics.get('Rank IC', 'N/A'):.4f}")
            print(f"  年化收益: {metrics.get('annualized_return', 'N/A'):.2%}")
            print(f"  信息比率: {metrics.get('information_ratio', 'N/A'):.4f}")
            print(f"  最大回撤: {metrics.get('max_drawdown', 'N/A'):.2%}")
            print(f"  Calmar比率: {metrics.get('calmar_ratio', 'N/A'):.4f}")
            
            print(f"\n标准参考值 (Qlib Alpha158 on CSI300, 通常范围):")
            print(f"  IC: 0.03 ~ 0.06")
            print(f"  ICIR: 0.3 ~ 0.8")
            print(f"  年化超额收益: 5% ~ 20%")
            print(f"  最大回撤: -20% ~ -40%")
            
            # 分析异常
            ic = metrics.get('IC', 0)
            ann_ret = metrics.get('annualized_return', 0)
            max_dd = metrics.get('max_drawdown', 0)
            
            print(f"\n异常分析:")
            
            # IC分析
            if ic < 0.02:
                print(f"  ⚠ IC={ic:.4f}偏低，因子预测能力较弱")
            elif ic > 0.08:
                print(f"  ⚠ IC={ic:.4f}异常高，可能存在数据泄露或过拟合")
            else:
                print(f"  ✓ IC={ic:.4f}在合理范围内")
            
            # 收益分析
            if ann_ret > 0.30:
                print(f"  ⚠ 年化收益{ann_ret:.2%}异常高，可能存在问题:")
                print(f"     - 可能原因1: 回测区间选择性偏差")
                print(f"     - 可能原因2: 交易成本计算不准确")
                print(f"     - 可能原因3: 策略实际上是在做空指数（如果基准选择有问题）")
            elif ann_ret < 0:
                print(f"  ⚠ 年化收益为负{ann_ret:.2%}，因子可能无效")
            else:
                print(f"  ✓ 年化收益{ann_ret:.2%}在合理范围")
                
            # 回撤分析
            if abs(max_dd) > 0.45:
                print(f"  ⚠ 最大回撤{max_dd:.2%}较大")
                print(f"     - 2022-2024年A股确实经历了大熊市")
                print(f"     - 但48%回撤仍然偏高，检查是否有极端交易")
            else:
                print(f"  ✓ 最大回撤{max_dd:.2%}在可接受范围")
                
            # 综合分析
            print(f"\n综合判断:")
            if ic < 0.05 and ann_ret > 0.30:
                print(f"  ⚠ IC偏低但收益很高，这不太合理:")
                print(f"     - IC=0.044表示因子预测能力一般")
                print(f"     - 但年化收益35%+非常高")
                print(f"     - 这种不匹配通常说明:")
                print(f"       1. 回测有偏（如未考虑停牌、涨跌停）")
                print(f"       2. 基准选择问题（超额收益计算有误）")
                print(f"       3. 交易成本低估")
                self.issues.append("IC与收益不匹配，需要详细排查")
            
        else:
            print(f"⚠ 未找到结果文件: {results_path}")
            
    def print_summary(self):
        """打印总结"""
        print_header("诊断总结")
        
        if self.issues:
            print("\n🔴 发现的问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        else:
            print("\n✓ 未发现严重问题")
            
        if self.warnings:
            print("\n🟡 警告:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
                
        print("\n📋 建议检查项:")
        print("   1. 手动验证抽样股票数据与公开行情是否一致")
        print("   2. 检查Fillna是否将停牌股票价格填充为0")
        print("   3. 确认benchmark指数是否正确（SH000905 vs SH000300）")
        print("   4. 检查TopkDropoutStrategy是否正确处理涨跌停")
        print("   5. 验证交易成本是否被正确扣除")
        print("")


def main():
    diagnosis = ComprehensiveDiagnosis()
    diagnosis.run_all_checks()


if __name__ == '__main__':
    main()

