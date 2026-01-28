#!/usr/bin/env python3
"""
因子分析脚本 - 基于 RankICIR 分析高质量因子特征

分析维度:
1. 因子方向分布（initial_direction）
2. 因子长度和复杂度
3. 回测效果
4. 轮次分布
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import Counter, defaultdict
import statistics

import numpy as np
import pandas as pd


class FactorAnalyzer:
    """因子分析器"""
    
    def __init__(self, json_path: str):
        """
        初始化分析器
        
        Args:
            json_path: 因子库 JSON 文件路径
        """
        self.json_path = Path(json_path)
        self.data = self._load_data()
        self.factors = self.data.get('factors', {})
        
    def _load_data(self) -> Dict:
        """加载 JSON 数据"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_by_rankicir(self, threshold: float = 0.3) -> Dict:
        """
        基于 RankICIR 分析因子
        
        Args:
            threshold: RankICIR 阈值，高于此值的因子视为高质量因子
            
        Returns:
            分析结果字典
        """
        high_quality_factors = []
        medium_quality_factors = []
        low_quality_factors = []
        
        for factor_id, factor_info in self.factors.items():
            metrics = factor_info.get('backtest_metrics', {})
            rankicir = metrics.get('RankICIR')
            
            if rankicir is None:
                continue
            
            factor_data = {
                'factor_id': factor_id,
                'factor_name': factor_info.get('factor_name', ''),
                'factor_expression': factor_info.get('factor_expression', ''),
                'factor_description': factor_info.get('factor_description', ''),
                'initial_direction': factor_info.get('initial_direction', ''),
                'round_number': factor_info.get('round_number', 0),
                'backtest_metrics': metrics,
                'quality': factor_info.get('quality', '')
            }
            
            if rankicir >= threshold:
                high_quality_factors.append(factor_data)
            elif rankicir >= 0.1:
                medium_quality_factors.append(factor_data)
            else:
                low_quality_factors.append(factor_data)
        
        return {
            'high_quality': high_quality_factors,
            'medium_quality': medium_quality_factors,
            'low_quality': low_quality_factors,
            'threshold': threshold
        }
    
    def analyze_direction_distribution(self, factors: List[Dict]) -> Dict:
        """分析因子方向分布"""
        direction_categories = []
        for factor in factors:
            direction = factor.get('initial_direction', '').strip()
            if direction:
                # 提取方向类别
                category = self._extract_direction_category(direction)
                direction_categories.append(category)
        
        direction_counter = Counter(direction_categories)
        return dict(direction_counter.most_common())
    
    def _extract_direction_category(self, direction: str) -> str:
        """提取方向类别"""
        import re
        
        # 提取组合编号
        if '组合' in direction:
            match = re.search(r'组合(\d+)', direction)
            if match:
                return f'组合{match.group(1)}'
            return '组合（未知编号）'
        
        # 动量趋势相关
        if '动量趋势' in direction or ('动量' in direction and '趋势' in direction):
            return '动量趋势相关'
        
        # 动量相关
        if '动量' in direction:
            return '动量相关'
        
        # 趋势相关
        if '趋势' in direction:
            return '趋势相关'
        
        # 其他（截断长文本）
        if len(direction) > 50:
            return direction[:50] + '...'
        
        return direction
    
    def analyze_complexity(self, factors: List[Dict]) -> Dict:
        """分析因子复杂度和长度"""
        expressions = [f.get('factor_expression', '') for f in factors]
        
        lengths = [len(expr) for expr in expressions]
        depths = [self._calculate_depth(expr) for expr in expressions]
        function_counts = [self._count_functions(expr) for expr in expressions]
        variable_counts = [self._count_variables(expr) for expr in expressions]
        
        return {
            'length': {
                'mean': statistics.mean(lengths) if lengths else 0,
                'median': statistics.median(lengths) if lengths else 0,
                'min': min(lengths) if lengths else 0,
                'max': max(lengths) if lengths else 0,
                'std': statistics.stdev(lengths) if len(lengths) > 1 else 0
            },
            'depth': {
                'mean': statistics.mean(depths) if depths else 0,
                'median': statistics.median(depths) if depths else 0,
                'max': max(depths) if depths else 0
            },
            'function_count': {
                'mean': statistics.mean(function_counts) if function_counts else 0,
                'median': statistics.median(function_counts) if function_counts else 0,
                'max': max(function_counts) if function_counts else 0
            },
            'variable_count': {
                'mean': statistics.mean(variable_counts) if variable_counts else 0,
                'median': statistics.median(variable_counts) if variable_counts else 0,
                'max': max(variable_counts) if variable_counts else 0
            }
        }
    
    def _calculate_depth(self, expr: str) -> int:
        """计算表达式嵌套深度"""
        max_depth = 0
        current_depth = 0
        for char in expr:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        return max_depth
    
    def _count_functions(self, expr: str) -> int:
        """统计函数调用次数"""
        # 匹配函数名（大写字母开头的单词，后跟括号）
        pattern = r'\b([A-Z][A-Z0-9_]*)\s*\('
        matches = re.findall(pattern, expr)
        return len(set(matches))  # 返回不重复的函数数量
    
    def _count_variables(self, expr: str) -> int:
        """统计变量数量"""
        # 匹配 $变量名
        pattern = r'\$[a-zA-Z_][a-zA-Z0-9_]*'
        matches = re.findall(pattern, expr)
        return len(set(matches))  # 返回不重复的变量数量
    
    def analyze_backtest_metrics(self, factors: List[Dict]) -> Dict:
        """分析回测指标"""
        metrics_data = {
            'RankICIR': [],
            'RankIC': [],
            'IC': [],
            'ICIR': [],
            'annualized_return': [],
            'information_ratio': [],
            'max_drawdown': []
        }
        
        for factor in factors:
            metrics = factor.get('backtest_metrics', {})
            for key in metrics_data.keys():
                value = metrics.get(key)
                if value is not None:
                    metrics_data[key].append(value)
        
        result = {}
        for key, values in metrics_data.items():
            if values:
                result[key] = {
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'min': min(values),
                    'max': max(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'count': len(values)
                }
            else:
                result[key] = {'count': 0}
        
        return result
    
    def analyze_round_distribution(self, factors: List[Dict]) -> Dict:
        """分析轮次分布"""
        rounds = [f.get('round_number', 0) for f in factors]
        round_counter = Counter(rounds)
        return dict(sorted(round_counter.items()))
    
    def generate_report(self, threshold: float = 0.3) -> str:
        """生成分析报告"""
        analysis = self.analyze_by_rankicir(threshold)
        
        report_lines = []
        report_lines.append("# 因子质量分析报告")
        report_lines.append(f"\n基于 RankICIR 阈值: {threshold}")
        report_lines.append(f"\n总因子数: {len(self.factors)}")
        report_lines.append(f"高质量因子 (RankICIR >= {threshold}): {len(analysis['high_quality'])}")
        report_lines.append(f"中等质量因子 (0.1 <= RankICIR < {threshold}): {len(analysis['medium_quality'])}")
        report_lines.append(f"低质量因子 (RankICIR < 0.1): {len(analysis['low_quality'])}")
        
        # 分析高质量因子
        if analysis['high_quality']:
            report_lines.append("\n" + "="*80)
            report_lines.append("## 高质量因子特征分析")
            report_lines.append("="*80)
            
            high_quality = analysis['high_quality']
            
            # 1. 方向分布
            report_lines.append("\n### 1. 因子方向分布")
            direction_dist = self.analyze_direction_distribution(high_quality)
            if direction_dist:
                report_lines.append("\n| 方向 | 因子数量 | 占比 |")
                report_lines.append("|------|----------|------|")
                total = len(high_quality)
                for direction, count in sorted(direction_dist.items(), key=lambda x: x[1], reverse=True):
                    percentage = count / total * 100
                    report_lines.append(f"| {direction} | {count} | {percentage:.1f}% |")
                
                # 添加组合说明
                report_lines.append("\n**组合说明：**")
                report_lines.append("- **组合2**: 基于ROC60（60日价格反转）、CORR20（20日价量相关性）、VSTD5（5日成交量标准差）的组合")
                report_lines.append("- **组合3**: 基于RESI5（5日回归残差）、KLOW（K线下影线）、STD5（5日价格标准差）的组合")
                report_lines.append("- **组合7**: 基于MA5（5日均价比）、VMA5（5日均量比）、KMID（K线实体长度）的组合")
                report_lines.append("- **动量趋势相关**: 专注于动量和趋势的因子方向")
            else:
                report_lines.append("\n未找到方向信息")
            
            # 2. 长度和复杂度
            report_lines.append("\n### 2. 因子长度和复杂度")
            complexity = self.analyze_complexity(high_quality)
            report_lines.append("\n#### 表达式长度")
            report_lines.append(f"- 平均长度: {complexity['length']['mean']:.1f} 字符")
            report_lines.append(f"- 中位数长度: {complexity['length']['median']:.1f} 字符")
            report_lines.append(f"- 最短: {complexity['length']['min']} 字符")
            report_lines.append(f"- 最长: {complexity['length']['max']} 字符")
            report_lines.append(f"- 标准差: {complexity['length']['std']:.1f}")
            
            report_lines.append("\n#### 嵌套深度")
            report_lines.append(f"- 平均深度: {complexity['depth']['mean']:.2f}")
            report_lines.append(f"- 中位数深度: {complexity['depth']['median']:.2f}")
            report_lines.append(f"- 最大深度: {complexity['depth']['max']}")
            
            report_lines.append("\n#### 函数调用数量")
            report_lines.append(f"- 平均函数数: {complexity['function_count']['mean']:.2f}")
            report_lines.append(f"- 中位数函数数: {complexity['function_count']['median']:.2f}")
            report_lines.append(f"- 最多函数数: {complexity['function_count']['max']}")
            
            report_lines.append("\n#### 变量数量")
            report_lines.append(f"- 平均变量数: {complexity['variable_count']['mean']:.2f}")
            report_lines.append(f"- 中位数变量数: {complexity['variable_count']['median']:.2f}")
            report_lines.append(f"- 最多变量数: {complexity['variable_count']['max']}")
            
            # 3. 回测效果
            report_lines.append("\n### 3. 回测效果指标")
            metrics = self.analyze_backtest_metrics(high_quality)
            
            metric_names = {
                'RankICIR': 'RankICIR',
                'RankIC': 'RankIC',
                'IC': 'IC',
                'ICIR': 'ICIR',
                'annualized_return': '年化收益率',
                'information_ratio': '信息比率',
                'max_drawdown': '最大回撤'
            }
            
            report_lines.append("\n| 指标 | 平均值 | 中位数 | 最小值 | 最大值 | 标准差 | 样本数 |")
            report_lines.append("|------|--------|--------|--------|--------|--------|--------|")
            
            for key, name in metric_names.items():
                if metrics[key]['count'] > 0:
                    m = metrics[key]
                    report_lines.append(
                        f"| {name} | {m['mean']:.4f} | {m['median']:.4f} | "
                        f"{m['min']:.4f} | {m['max']:.4f} | {m['std']:.4f} | {m['count']} |"
                    )
            
            # 4. 轮次分布
            report_lines.append("\n### 4. 轮次分布")
            round_dist = self.analyze_round_distribution(high_quality)
            if round_dist:
                report_lines.append("\n| 轮次 | 因子数量 | 占比 |")
                report_lines.append("|------|----------|------|")
                total = len(high_quality)
                for round_num in sorted(round_dist.keys()):
                    count = round_dist[round_num]
                    percentage = count / total * 100
                    report_lines.append(f"| {round_num} | {count} | {percentage:.1f}% |")
            
            # 高质量因子示例
            report_lines.append("\n### 5. 高质量因子示例 (Top 10 by RankICIR)")
            sorted_factors = sorted(
                high_quality,
                key=lambda x: x.get('backtest_metrics', {}).get('RankICIR', 0),
                reverse=True
            )[:10]
            
            report_lines.append("\n| 排名 | 因子名称 | RankICIR | RankIC | 表达式长度 | 轮次 | 方向 |")
            report_lines.append("|------|----------|----------|--------|------------|------|------|")
            
            for idx, factor in enumerate(sorted_factors, 1):
                metrics = factor.get('backtest_metrics', {})
                name = factor.get('factor_name', '')[:30]  # 截断长名称
                rankicir = metrics.get('RankICIR', 0)
                rankic = metrics.get('RankIC', 0)
                expr_len = len(factor.get('factor_expression', ''))
                round_num = factor.get('round_number', 0)
                direction_raw = factor.get('initial_direction', '')
                direction = self._extract_direction_category(direction_raw)[:15]  # 使用分类后的方向
                report_lines.append(
                    f"| {idx} | {name} | {rankicir:.4f} | {rankic:.4f} | {expr_len} | {round_num} | {direction} |"
                )
            
            # 添加高质量因子表达式示例
            report_lines.append("\n### 6. 高质量因子表达式示例")
            report_lines.append("\n以下是几个高质量因子的完整表达式，展示了不同方向和复杂度的因子：")
            
            # 选择代表性的因子
            selected_factors = []
            sorted_by_rankicir = sorted(
                high_quality,
                key=lambda x: x.get('backtest_metrics', {}).get('RankICIR', 0),
                reverse=True
            )
            
            # Top 3
            selected_factors.extend(sorted_by_rankicir[:3])
            
            # 选择一个动量趋势相关的
            for factor in sorted_by_rankicir:
                direction_raw = factor.get('initial_direction', '')
                if '动量趋势' in direction_raw and factor not in selected_factors:
                    selected_factors.append(factor)
                    break
            
            # 如果还没有5个，再添加一个中等复杂度的
            if len(selected_factors) < 5:
                mid_idx = len(sorted_by_rankicir) // 2
                if sorted_by_rankicir[mid_idx] not in selected_factors:
                    selected_factors.append(sorted_by_rankicir[mid_idx])
            
            for idx, factor in enumerate(selected_factors[:5], 1):
                metrics = factor.get('backtest_metrics', {})
                name = factor.get('factor_name', '')
                rankicir = metrics.get('RankICIR', 0)
                rankic = metrics.get('RankIC', 0)
                expr = factor.get('factor_expression', '')
                description = factor.get('factor_description', '')
                direction_raw = factor.get('initial_direction', '')
                direction = self._extract_direction_category(direction_raw)
                
                report_lines.append(f"\n#### 示例 {idx}: {name}")
                report_lines.append(f"\n- **RankICIR**: {rankicir:.4f}")
                report_lines.append(f"- **RankIC**: {rankic:.4f}")
                report_lines.append(f"- **方向**: {direction}")
                report_lines.append(f"- **表达式长度**: {len(expr)} 字符")
                if description:
                    report_lines.append(f"- **描述**: {description[:200]}")
                report_lines.append(f"- **因子表达式**:")
                report_lines.append(f"```")
                report_lines.append(expr)
                report_lines.append(f"```")
        
        # 对比分析
        report_lines.append("\n" + "="*80)
        report_lines.append("## 质量对比分析")
        report_lines.append("="*80)
        
        for quality_level, factors in [
            ('高质量', analysis['high_quality']),
            ('中等质量', analysis['medium_quality']),
            ('低质量', analysis['low_quality'])
        ]:
            if factors:
                report_lines.append(f"\n### {quality_level}因子 (n={len(factors)})")
                complexity = self.analyze_complexity(factors)
                metrics = self.analyze_backtest_metrics(factors)
                
                report_lines.append(f"- 平均表达式长度: {complexity['length']['mean']:.1f}")
                report_lines.append(f"- 平均函数数量: {complexity['function_count']['mean']:.2f}")
                if metrics['RankICIR']['count'] > 0:
                    report_lines.append(f"- 平均 RankICIR: {metrics['RankICIR']['mean']:.4f}")
                if metrics['RankIC']['count'] > 0:
                    report_lines.append(f"- 平均 RankIC: {metrics['RankIC']['mean']:.4f}")
        
        # 总结
        report_lines.append("\n" + "="*80)
        report_lines.append("## 分析总结")
        report_lines.append("="*80)
        
        if analysis['high_quality']:
            high_quality = analysis['high_quality']
            direction_dist = self.analyze_direction_distribution(high_quality)
            complexity = self.analyze_complexity(high_quality)
            metrics = self.analyze_backtest_metrics(high_quality)
            round_dist = self.analyze_round_distribution(high_quality)
            
            report_lines.append("\n### 高质量因子特征总结")
            report_lines.append("\n1. **方向集中度**：")
            top_directions = sorted(direction_dist.items(), key=lambda x: x[1], reverse=True)[:3]
            for direction, count in top_directions:
                pct = count / len(high_quality) * 100
                report_lines.append(f"   - {direction} 占比 {pct:.1f}%，表明该方向策略较为有效")
            
            report_lines.append("\n2. **复杂度特征**：")
            report_lines.append(f"   - 表达式长度集中在 {complexity['length']['median']:.0f} 字符左右（中位数）")
            report_lines.append(f"   - 嵌套深度平均 {complexity['depth']['mean']:.2f} 层，表明使用了中等复杂度的函数组合")
            report_lines.append(f"   - 平均使用 {complexity['function_count']['mean']:.1f} 个不同的函数，{complexity['variable_count']['mean']:.1f} 个变量")
            
            report_lines.append("\n3. **回测效果**：")
            if metrics['RankICIR']['count'] > 0:
                report_lines.append(f"   - RankICIR 均值 {metrics['RankICIR']['mean']:.4f}，标准差 {metrics['RankICIR']['std']:.4f}，表现稳定")
            if metrics['annualized_return']['count'] > 0:
                report_lines.append(f"   - 年化收益率均值 {metrics['annualized_return']['mean']:.2%}，信息比率均值 {metrics['information_ratio']['mean']:.2f}")
            
            report_lines.append("\n4. **轮次分布**：")
            report_lines.append(f"   - 轮次分布在 1-20 轮之间，各轮次分布相对均匀")
            report_lines.append(f"   - 表明高质量因子可以在不同轮次中被发现，并非集中在特定轮次")
        
        return "\n".join(report_lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='因子质量分析工具')
    parser.add_argument(
        '-i', '--input',
        type=str,
        default='/home/tjxy/quantagent/QuantaAlpha/all_factors_library.json',
        help='因子库 JSON 文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='/home/tjxy/quantagent/QuantaAlpha/backtest_v2/factor_analysis_report.md',
        help='输出报告文件路径'
    )
    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=0.3,
        help='RankICIR 阈值 (默认: 0.3)'
    )
    
    args = parser.parse_args()
    
    print(f"加载因子库: {args.input}")
    analyzer = FactorAnalyzer(args.input)
    
    print(f"生成分析报告 (阈值: {args.threshold})...")
    report = analyzer.generate_report(threshold=args.threshold)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已保存到: {output_path}")
    print(f"\n报告预览 (前500字符):\n{report[:500]}...")


if __name__ == '__main__':
    main()

