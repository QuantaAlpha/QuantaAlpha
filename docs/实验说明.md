# Quanta Alpha 量化因子挖掘实验说明

## 目录
- [1. 项目概述](#1-项目概述)
- [2. 实验思路与方法论](#2-实验思路与方法论)
- [3. 主实验流程详解](#3-主实验流程详解)
- [4. 独立回测框架](#4-独立回测框架)
- [5. 评价指标详解](#5-评价指标详解)
- [6. 实验配置与超参数](#6-实验配置与超参数)
- [7. 数据与回测设置](#7-数据与回测设置)
- [8. 实验结论与分析](#8-实验结论与分析)

---

## 1. 项目概述

### 1.1 项目目标

**Quanta Alpha** 是一个基于大语言模型（LLM）驱动的量化因子自动挖掘系统。其核心目标是：

- **自动化因子发现**：利用 LLM 生成市场假设，并将假设转化为可计算的因子表达式
- **进化式优化**：通过变异（Mutation）和交叉（Crossover）操作，迭代优化因子质量
- **端到端回测验证**：基于 Qlib 框架进行因子回测，评估因子的预测能力和投资价值

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   Quanta Alpha 系统架构                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   用户输入（探索方向）                                              │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────┐                                               │
│   │   Planning   │ ──→ 生成 N 个并行探索方向                        │
│   └──────────────┘                                               │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │              Evolution Controller                         │  │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│   │  │ Original │→│ Mutation │→│ Crossover│→ 循环...        │  │
│   │  │   原始轮  │  │   变异轮  │  │   交叉轮  │               │  │
│   │  └──────────┘  └──────────┘  └──────────┘               │  │
│   └──────────────────────────────────────────────────────────┘  │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │           QuantAgentLoop（5 步循环）                       │  │
│   │  1. factor_propose    → LLM 生成市场假设                   │  │
│   │  2. factor_construct  → LLM 生成因子表达式                  │  │
│   │  3. factor_calculate  → 解析并计算因子值                    │  │
│   │  4. factor_backtest   → Qlib 回测                         │  │
│   │  5. feedback          → LLM 分析反馈 + 因子入库             │  │
│   └──────────────────────────────────────────────────────────┘  │
│         │                                                        │
│         ▼                                                        │
│   ┌──────────────┐                                               │
│   │  因子库 JSON  │ ──→ 所有有效因子的归档                         │
│   └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 核心文件结构

| 文件/脚本 | 功能说明 |
|-----------|----------|
| `运行实验.sh` | 主实验入口脚本，激活环境并调用 `alphaagent mine` |
| `backtest_v2/run_backtest.py` | 独立回测工具，对因子库进行批量回测 |
| `run_config.yaml` | 主实验配置文件（规划、进化、回测参数） |
| `backtest_v2/config.yaml` | 独立回测配置文件 |
| `all_factors_library_*.json` | 因子库输出文件 |

---

## 2. 实验思路与方法论

### 2.1 核心方法：LLM 驱动的进化式因子挖掘

传统因子挖掘依赖人工经验和领域知识，效率低且难以规模化。Quanta Alpha 采用创新的方法：

#### 2.1.1 假设驱动

```
用户输入（如"动量策略"）
        │
        ▼
   ┌─────────────────────────────────────────┐
   │  LLM 生成市场假设                         │
   │  例如：                                   │
   │  "过去N天收益率的动量效应在A股市场显著，    │
   │   短期动量可能反转而中期动量持续有效"       │
   └─────────────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────────────┐
   │  LLM 将假设转化为因子表达式               │
   │  例如：                                   │
   │  ($close - Ref($close, 5)) / Ref($close, 5)  │
   │  Rank(Mean($close/Ref($close,1)-1, 20))      │
   └─────────────────────────────────────────┘
```

#### 2.1.2 进化式优化

借鉴遗传算法思想，通过 **变异** 和 **交叉** 操作优化因子：

```
             ┌─────────────────────────────────────────────┐
             │            进化流程                          │
             ├─────────────────────────────────────────────┤
             │                                             │
  Round 0    │   原始轮：N 个方向并行探索                     │
  (Original) │   → 生成 N 条初始轨迹                        │
             │                                             │
             │              │                              │
             │              ▼                              │
             │                                             │
  Round 1    │   变异轮：对原始轨迹进行"变异"                 │
  (Mutation) │   → 基于原始轨迹生成正交策略                  │
             │   → 避免重复探索相同路径                      │
             │                                             │
             │              │                              │
             │              ▼                              │
             │                                             │
  Round 2    │   交叉轮：选择 K 个父代组合                   │
  (Crossover)│   → 融合不同轨迹的优点                       │
             │   → 生成新的混合策略                         │
             │                                             │
             │              │                              │
             │              ▼                              │
             │                                             │
  Round 3+   │   继续 变异 → 交叉 → 变异 → ...              │
             │   直到达到最大轮数                           │
             │                                             │
             └─────────────────────────────────────────────┘
```

### 2.2 方法论优势

| 优势 | 说明 |
|------|------|
| **可解释性** | LLM 生成的因子带有假设说明，便于理解因子逻辑 |
| **多样性** | 进化机制确保因子多样化，避免局部最优 |
| **自动化** | 全流程自动化，减少人工干预 |
| **迭代优化** | 反馈机制让系统从失败中学习，持续改进 |

---

## 3. 主实验流程详解

### 3.1 启动命令

```bash
# 基本用法
./运行实验.sh "你的探索方向描述"

# 示例
./运行实验.sh "基于量价关系的短期反转因子"
./运行实验.sh "利用波动率和成交量构建市场情绪因子"
```

### 3.2 五步循环详解

每一轮探索包含 5 个核心步骤：

#### Step 1: factor_propose（假设生成）
- **输入**：探索方向 + 历史轨迹（trace）
- **过程**：调用 LLM 生成市场假设
- **输出**：结构化的假设描述（hypothesis）
- **核心模块**：`QuantAgentHypothesisGen`

```python
# 伪代码示例
hypothesis = llm.generate(
    prompt="""
    根据以下探索方向，生成一个可验证的市场假设：
    方向：{direction}
    历史经验：{trace.history}
    
    请描述：
    1. 假设的核心逻辑
    2. 预期的市场现象
    3. 可能的验证方法
    """
)
```

#### Step 2: factor_construct（因子构建）
- **输入**：市场假设
- **过程**：LLM 将假设转化为 2-3 个因子表达式
- **输出**：因子表达式列表
- **核心模块**：`QuantAgentHypothesis2FactorExpression`

```
# 因子表达式语法示例
$close                          # 收盘价
Ref($close, 5)                  # 5天前的收盘价
Mean($volume, 20)               # 20日均量
Rank($close / Ref($close, 1) - 1)  # 日收益率排名
Std($close / Ref($close, 1) - 1, 20)  # 20日收益率标准差
```

#### Step 3: factor_calculate（因子计算）
- **输入**：因子表达式
- **过程**：解析表达式并计算因子值
- **输出**：因子值矩阵（时间 × 股票）
- **核心模块**：`QlibFactorParser`

##### 3.1 计算流程概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     因子计算流程                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   因子表达式输入                                                          │
│   例: "RANK(DELTA($close, 5) / TS_STD($close, 20))"                     │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  1. 表达式预处理 (expr_parser.py)                                  │  │
│   │     - 括号平衡检查                                                  │  │
│   │     - 无效运算符检查                                                │  │
│   │     - 一元负号预处理 (如 "* -$close" → "* (-1 * $close)")          │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  2. 表达式解析 (pyparsing 库)                                      │  │
│   │     - 构建 AST (抽象语法树)                                         │  │
│   │     - 运算符优先级: * / → + - → > < >= <= == != → && → ||          │  │
│   │     - 将中缀表达式转换为函数调用形式                                  │  │
│   │       例: "$close + $open" → "ADD($close, $open)"                  │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  3. 因子验证 (factor_regulator.py)                                 │  │
│   │     - 可解析性检查                                                  │  │
│   │     - 重复子树检测 (与已有因子库对比)                                 │  │
│   │     - 复杂度约束:                                                   │  │
│   │       · 符号长度 (SL) ≤ 300                                        │  │
│   │       · 基础特征数 (ER) ≤ 6                                         │  │
│   │       · 自由参数比例 < 50%                                          │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  4. 加载市场数据 (Qlib)                                            │  │
│   │     - 数据源: daily_pv.h5 (日线数据)                                │  │
│   │     - 包含: $open, $high, $low, $close, $volume                    │  │
│   │     - 索引: MultiIndex (instrument, datetime)                      │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  5. 递归计算因子值 (function_lib.py)                               │  │
│   │     - 变量替换: "$close" → "df['$close']"                          │  │
│   │     - 使用 eval() 执行解析后的表达式                                 │  │
│   │     - 所有函数自动处理 groupby('instrument') 分组                   │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  6. 结果输出与缓存                                                  │  │
│   │     - 输出: result.h5 (HDF5 格式)                                  │  │
│   │     - 索引: MultiIndex (instrument, datetime)                      │  │
│   │     - 数据类型: float64                                            │  │
│   └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

##### 3.2 表达式解析器实现

表达式解析器基于 **pyparsing** 库实现，支持完整的算术、比较、逻辑和条件表达式：

```python
# 核心解析逻辑 (expr_parser.py)

# 1. 定义基本元素
var = Combine(Optional("$") + Word(alphas, alphanums + "_"))  # 变量: $close, volume
number = Regex(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")   # 数字: 1.5, -3, 1e-8

# 2. 定义运算符优先级（从低到高）
expr = infixNotation(operand, [
    (mul_div,      2, LEFT,  parse_arith_op),      # * /
    (add_minus,    2, LEFT,  parse_arith_op),      # + -
    (comparison,   2, LEFT,  parse_comparison_op),  # > < >= <= == !=
    (logical_and,  2, LEFT,  parse_logical),        # && &
    (logical_or,   2, LEFT,  parse_logical),        # || |
    (conditional,  3, RIGHT, parse_conditional)     # ? :
])

# 3. 运算符转换为函数调用
# 例如: "$close + $open"  →  "ADD($close, $open)"
#       "$close > $open"  →  "GT($close, $open)"
#       "A ? B : C"       →  "WHERE(A, B, C)"
```

##### 3.3 支持的因子函数库

系统内置了丰富的因子计算函数（`function_lib.py`），分为以下几类：

**时间序列函数（TS_*）**- 按股票分组，沿时间轴计算

| 函数 | 说明 | 示例 |
|------|------|------|
| `DELTA(df, p)` | p 期差分 | `DELTA($close, 5)` 5日收盘价变化 |
| `DELAY(df, p)` | 延迟 p 期 | `DELAY($close, 1)` 昨日收盘价 |
| `TS_MEAN(df, p)` | p 期滚动均值 | `TS_MEAN($volume, 20)` 20日均量 |
| `TS_STD(df, p)` | p 期滚动标准差 | `TS_STD($close, 20)` 20日波动率 |
| `TS_MAX(df, p)` | p 期滚动最大值 | `TS_MAX($high, 10)` 10日最高价 |
| `TS_MIN(df, p)` | p 期滚动最小值 | `TS_MIN($low, 10)` 10日最低价 |
| `TS_RANK(df, p)` | p 期滚动排名 | `TS_RANK($close, 20)` 20日排名 |
| `TS_CORR(df1, df2, p)` | p 期滚动相关系数 | `TS_CORR($close, $volume, 20)` |
| `TS_SUM(df, p)` | p 期滚动累加 | `TS_SUM($volume, 5)` 5日成交量 |
| `TS_ARGMAX(df, p)` | 最大值位置 | `TS_ARGMAX($close, 20)` 最高点距今天数 |
| `TS_ARGMIN(df, p)` | 最小值位置 | `TS_ARGMIN($close, 20)` 最低点距今天数 |
| `TS_PCTCHANGE(df, p)` | p 期收益率 | `TS_PCTCHANGE($close, 5)` 5日收益率 |

**横截面函数（CS_*）**- 按日期分组，跨股票计算

| 函数 | 说明 | 示例 |
|------|------|------|
| `RANK(df)` | 横截面排名（百分比） | `RANK($close)` 收盘价排名 |
| `ZSCORE(df)` | 横截面标准化 | `ZSCORE($volume)` 成交量Z-Score |
| `MEAN(df)` | 横截面均值 | `MEAN($close)` 全市场平均价 |
| `STD(df)` | 横截面标准差 | `STD($close)` 全市场价格离散度 |
| `SCALE(df)` | 横截面缩放 | `SCALE($close)` 归一化 |

**数学函数**

| 函数 | 说明 | 示例 |
|------|------|------|
| `ABS(df)` | 绝对值 | `ABS(DELTA($close, 1))` |
| `LOG(df)` | 自然对数 | `LOG($volume)` |
| `SQRT(df)` | 平方根 | `SQRT($volume)` |
| `SIGN(df)` | 符号函数 | `SIGN(DELTA($close, 1))` |
| `POW(df, n)` | 幂运算 | `POW($close, 2)` |
| `EXP(df)` | 指数函数 | `EXP($close / 100)` |

**技术指标函数**

| 函数 | 说明 | 示例 |
|------|------|------|
| `SMA(df, m)` | 简单移动平均 | `SMA($close, 20)` |
| `EMA(df, p)` | 指数移动平均 | `EMA($close, 12)` |
| `WMA(df, p)` | 加权移动平均 | `WMA($close, 10)` |
| `MACD(price, s, l)` | MACD 指标 | `MACD($close, 12, 26)` |
| `RSI(price, p)` | 相对强弱指数 | `RSI($close, 14)` |
| `BB_UPPER/MIDDLE/LOWER` | 布林带 | `BB_UPPER($close, 20)` |
| `DECAYLINEAR(df, p)` | 线性衰减加权 | `DECAYLINEAR($close, 10)` |

**回归函数**

| 函数 | 说明 | 示例 |
|------|------|------|
| `REGBETA(y, x, p)` | 滚动回归系数 | `REGBETA($close, $volume, 20)` |
| `REGRESI(y, x, p)` | 滚动回归残差 | `REGRESI($close, MEAN($close), 20)` |

**逻辑与条件函数**

| 函数 | 说明 | 示例 |
|------|------|------|
| `GT(a, b)` | 大于 | `GT($close, $open)` |
| `LT(a, b)` | 小于 | `LT($close, DELAY($close, 1))` |
| `AND(a, b)` | 逻辑与 | `AND(GT($close, $open), GT($volume, 1e8))` |
| `OR(a, b)` | 逻辑或 | `OR(GT($close, $open), LT($low, $open))` |
| `WHERE(cond, t, f)` | 条件选择 | `WHERE(GT($close, $open), $high, $low)` |

##### 3.4 因子复杂度正则化

为防止因子过于复杂或与已有因子重复，系统实现了复杂度正则化（`FactorRegulator`）：

```
复杂度惩罚: R_g(f, h) = α₁·SL(f) + α₂·PC(f) + α₃·ER(f, h)

其中:
- SL(f): 符号长度 (Symbol Length) - 表达式字符数
- PC(f): 参数复杂度 (Parameter Complexity) - 自由参数比例
- ER(f, h): 特征冗余 (Expression Redundancy) - 基础特征数量
```

**验证规则**：

| 指标 | 阈值 | 说明 |
|------|------|------|
| 符号长度 (SL) | ≤ 300 | 表达式不能太长 |
| 基础特征数 (ER) | ≤ 6 | 最多使用 6 种原始特征 |
| 自由参数比例 | < 50% | 数值常量不能占比过高 |
| 重复子树大小 | ≤ 8 | 与已有因子的重复部分不能太大 |

##### 3.5 计算执行与缓存

因子计算的最终执行使用 Python 的 `eval()` 函数：

```python
# 计算模板 (template.jinja2)
def calculate_factor(expr: str, name: str):
    # 1. 加载数据
    df = pd.read_hdf('./daily_pv.h5', key='data')
    
    # 2. 符号替换
    expr = parse_symbol(expr, df.columns)   # TRUE → True, $close → close
    expr = parse_expression(expr)            # 解析为函数调用形式
    
    # 3. 变量替换
    for col in df.columns:
        expr = expr.replace(col[1:], f"df['{col}']")  # close → df['$close']
    
    # 4. 执行计算
    df[name] = eval(expr)  # 执行解析后的表达式
    result = df[name].astype(np.float64)
    
    # 5. 保存结果
    result.to_hdf('result.h5', key='data')
```

**缓存机制**：
- 计算结果保存为 HDF5 格式（`result.h5`）
- 工作空间路径：`/mnt/DATA/quantagent/QuantaAlpha/QuantaAlpha_workspace/{UUID}/`
- 独立回测框架可通过缓存提取工具复用这些计算结果

#### Step 4: factor_backtest（因子回测）
- **输入**：计算好的因子值
- **过程**：基于 Qlib 进行机器学习回测
- **输出**：回测指标（IC、ICIR、收益率等）
- **核心模块**：`QlibFactorRunner`

```yaml
# 主程序回测配置 (conf.yaml)
训练集: 2016-01-01 ~ 2020-12-31  # 5年
验证集: 2021-01-01 ~ 2021-12-31  # 1年
测试集: 2022-01-01 ~ 2025-12-26  # 约4年

模型: LightGBM
策略: TopkDropoutStrategy (Top50, Drop5)
```

#### Step 5: feedback（反馈与入库）
- **输入**：回测结果 + 假设
- **过程**：LLM 分析结果，生成反馈
- **输出**：反馈报告 + 因子写入库
- **核心模块**：`QuantAgentQlibFactorHypothesisExperiment2Feedback`

```python
# 因子入库结构
factor_entry = {
    "factor_name": "momentum_5d",
    "factor_expression": "($close - Ref($close, 5)) / Ref($close, 5)",
    "hypothesis": "短期动量效应...",
    "direction": "动量策略",
    "evolution_phase": "original" | "mutation" | "crossover",
    "metrics": {
        "RankIC": 0.05,
        "RankICIR": 0.8,
        "annualized_return": 0.15,
        ...
    }
}
```

### 3.3 进化控制器

进化控制器（`EvolutionController`）管理整个进化流程：

```
┌─────────────────────────────────────────────────────────────┐
│                  Evolution Controller                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  TrajectoryPool（轨迹池）                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Trajectory 1: direction=0, phase=original, ic=0.03  │   │
│  │ Trajectory 2: direction=1, phase=original, ic=0.05  │   │
│  │ Trajectory 3: direction=0, phase=mutation, ic=0.04  │   │
│  │ Trajectory 4: parents=[1,2], phase=crossover, ic=0.06│   │
│  │ ...                                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  任务调度逻辑                                                  │
│  ├─ Original: 为每个 planning 方向创建初始任务                  │
│  ├─ Mutation: 对每条已有轨迹生成变异任务                        │
│  └─ Crossover: 选择 K 个父代组合，生成交叉任务                  │
│                                                              │
│  父代选择策略                                                  │
│  ├─ best: 优先选择表现最好的轨迹                               │
│  ├─ weighted: 性能加权采样（差的更可能被选中，鼓励探索）          │
│  └─ random: 随机选择                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
交叉轮评估器的评估机制
1. 可见的评价指标
交叉轮评估器可以看到每个轨迹的 7 个指标：
指标	说明	用途
IC	信息系数	因子与收益的相关性
ICIR	IC 信息比率	IC 的稳定性
RankIC	排名 IC	更稳健的因子相关性指标
RankICIR	排名 IC 信息比率	RankIC 的稳定性
annualized_return	年化超额收益率	策略收益能力
information_ratio	信息比率	风险调整后收益
max_drawdown	最大回撤	策略风险
2. 主要评估指标
当前使用 RankIC 作为主要评估指标（get_primary_metric() 方法）：
trajectory.pyLines 90-92
def get_primary_metric(self) -> Optional[float]:    """Get the primary metric (RankIC) for comparison."""    return self.backtest_metrics.get("RankIC")
3. 评估用于哪些决策
决策环节	使用方式
父代选择	根据 parent_selection_strategy 使用 get_primary_metric() (RankIC) 排序或加权
组合评分	select_crossover_pairs 中根据平均 RankIC 评估组合质量
多样性偏好	结合 direction_id 多样性 + phase 多样性 + 平均性能综合打分
4. LLM 可见的轨迹信息
在生成交叉提示词时，LLM 可以看到：
### Parent 1: Original Round**Direction ID**: 0**Hypothesis**: 价量因子挖掘...**Factors**:  - ROC60_Factor: RANK(TS_PCTCHANGE($close, 60))...**Metrics**:  - IC: 0.0053  - ICIR: 0.0418  - RankIC: 0.0220  - RankICIR: 0.1789  - annualized_return: 0.068  - information_ratio: 1.12  - max_drawdown: -0.05**Feedback**: The results show...
5. 评估流程图
┌─────────────────────────────────────────────────────────────────┐│                    交叉轮评估流程                                │├─────────────────────────────────────────────────────────────────┤│                                                                  ││  1. 候选轨迹池 (来自前几轮)                                       ││     ├── 轨迹A: RankIC=0.22, direction=0, phase=original          ││     ├── 轨迹B: RankIC=0.18, direction=1, phase=original          ││     ├── 轨迹C: RankIC=0.25, direction=0, phase=mutation          ││     └── 轨迹D: RankIC=0.15, direction=1, phase=mutation          ││                                                                  ││  2. 根据 parent_selection_strategy 筛选                          ││     ├── best: 按 RankIC 降序取 Top-N                             ││     ├── weighted: 高 RankIC 权重大                                ││     ├── weighted_inverse: 低 RankIC 权重大（探索）                 ││     └── top_percent_plus_random: 前30%必选 + 随机                 ││                                                                  ││  3. 生成组合并评分                                                ││     ├── 组合1: [A, C] → score = diversity + avg_metric            ││     ├── 组合2: [A, D] → score = ...                               ││     └── ...                                                       ││                                                                  ││  4. 选择 Top-N 组合作为交叉父代                                    ││                                                                  │└─────────────────────────────────────────────────────────────────┘
---

## 4. 独立回测框架

### 4.1 设计目的

主实验过程中的回测（`factor_backtest`）用于快速评估单个因子。而独立回测框架（`backtest_v2`）用于：

1. **批量评估**：对整个因子库进行统一回测
2. **长周期验证**：使用更长的测试期（2022-2025）验证因子稳定性
3. **组合效果**：评估多因子组合的整体表现
4. **对照实验**：与 Qlib 官方因子库（Alpha158）进行对比

### 4.2 回测配置

```yaml
# backtest_v2/config.yaml 关键配置

数据配置:
  数据源: ~/.qlib/qlib_data/cn_data
  市场: csi300 (沪深300成分股)
  数据范围: 2016-01-01 ~ 2025-12-26

数据集划分:
  训练集: 2016-01-01 ~ 2020-12-31  # 模型学习历史规律
  验证集: 2021-01-01 ~ 2021-12-31  # 模型调参
  测试集: 2022-01-01 ~ 2025-12-26  # 样本外验证（最终评估）

模型配置:
  模型类型: LightGBM
  学习率: 0.1
  最大深度: 8
  叶子节点数: 210
  早停轮数: 50
  最大迭代: 500

回测策略:
  策略: TopkDropoutStrategy
  - topk: 50      # 持有评分最高的50只股票
  - n_drop: 5     # 每次调仓剔除评分最低的5只
  
交易成本:
  买入: 0.05%
  卖出: 0.15%
  最低: 5元
```

### 4.3 使用方式

```bash
# 单个因子库回测
python backtest_v2/run_backtest.py \
    -c backtest_v2/config.yaml \
    --factor-source custom \
    --factor-json /path/to/factors.json

# 与 Alpha158 对比
python backtest_v2/run_backtest.py \
    -c backtest_v2/config.yaml \
    --factor-source alpha158_20

# 批量回测
./批量回测.sh
```

### 4.4 两套回测的区别

| 特性 | 主程序内部回测 | 独立回测框架 |
|------|---------------|--------------|
| 用途 | 快速评估单因子 | 批量评估因子库 |
| 回测期 | 2021年（验证集） | 2022-2025（测试集） |
| 因子数 | 2-3个/轮 | 整个因子库 |
| 缓存 | 自动缓存到 workspace | 独立缓存目录 |
| 输出 | 写入因子库 JSON | 独立指标 JSON |

---

## 5. 评价指标详解

### 5.1 重要说明：收益指标均为超额收益

⚠️ **注意**：回测框架输出的收益类指标（`annualized_return`、`max_drawdown` 等）**均为超额收益**，即相对于基准（沪深300指数）的超额表现，而非绝对收益。

**计算公式**：
```python
超额收益 = 组合收益 - 基准收益 - 交易成本
excess_return = portfolio_return - bench_return - cost
```

所有风险分析指标（年化收益、最大回撤、信息比率等）均基于此超额收益序列计算。

### 5.2 预测能力指标

#### IC (Information Coefficient)
```
定义: 因子值与未来收益的 Pearson 相关系数
范围: [-1, 1]
解读:
  IC > 0.03: 因子有一定预测能力
  IC > 0.05: 因子预测能力较强
  IC > 0.10: 因子预测能力很强（罕见）
  
计算公式:
  IC_t = Corr(Factor_t, Return_{t+1})
  IC = Mean(IC_t)  # 所有时间的平均
```

#### ICIR (IC Information Ratio)
```
定义: IC 的均值与标准差之比
公式: ICIR = Mean(IC) / Std(IC)
解读:
  ICIR > 0.5: 因子预测能力稳定
  ICIR > 1.0: 因子预测能力非常稳定
  
意义: IC 高但不稳定的因子可能不如 IC 适中但稳定的因子
```

#### Rank IC
```
定义: 因子排名与收益排名的 Spearman 相关系数
优势: 对异常值更鲁棒，更适合实际投资场景
```

#### Rank ICIR
```
定义: Rank IC 的均值与标准差之比
公式: RankICIR = Mean(RankIC) / Std(RankIC)
```

### 5.3 收益指标（均为超额收益）

#### 超额年化收益率 (Annualized Return)
```
定义: 策略相对于基准的年化超额收益
公式: Ann_Excess_Return = (1 + Total_Excess_Return)^(252/Trading_Days) - 1
示例:
  0.18 (18%) 表示策略每年跑赢基准 18%
  
注意: 此指标已扣除交易成本
```

#### 信息比率 (Information Ratio)
```
定义: 超额收益与跟踪误差之比
公式: IR = Mean(Excess_Return) / Std(Excess_Return) × √252
解读:
  IR > 1.0: 策略显著跑赢基准
  IR > 2.0: 策略表现优异
  
意义: 衡量每承担1单位跟踪误差风险，可获得多少超额收益
```

#### 超额最大回撤 (Max Drawdown)
```
定义: 超额收益曲线从历史最高点到最低点的最大跌幅
公式: MDD = min((Excess_Cumulative_t - Excess_Peak) / Excess_Peak)
示例:
  -0.09 (-9%) 表示超额收益最大从高点下跌 9%
  
注意: 这是相对于基准的回撤，不是组合绝对回撤
```

#### 卡尔玛比率 (Calmar Ratio)
```
定义: 超额年化收益与超额最大回撤的比值
公式: Calmar = Ann_Excess_Return / |MDD|
解读:
  Calmar > 1.0: 收益风险比较好
  Calmar > 2.0: 收益风险比优秀
```

### 5.4 指标解读示例

以实际回测结果为例（`QA_phase_mutation` 因子库）：

```json
{
  "IC": 0.1277,                    // 非常强的预测能力
  "ICIR": 0.8738,                  // 预测能力稳定
  "Rank IC": 0.1242,               // 排名预测能力强
  "Rank ICIR": 0.8566,             // 排名预测稳定
  "annualized_return": 0.1827,     // 超额年化收益 18.27%
  "information_ratio": 2.2588,     // 信息比率 2.26
  "max_drawdown": -0.0894,         // 超额最大回撤 8.94%
  "calmar_ratio": 2.0447           // 收益风险比 2.04
}
```

**综合评价**：
- 该因子库在 2022-2025 测试期表现优异
- IC > 0.12 表明因子组合有很强的收益预测能力
- **超额年化收益 18.27%**：策略每年平均跑赢沪深300指数 18.27%（已扣除交易成本）
- **信息比率 2.26**：每承担 1% 的跟踪误差，可获得 2.26% 的超额收益（IR > 2 通常被认为优秀）
- **超额最大回撤 8.94%**：相对于基准的最大下跌幅度控制在 9% 以内
- **卡尔玛比率 2.04**：超额收益是最大回撤的 2 倍，风险收益比良好

### 5.5 与基准对比总结

| 指标类型 | 具体指标 | 基准对比方式 |
|----------|----------|--------------|
| 预测能力 | IC, ICIR, Rank IC, Rank ICIR | 直接计算因子与收益的相关性 |
| 收益指标 | annualized_return | **超额**年化 = 组合年化 - 基准年化 - 成本 |
| 风险指标 | max_drawdown | **超额**收益曲线的最大回撤 |
| 综合指标 | information_ratio, calmar_ratio | 基于超额收益计算 |

**基准设置**：
```yaml
benchmark: SH000300  # 沪深300指数
market: csi300       # 沪深300成分股
```

---

## 6. 实验配置与超参数

### 6.1 核心超参数

#### 规划阶段 (Planning)
```yaml
planning:
  num_directions: 10    # 并行探索方向数
                        # 越大 → 初始探索越广，但资源消耗越大
                        # 建议范围: 5-15
```

#### 进化阶段 (Evolution)
```yaml
evolution:
  max_rounds: 5         # 最大进化轮数
                        # 越大 → 探索越深入，但耗时越长
                        # 建议范围: 3-7
  
  crossover_size: 2     # 每次交叉的父代数量
                        # 2: 两两交叉（最常用）
                        # 3: 三方交叉（更多样化）
  
  crossover_n: 10       # 每轮交叉生成的组合数
                        # 越大 → 交叉探索越广
                        # 建议范围: 5-15
  
  parent_selection_strategy: best  # 父代选择策略
                        # best: 优先选择最优轨迹
                        # weighted: 加权采样（鼓励探索）
                        # random: 随机选择
```

#### 执行阶段 (Execution)
```yaml
execution:
  max_loops: 7          # 每条轨迹的最大循环次数
                        # 总步数 = max_loops × 5
  
  steps_per_loop: 5     # 固定为 5（5 步循环）
```

### 6.2 配置示例

**探索模式**（广度优先）:
```yaml
planning:
  num_directions: 15
evolution:
  max_rounds: 3
  crossover_n: 15
  parent_selection_strategy: weighted
```

**深度模式**（深度优先）:
```yaml
planning:
  num_directions: 5
evolution:
  max_rounds: 7
  crossover_n: 5
  parent_selection_strategy: best
```

**平衡模式**（推荐）:
```yaml
planning:
  num_directions: 10
evolution:
  max_rounds: 5
  crossover_n: 10
  parent_selection_strategy: best
```

---

## 7. 数据与回测设置

### 7.1 数据来源

```
数据源: Qlib 中国 A 股数据
路径: ~/.qlib/qlib_data/cn_data

包含:
- 日线行情: 开盘价、最高价、最低价、收盘价、成交量
- 市值、估值等基本面数据
- 沪深300 成分股列表
```

### 7.2 市场设置

```yaml
市场: csi300 (沪深300成分股)
基准: SH000300 (沪深300指数)

选择理由:
- 流动性好，交易成本低
- 代表性强，覆盖核心蓝筹
- 数据质量高，异常值少
```

### 7.3 时间划分

```
┌───────────────────────────────────────────────────────────────┐
│                        时间线                                  │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  2016        2020        2021        2022        2025         │
│    │──────────┼───────────┼───────────┼───────────┤          │
│    │  训练集   │  验证集    │         测试集         │          │
│    │  5年     │  1年      │         4年           │          │
│    │          │           │                       │          │
│    │  模型学习  │  调参优化  │    样本外评估（最终）   │          │
│    │  历史规律  │           │                       │          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**设计考量**:
- **训练集 (2016-2020)**：5 年数据足够模型学习市场规律
- **验证集 (2021)**：防止过拟合，用于早停和超参调优
- **测试集 (2022-2025)**：完全样本外，评估真实泛化能力

### 7.4 交易策略

```yaml
策略: TopkDropoutStrategy
参数:
  topk: 50      # 持有评分最高的 50 只股票
  n_drop: 5     # 每次调仓剔除评分最低的 5 只

逻辑:
1. 每个交易日，对所有股票计算预测评分
2. 选择评分最高的 50 只构建组合
3. 每次调仓时：
   - 保留原组合中评分仍在 Top50 的股票
   - 卖出评分最低的 5 只
   - 买入新进入 Top50 的股票
4. 等权重持仓

优势:
- 避免过度交易（只剔除最差的）
- 保持组合稳定性
- 降低交易成本
```

---

## 8. 实验结论与分析

### 8.1 实验设计总结

1. **输入**：用户提供探索方向（如"动量策略"、"价值因子"）
2. **过程**：
   - Planning 生成 10 个并行方向
   - 5 轮进化（原始 → 变异 → 交叉 → 变异 → 交叉）
   - 每轮 7 次循环，每次生成 2-3 个因子
3. **输出**：因子库 JSON（包含数百个经过验证的因子）

### 8.2 关键发现

#### 进化阶段对因子质量的影响

| 进化阶段 | 因子特点 | 典型表现 |
|----------|----------|----------|
| Original | 基础探索 | IC 分布广，包含大量噪声因子 |
| Mutation | 改进优化 | 在原始基础上针对性改进，IC 略有提升 |
| Crossover | 组合创新 | 融合多个方向优点，可能产生突破性因子 |

#### 因子筛选策略
- **RankIC 排序**：选择预测能力最强的因子
- **阶段筛选**：不同阶段因子可能有不同特性
- **随机采样**：验证整体因子库质量

### 8.3 实践建议

1. **初次实验**：使用平衡模式配置，运行完整流程
2. **对比基准**：始终与 Alpha158 进行对比
3. **多次验证**：不同时间窗口、不同市场验证
4. **因子筛选**：关注 RankIC > 0.03 且 ICIR > 0.5 的因子

### 8.4 局限性与改进方向

| 局限性 | 可能的改进 |
|--------|-----------|
| LLM 生成因子可能有偏差 | 增加因子正则化约束 |
| 回测可能存在过拟合 | 使用更多样本外验证 |
| 计算资源消耗大 | 优化缓存机制，增量计算 |
| 交易成本简化 | 考虑更真实的滑点模型 |

---

## 附录

### A. 常用命令速查

```bash
# 运行主实验
./运行实验.sh "你的探索方向"

# 独立回测
python backtest_v2/run_backtest.py -c backtest_v2/config.yaml \
    --factor-source custom \
    --factor-json /path/to/factors.json

# 批量回测
./批量回测.sh

# 查看因子库
python show_all_factors.py

# 清理缓存
./清理缓存.sh
```

### B. 目录结构

```
AlphaAgent/                      # Quanta Alpha 主目录
├── 运行实验.sh                   # 主实验入口
├── 批量回测.sh                   # 批量回测脚本
├── 清理缓存.sh                   # 清理缓存脚本
├── all_factors_library_*.json   # 因子库输出
├── factor_library/              # 因子库采样
├── backtest_v2/                 # 独立回测框架
│   ├── run_backtest.py          # 回测入口
│   ├── config.yaml              # 回测配置
│   └── ...
├── alphaagent/                  # 核心代码
│   ├── app/                     # 应用入口
│   │   └── qlib_rd_loop/        # 主循环
│   │       ├── run_config.yaml
│   │       ├── factor_mining.py
│   │       └── ...
│   ├── components/              # 组件
│   │   ├── workflow/            # 工作流
│   │   ├── coder/               # 因子编码
│   │   └── proposal/            # 提案生成
│   └── scenarios/               # 场景配置
│       └── qlib/                # Qlib 场景
└── /mnt/DATA/quantagent/        # 数据存储
    └── AlphaAgent/
        ├── factor_cache/        # 因子缓存
        ├── backtest_v2_results/ # 回测结果
        └── QuantaAlpha_workspace/  # 工作空间
```

### C. 指标速查表

| 指标 | 中文名 | 类型 | 好的标准 | 说明 |
|------|--------|------|----------|------|
| IC | 信息系数 | 预测能力 | > 0.05 | 因子与收益的相关性 |
| ICIR | IC信息比 | 预测稳定性 | > 0.5 | IC的稳定程度 |
| Rank IC | 排名IC | 预测能力 | > 0.05 | 排名相关性，更鲁棒 |
| Rank ICIR | 排名IC信息比 | 预测稳定性 | > 0.5 | Rank IC的稳定程度 |
| annualized_return | **超额**年化收益 | 收益 | > 10% | 相对基准的年化超额 |
| information_ratio | 信息比率 | 风险调整收益 | > 1.0 | 超额收益/跟踪误差 |
| max_drawdown | **超额**最大回撤 | 风险 | > -15% | 超额收益曲线最大跌幅 |
| calmar_ratio | 卡尔玛比率 | 风险调整收益 | > 1.0 | 超额年化/\|最大回撤\| |

### D. 参考文献

1. Qlib: An AI-oriented Quantitative Investment Platform (Microsoft Research)
2. LightGBM: A Highly Efficient Gradient Boosting Decision Tree
3. Factor Investing: From Traditional to Alternative Risk Premia

---

*文档版本: 1.1*  
*项目名称: Quanta Alpha*  
*更新日期: 2026-01-17*
