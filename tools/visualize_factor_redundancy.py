#!/usr/bin/env python3
"""
因子冗余度可视化工具

基于 AST 结构计算因子之间的相似度/距离，然后使用降维算法（MDS/t-SNE）
将因子映射到 2D 空间，生成散点图来展示因子的冗余程度。

越聚集的点表示因子之间冗余度越高。

使用方式：
    python tools/visualize_factor_redundancy.py factor_ast_output.json --output redundancy_plot.html
"""

import json
import sys
import os
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from quantaalpha.components.coder.factor_coder.factor_ast import (
    parse_expression, Node, VarNode, NumberNode, FunctionNode, 
    BinaryOpNode, ConditionalNode, UnaryOpNode,
    find_largest_common_subtree, count_nodes
)


def get_subtree_size(node: Node) -> int:
    """计算子树大小"""
    if isinstance(node, (NumberNode, VarNode)):
        return 1
    elif isinstance(node, FunctionNode):
        return 1 + sum(get_subtree_size(arg) for arg in node.args)
    elif isinstance(node, BinaryOpNode):
        return 1 + get_subtree_size(node.left) + get_subtree_size(node.right)
    elif isinstance(node, ConditionalNode):
        return 1 + get_subtree_size(node.condition) + \
               get_subtree_size(node.true_expr) + \
               get_subtree_size(node.false_expr)
    elif isinstance(node, UnaryOpNode):
        return 1 + get_subtree_size(node.operand)
    return 0


def calculate_similarity(expr1: str, expr2: str) -> float:
    """
    计算两个因子表达式的相似度
    
    相似度 = 最大公共子树大小 / min(树1大小, 树2大小)
    
    返回值在 [0, 1] 之间，1 表示完全相同
    """
    try:
        tree1 = parse_expression(expr1)
        tree2 = parse_expression(expr2)
        
        size1 = get_subtree_size(tree1)
        size2 = get_subtree_size(tree2)
        
        if size1 == 0 or size2 == 0:
            return 0.0
        
        match = find_largest_common_subtree(tree1, tree2)
        
        if match is None:
            return 0.0
        
        # 使用 Jaccard-like 相似度
        min_size = min(size1, size2)
        similarity = match.size / min_size
        
        return min(similarity, 1.0)  # 确保不超过1
        
    except Exception as e:
        return 0.0


def calculate_distance(similarity: float) -> float:
    """将相似度转换为距离"""
    return 1.0 - similarity


def build_distance_matrix(factors: List[Tuple[str, str, str]], 
                          verbose: bool = True) -> Tuple[np.ndarray, List[str], List[str]]:
    """
    构建因子之间的距离矩阵
    
    Args:
        factors: [(factor_id, factor_name, factor_expression), ...]
        verbose: 是否打印进度
        
    Returns:
        (距离矩阵, 因子ID列表, 因子名称列表)
    """
    n = len(factors)
    distance_matrix = np.zeros((n, n))
    factor_ids = [f[0] for f in factors]
    factor_names = [f[1] for f in factors]
    expressions = [f[2] for f in factors]
    
    total_pairs = n * (n - 1) // 2
    computed = 0
    
    if verbose:
        print(f"📊 计算 {n} 个因子之间的距离矩阵 ({total_pairs} 对)...")
    
    for i in range(n):
        for j in range(i + 1, n):
            similarity = calculate_similarity(expressions[i], expressions[j])
            distance = calculate_distance(similarity)
            distance_matrix[i, j] = distance
            distance_matrix[j, i] = distance
            
            computed += 1
            if verbose and computed % 500 == 0:
                print(f"  进度: {computed}/{total_pairs} ({100*computed/total_pairs:.1f}%)")
    
    if verbose:
        print(f"✅ 距离矩阵计算完成！")
    
    return distance_matrix, factor_ids, factor_names


def reduce_to_2d(distance_matrix: np.ndarray, method: str = 'mds') -> np.ndarray:
    """
    将距离矩阵降维到 2D
    
    Args:
        distance_matrix: 距离矩阵
        method: 'mds' 或 'tsne'
        
    Returns:
        2D 坐标数组 (n, 2)
    """
    print(f"🔄 使用 {method.upper()} 进行降维...")
    
    if method == 'mds':
        from sklearn.manifold import MDS
        mds = MDS(n_components=2, dissimilarity='precomputed', 
                  random_state=42, n_init=4, max_iter=300)
        coords = mds.fit_transform(distance_matrix)
    elif method == 'tsne':
        from sklearn.manifold import TSNE
        # t-SNE 需要先转换为相似度矩阵或使用 metric='precomputed'
        tsne = TSNE(n_components=2, metric='precomputed', 
                    random_state=42, perplexity=min(30, len(distance_matrix)-1))
        coords = tsne.fit_transform(distance_matrix)
    else:
        raise ValueError(f"Unknown method: {method}")
    
    print(f"✅ 降维完成！")
    return coords


def create_interactive_plot(coords: np.ndarray, 
                           factor_ids: List[str],
                           factor_names: List[str],
                           factor_expressions: List[str],
                           statistics: Optional[List[Dict]] = None,
                           cluster_labels: Optional[List[int]] = None,
                           output_path: str = 'redundancy_plot.html'):
    """
    创建交互式散点图 (使用 Plotly)
    """
    try:
        import plotly.graph_objects as go
        import plotly.express as px
    except ImportError:
        print("⚠️ 需要安装 plotly: pip install plotly")
        return None
    
    # 准备 hover 文本
    hover_texts = []
    for i, (fid, fname, expr) in enumerate(zip(factor_ids, factor_names, factor_expressions)):
        text = f"<b>{fname}</b><br>"
        text += f"ID: {fid[:16]}...<br>"
        text += f"表达式: {expr[:80]}..."
        if statistics and statistics[i]:
            stats = statistics[i]
            text += f"<br>节点数: {stats.get('total_nodes', 'N/A')}"
            text += f"<br>AST深度: {stats.get('tree_depth', 'N/A')}"
            text += f"<br>函数数: {stats.get('function_count', 'N/A')}"
            text += f"<br>变量数: {stats.get('variable_count', 'N/A')}"
        if cluster_labels is not None:
            text += f"<br>聚类: {cluster_labels[i]}"
        hover_texts.append(text)
    
    # 使用节点数作为点大小（如果有统计信息）
    if statistics:
        sizes = [s.get('total_nodes', 10) if s else 10 for s in statistics]
        # 归一化大小
        min_s, max_s = min(sizes), max(sizes)
        if max_s > min_s:
            sizes = [8 + 20 * (s - min_s) / (max_s - min_s) for s in sizes]
        else:
            sizes = [12] * len(sizes)
    else:
        sizes = [12] * len(coords)
    
    # 使用聚类标签或AST深度作为颜色
    if cluster_labels is not None:
        colors = cluster_labels
        colorscale = 'Rainbow'
        colorbar_title = '聚类编号'
    elif statistics:
        colors = [s.get('tree_depth', 5) if s else 5 for s in statistics]
        colorscale = 'Viridis'
        colorbar_title = 'AST 深度'
    else:
        colors = coords[:, 0]
        colorscale = 'Viridis'
        colorbar_title = '位置'
    
    # 创建散点图
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=coords[:, 0],
        y=coords[:, 1],
        mode='markers',
        marker=dict(
            size=sizes,
            color=colors,
            colorscale=colorscale,
            opacity=0.75,
            line=dict(width=1, color='white'),
            colorbar=dict(title=colorbar_title)
        ),
        text=hover_texts,
        hoverinfo='text',
        name='因子'
    ))
    
    fig.update_layout(
        title=dict(
            text='因子冗余度散点图<br><sup>距离越近 = AST结构越相似 = 冗余度越高 | 点大小 = 节点数 | 颜色 = 聚类</sup>',
            font=dict(size=18)
        ),
        xaxis_title='MDS 维度 1 (保持距离关系的投影坐标)',
        yaxis_title='MDS 维度 2 (保持距离关系的投影坐标)',
        template='plotly_dark',
        width=1200,
        height=800,
        hovermode='closest',
        annotations=[
            dict(
                text="💡 提示：维度1/2 是将高维距离矩阵降维到2D的投影坐标，<br>本身无具体物理含义，但保持了因子间的相对距离关系",
                xref="paper", yref="paper",
                x=0.01, y=-0.08,
                showarrow=False,
                font=dict(size=11, color='gray')
            )
        ]
    )
    
    # 保存为 HTML
    fig.write_html(output_path)
    print(f"📊 交互式图表已保存到: {output_path}")
    
    return fig


def create_matplotlib_plot(coords: np.ndarray,
                          factor_names: List[str],
                          statistics: Optional[List[Dict]] = None,
                          output_path: str = 'redundancy_plot.png',
                          show_labels: bool = False):
    """
    创建静态散点图 (使用 Matplotlib)
    """
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # 使用节点数作为点大小
    if statistics:
        sizes = [s.get('total_nodes', 30) * 3 if s else 30 for s in statistics]
    else:
        sizes = [50] * len(coords)
    
    # 使用深度作为颜色
    if statistics:
        colors = [s.get('tree_depth', 5) if s else 5 for s in statistics]
    else:
        colors = coords[:, 0]
    
    scatter = ax.scatter(coords[:, 0], coords[:, 1], 
                        c=colors, s=sizes, 
                        alpha=0.6, cmap='viridis',
                        edgecolors='white', linewidths=0.5)
    
    # 添加颜色条
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('AST 深度', fontsize=12)
    
    # 可选：添加标签
    if show_labels and len(factor_names) <= 50:
        for i, name in enumerate(factor_names):
            ax.annotate(name[:15], (coords[i, 0], coords[i, 1]),
                       fontsize=6, alpha=0.7)
    
    ax.set_xlabel('维度 1', fontsize=12)
    ax.set_ylabel('维度 2', fontsize=12)
    ax.set_title('因子冗余度散点图\n（距离越近表示冗余度越高，点大小=节点数，颜色=深度）', 
                 fontsize=14, fontweight='bold')
    
    # 添加网格
    ax.grid(True, alpha=0.3)
    ax.set_facecolor('#f8f9fa')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"📊 静态图表已保存到: {output_path}")
    
    return fig


def load_factor_ast_data(input_path: str) -> Tuple[List[Tuple[str, str, str]], List[Dict]]:
    """
    从 AST 提取结果文件加载因子数据
    
    Returns:
        (factors_list, statistics_list)
        factors_list: [(factor_id, factor_name, factor_expression), ...]
        statistics_list: [stats_dict, ...]
    """
    print(f"📖 加载因子 AST 数据: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    factors = []
    statistics = []
    
    # 检查是 AST-only 格式还是完整因子库格式
    if 'factor_asts' in data:
        # AST-only 格式
        factor_asts = data['factor_asts']
        for factor_id, factor_data in factor_asts.items():
            if not factor_data.get('parse_success', False):
                continue
            
            factors.append((
                factor_id,
                factor_data.get('factor_name', factor_id),
                factor_data.get('factor_expression', '')
            ))
            statistics.append(factor_data.get('statistics', {}))
    
    elif 'factors' in data:
        # 完整因子库格式（带或不带 AST）
        for factor_id, factor_data in data['factors'].items():
            expr = factor_data.get('factor_expression', '')
            if not expr:
                continue
            
            factors.append((
                factor_id,
                factor_data.get('factor_name', factor_id),
                expr
            ))
            
            # 如果有 AST 统计信息
            if 'factor_ast' in factor_data:
                statistics.append(factor_data['factor_ast'].get('statistics', {}))
            else:
                statistics.append({})
    
    print(f"✅ 加载了 {len(factors)} 个有效因子")
    return factors, statistics


def analyze_clusters(coords: np.ndarray, factor_names: List[str], 
                    n_clusters: int = 5) -> Dict[str, Any]:
    """
    对降维后的坐标进行聚类分析
    """
    from sklearn.cluster import KMeans
    
    print(f"🔍 进行 {n_clusters} 聚类分析...")
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)
    
    # 统计每个簇的信息
    clusters = {}
    for i in range(n_clusters):
        cluster_indices = np.where(labels == i)[0]
        cluster_factors = [factor_names[j] for j in cluster_indices]
        
        # 计算簇内平均距离（紧密度）
        cluster_coords = coords[cluster_indices]
        center = cluster_coords.mean(axis=0)
        avg_dist = np.mean(np.sqrt(np.sum((cluster_coords - center) ** 2, axis=1)))
        
        clusters[f"cluster_{i}"] = {
            "size": len(cluster_factors),
            "factors": cluster_factors[:10],  # 只显示前10个
            "compactness": float(avg_dist),
            "center": center.tolist()
        }
    
    print(f"✅ 聚类完成！")
    
    # 打印聚类摘要
    print("\n📊 聚类摘要:")
    for cluster_name, info in sorted(clusters.items(), key=lambda x: -x[1]['size']):
        print(f"  {cluster_name}: {info['size']} 个因子, 紧密度={info['compactness']:.3f}")
        print(f"    代表因子: {', '.join(info['factors'][:3])}...")
    
    return {"labels": labels.tolist(), "clusters": clusters}


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='因子冗余度可视化工具')
    parser.add_argument('input', help='因子 AST JSON 文件路径')
    parser.add_argument('--output', '-o', default='redundancy_plot.html',
                       help='输出图片路径 (默认: redundancy_plot.html)')
    parser.add_argument('--method', '-m', choices=['mds', 'tsne'], default='mds',
                       help='降维方法 (默认: mds)')
    parser.add_argument('--max-factors', type=int, default=200,
                       help='最大处理因子数 (默认: 200，过多会很慢)')
    parser.add_argument('--clusters', '-c', type=int, default=5,
                       help='聚类数 (默认: 5)')
    parser.add_argument('--static', action='store_true',
                       help='生成静态 PNG 图片而非交互式 HTML')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"❌ 文件不存在: {args.input}")
        sys.exit(1)
    
    # 加载数据
    factors, statistics = load_factor_ast_data(args.input)
    
    # 限制因子数量
    if len(factors) > args.max_factors:
        print(f"⚠️ 因子数量 ({len(factors)}) 超过限制，随机采样 {args.max_factors} 个")
        np.random.seed(42)
        indices = np.random.choice(len(factors), args.max_factors, replace=False)
        factors = [factors[i] for i in indices]
        statistics = [statistics[i] for i in indices]
    
    if len(factors) < 3:
        print("❌ 因子数量太少，至少需要 3 个")
        sys.exit(1)
    
    # 计算距离矩阵
    distance_matrix, factor_ids, factor_names = build_distance_matrix(factors)
    
    # 降维
    coords = reduce_to_2d(distance_matrix, method=args.method)
    
    # 聚类分析
    cluster_result = analyze_clusters(coords, factor_names, n_clusters=args.clusters)
    
    # 生成图表
    expressions = [f[2] for f in factors]
    
    if args.static:
        output_path = args.output.replace('.html', '.png')
        create_matplotlib_plot(coords, factor_names, statistics, output_path)
    else:
        create_interactive_plot(coords, factor_ids, factor_names, expressions, 
                               statistics, cluster_result['labels'], args.output)
    
    # 保存聚类结果
    cluster_output = args.output.replace('.html', '_clusters.json').replace('.png', '_clusters.json')
    with open(cluster_output, 'w', encoding='utf-8') as f:
        json.dump(cluster_result, f, indent=2, ensure_ascii=False)
    print(f"📊 聚类结果已保存到: {cluster_output}")
    
    print("\n✅ 完成！")


if __name__ == '__main__':
    main()

