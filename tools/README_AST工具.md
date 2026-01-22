# 因子AST提取工具使用说明

## 概述

`extract_factor_ast.py` 工具用于将因子表达式解析为AST（抽象语法树）结构，并保存到JSON文件中。这对于：
- 分析因子的结构复杂度
- 计算因子之间的冗余度/相似度
- 因子表达式的结构化比较

非常有用。

## 使用方式

### 方式1：命令行使用

```bash
# 激活虚拟环境
cd /home/tjxy/quantagent
source venv/bin/activate
cd AlphaAgent

# 1. 仅提取AST到单独文件（不修改原因子库）- 推荐
python tools/extract_factor_ast.py <因子库.json> --ast-only <输出文件.json>

# 示例：
python tools/extract_factor_ast.py all_factors_library_QA_round41_best_deepseek_aliyun_all_csi300.json --ast-only factor_ast_data.json

# 2. 原地更新因子库（在每个因子记录中添加 factor_ast 字段）
python tools/extract_factor_ast.py <因子库.json>

# 3. 输出到新文件（带AST的完整因子库）
python tools/extract_factor_ast.py <因子库.json> <输出文件.json>
```

### 方式2：Python代码中使用

```python
import sys
sys.path.insert(0, '/home/tjxy/quantagent/AlphaAgent')

# 方式A：直接导入工具模块
from tools import extract_ast_for_factor, serialize_ast, collect_functions

# 方式B：从模块导入
from tools.extract_factor_ast import (
    extract_ast_for_factor,
    process_factor_library,
    extract_ast_only,
    serialize_ast,
    deserialize_ast,
    collect_functions,
    collect_variables,
    compute_tree_depth,
)

# 也可以使用原始的AST解析模块
from alphaagent.components.coder.factor_coder.factor_ast import (
    parse_expression,
    Node, VarNode, NumberNode, FunctionNode, BinaryOpNode,
    find_largest_common_subtree,
    compare_expressions,
)

# ============================================================
# 示例1：提取单个因子的AST
# ============================================================
expr = "TS_CORR($close, $volume, 20) * STD($close, 10)"
result = extract_ast_for_factor(expr)

if result['parse_success']:
    print("AST树结构:")
    print(result['ast_tree_string'])
    
    print("\n统计信息:")
    stats = result['statistics']
    print(f"  总节点数: {stats['total_nodes']}")
    print(f"  树深度: {stats['tree_depth']}")
    print(f"  使用的函数: {stats['functions_used']}")
    print(f"  使用的变量: {stats['variables_used']}")
else:
    print(f"解析失败: {result['parse_error']}")

# ============================================================
# 示例2：批量处理因子库
# ============================================================
# 提取AST到单独文件
from tools.extract_factor_ast import extract_ast_only

stats = extract_ast_only(
    input_path="all_factors_library.json",
    output_path="factor_asts.json"
)
print(f"处理完成: 成功 {stats['success']}, 失败 {stats['failed']}")

# ============================================================
# 示例3：比较两个因子的相似度
# ============================================================
from alphaagent.components.coder.factor_coder.factor_ast import compare_expressions

expr1 = "TS_CORR($close, $volume, 20)"
expr2 = "TS_CORR($close, $volume, 30)"

match = compare_expressions(expr1, expr2)
if match:
    print(f"最大公共子树大小: {match.size}")
    print(f"公共子树: {match.root1}")
else:
    print("没有公共子树")
```

## 输出格式说明

### AST树结构 (ast_tree)

每个节点包含以下字段：
- `type`: 节点类型
  - `VAR`: 变量节点（如 `$close`, `$volume`）
  - `NUM`: 数字常量（如 `10`, `0.5`）
  - `FUNC`: 函数调用（如 `TS_CORR`, `STD`）
  - `BINOP`: 二元运算（如 `+`, `-`, `*`, `/`）
  - `UNARY`: 一元运算（如 `-x`）
  - `COND`: 条件表达式（`a ? b : c`）

示例：
```json
{
  "type": "FUNC",
  "name": "TS_CORR",
  "args": [
    {"type": "VAR", "name": "$close"},
    {"type": "VAR", "name": "$volume"},
    {"type": "NUM", "value": 20}
  ]
}
```

### 统计信息 (statistics)

| 字段 | 说明 |
|------|------|
| `total_nodes` | AST总节点数（复杂度指标） |
| `tree_depth` | 树的最大深度 |
| `num_free_args` | 数字常量的数量（参数数量） |
| `num_unique_vars` | 唯一变量数量 |
| `symbol_length` | 表达式字符串长度 |
| `num_base_features` | 基础特征数量（`$`开头的变量） |
| `functions_used` | 使用的函数列表 |
| `variables_used` | 使用的变量列表 |
| `function_count` | 函数调用总次数 |
| `variable_count` | 变量引用总次数 |

## 常见问题

### Q: 为什么有些因子解析失败？

A: 可能原因：
1. 表达式包含 `where` 子句（如 `IF(...) where x = ...`）- 解析器不支持
2. 表达式包含非标准语法
3. 括号不匹配

### Q: 如何处理解析失败的因子？

A: 解析失败的因子会被标记为 `parse_success: false`，并记录错误信息在 `parse_error` 字段中。您可以手动检查这些因子的表达式。

### Q: AST数据可以用来做什么？

A: 
1. **冗余度检测**: 使用 `find_largest_common_subtree()` 找到两个因子的最大公共子树
2. **复杂度分析**: 通过 `total_nodes` 和 `tree_depth` 评估因子复杂度
3. **特征工程**: 分析因子使用的函数和变量模式
4. **因子聚类**: 基于AST结构对因子进行聚类

---

# 因子冗余度可视化工具

## 概述

`visualize_factor_redundancy.py` 工具用于将因子之间的冗余关系可视化为散点图。

**核心原理**：
1. 基于 AST 结构计算每对因子之间的**相似度**（最大公共子树 / 最小树大小）
2. 将相似度转换为**距离**（距离 = 1 - 相似度）
3. 使用 **MDS（多维缩放）** 或 **t-SNE** 将高维距离矩阵降维到 2D
4. 在散点图中，**距离越近的点表示因子越相似（冗余度越高）**

## 使用方式

### 方式1：命令行使用

```bash
# 激活虚拟环境
cd /home/tjxy/quantagent
source venv/bin/activate
cd AlphaAgent

# 基本用法（生成交互式 HTML 图表）
python tools/visualize_factor_redundancy.py <AST文件.json> --output <输出.html>

# 示例：
python tools/visualize_factor_redundancy.py factor_ast_output_demo.json --output redundancy_plot.html

# 完整参数：
python tools/visualize_factor_redundancy.py factor_ast_output_demo.json \
    --output redundancy_plot.html \
    --method mds \        # 降维方法: mds 或 tsne
    --max-factors 100 \   # 最大处理因子数（过多会很慢）
    --clusters 6 \        # 聚类数量
    --static              # 生成静态 PNG 而非交互式 HTML
```

### 方式2：Python 代码中使用

```python
import sys
sys.path.insert(0, '/home/tjxy/quantagent/AlphaAgent')

from tools.visualize_factor_redundancy import (
    load_factor_ast_data,
    calculate_similarity,
    build_distance_matrix,
    reduce_to_2d,
    analyze_clusters,
    create_interactive_plot,
)

# ============================================================
# 示例1：计算两个因子的相似度
# ============================================================
expr1 = "TS_CORR($close, $volume, 20) * STD($close, 10)"
expr2 = "TS_CORR($close, $volume, 30) * STD($close, 20)"

similarity = calculate_similarity(expr1, expr2)
print(f"相似度: {similarity:.4f}")  # 0 = 完全不同, 1 = 完全相同
print(f"距离: {1 - similarity:.4f}")

# ============================================================
# 示例2：完整的可视化流程
# ============================================================
# 1. 加载数据
factors, statistics = load_factor_ast_data('factor_ast_output_demo.json')
print(f"加载了 {len(factors)} 个因子")

# 2. 计算距离矩阵
distance_matrix, factor_ids, factor_names = build_distance_matrix(factors)

# 3. 降维到 2D
coords = reduce_to_2d(distance_matrix, method='mds')  # 或 'tsne'

# 4. 聚类分析
cluster_result = analyze_clusters(coords, factor_names, n_clusters=5)

# 5. 生成图表
expressions = [f[2] for f in factors]
create_interactive_plot(
    coords, factor_ids, factor_names, expressions,
    statistics, cluster_result['labels'], 
    output_path='redundancy_plot.html'
)
```

## 图表解读

### 散点图坐标含义

| 元素 | 含义 |
|------|------|
| **位置（x, y）** | MDS/t-SNE 降维后的投影坐标，**本身无物理含义**，但保持了因子间的相对距离关系 |
| **点之间的距离** | 距离越近 = AST 结构越相似 = 冗余度越高 |
| **点的大小** | AST 节点数（复杂度） |
| **点的颜色** | 聚类编号 |

### 如何发现冗余因子

1. **聚集成簇的点**：这些因子之间高度冗余，可能需要去重
2. **孤立的点**：这些因子与其他因子差异较大，较为独特
3. **同色的簇**：聚类结果，同一聚类内的因子结构相似

### 输出文件

运行后会生成两个文件：
- `<output>.html`：交互式散点图（可 hover 查看因子详情）
- `<output>_clusters.json`：聚类结果

```json
{
  "labels": [0, 1, 2, ...],  // 每个因子的聚类标签
  "clusters": {
    "cluster_0": {
      "size": 12,
      "factors": ["Factor_A", "Factor_B", ...],
      "compactness": 0.234  // 越小表示聚类越紧密
    },
    ...
  }
}
```

## 性能说明

| 因子数量 | 距离计算次数 | 预计时间 |
|---------|-------------|---------|
| 50 | 1,225 | ~10秒 |
| 100 | 4,950 | ~30秒 |
| 150 | 11,175 | ~1分钟 |
| 200 | 19,900 | ~2分钟 |

**建议**：因子数量较多时，使用 `--max-factors` 参数限制处理数量。

## 完整工作流示例

```bash
cd /home/tjxy/quantagent/AlphaAgent

# 步骤1：从因子库提取 AST
python tools/extract_factor_ast.py \
    all_factors_library_QA_round41_best_deepseek_aliyun_all_csi300.json \ factor_ast_data.json

# 步骤2：生成冗余度可视化
python tools/visualize_factor_redundancy.py factor_ast_data.json \
    --output redundancy_analysis.html \
    --max-factors 100 \
    --clusters 8

# 步骤3：在浏览器中打开 redundancy_analysis.html 查看结果
```

## 依赖

```bash
pip install scikit-learn plotly matplotlib
```

---

## 相关模块

- `alphaagent/components/coder/factor_coder/factor_ast.py` - 核心AST解析模块
- `alphaagent/scenarios/qlib/regulator/factor_regulator.py` - 因子冗余度检测器
- `alphaagent/scenarios/qlib/regulator/consistency_checker.py` - 一致性和复杂度检查

