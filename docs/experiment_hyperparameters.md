# AlphaAgent 实验超参数配置文档

> 本文档详细整理了 `运行实验.sh` 及其相关配置文件中的所有超参数设置。

---

## 目录

1. [模型配置](#1-模型配置)
2. [规划配置](#2-规划配置-planning)
3. [执行配置](#3-执行配置-execution)
4. [进化配置](#4-进化配置-evolution)
5. [因子生成配置](#5-因子生成配置-factor)
6. [回测配置](#6-回测配置-backtest)
7. [数据配置](#7-数据配置-data)
8. [模型训练配置](#8-模型训练配置-lgbmodel)
9. [交易策略配置](#9-交易策略配置-strategy)
10. [LLM配置](#10-llm配置)
11. [日志配置](#11-日志配置-logging)
12. [路径配置](#12-路径配置)

---

## 1. 模型配置

### 1.1 LLM 模型预设

通过 `MODEL_PRESET` 环境变量快速切换模型：

| 预设名称 | 推理模型 | 对话模型 | API 端点 |
|---------|---------|---------|----------|
| `gemini` | `google/gemini-3-pro-preview` | `google/gemini-3-pro-preview` | OpenRouter |
| `deepseek` | `deepseek/deepseek-v3.2` | `deepseek/deepseek-v3.2` | OpenRouter |
| `deepseek_aliyun` | `deepseek-v3.2` | `deepseek-v3.2` | 阿里云 DashScope |
| `claude` | `anthropic/claude-sonnet-4.5` | `anthropic/claude-sonnet-4.5` | OpenRouter |
| `gpt` | `openai/gpt-5.2` | `openai/gpt-5.2` | OpenRouter |
| `qwen` | `qwen3-235b-a22b-instruct-2507` | `qwen3-235b-a22b-instruct-2507` | 阿里云 DashScope |

### 1.2 环境变量覆盖

```bash
REASONING_MODEL=<model_name>   # 推理模型
CHAT_MODEL=<model_name>        # 对话模型
OPENAI_API_KEY=<api_key>       # API 密钥
OPENAI_BASE_URL=<base_url>     # API 端点
```

---

## 2. 规划配置 (Planning)

> 配置文件: `alphaagent/app/qlib_rd_loop/run_config.yaml`

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `enabled` | `true` | bool | 启用并行规划功能 |
| `num_directions` | **10** | int | 🔥**超参** 并行探索方向数量 |
| `max_attempts` | `5` | int | 规划最大重试次数 |
| `use_llm` | `true` | bool | 是否使用 LLM 生成方向 |
| `allow_fallback` | `true` | bool | LLM 失败时是否使用内置模板回退 |
| `prompt_file` | `planning_prompts.yaml` | str | 规划提示词文件路径 |

---

## 3. 执行配置 (Execution)

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `max_loops` | `11` | int | 最大循环迭代次数 |
| `steps_per_loop` | `5` | int | 每循环步数 (固定: 提出假设/构建因子/计算/回测/反馈) |
| `step_n` | `null` | int | 总步数 (最高优先级，覆盖 max_loops × steps_per_loop) |
| `use_local` | `true` | bool | 使用本地环境回测 (vs Docker) |
| `parallel_execution` | `false` | bool | 是否使用多进程并行运行分支 |
| `branch_log_root` | `/path/to/log` | str | 分支日志根目录 |
| `branch_log_prefix` | `branch` | str | 分支日志前缀 |

---

## 4. 进化配置 (Evolution)

> 🔥 核心超参数区域

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `enabled` | `true` | bool | 启用进化模式 |
| `mutation_enabled` | `true` | bool | 启用变异阶段 |
| `crossover_enabled` | `true` | bool | 启用交叉阶段 |
| `max_rounds` | **11** | int | 🔥**超参** 最大进化轮数 (包括原始轮) |
| `crossover_size` | **2** | int | 🔥**超参** 每次交叉选择的父代数量 (可选 2 或 3) |
| `crossover_n` | **10** | int | 🔥**超参** 每轮交叉生成的组合数量 |
| `parallel_enabled` | `false` | bool | 进化阶段内并行执行 |
| `prefer_diverse_crossover` | `true` | bool | 偏好多样化的交叉组合 |
| `parent_selection_strategy` | `best` | str | 父代选择策略 |
| `top_percent_threshold` | `0.3` | float | Top 百分比阈值 (配合 `top_percent_plus_random` 策略) |
| `fresh_start` | `true` | bool | 是否从空轨迹池开始 |
| `cleanup_on_finish` | `false` | bool | 实验结束后是否清理轨迹池 |
| `prompt_file` | `evolution_prompts.yaml` | str | 进化提示词文件路径 |

### 4.1 父代选择策略

| 策略名 | 说明 |
|--------|------|
| `best` | 优先选择表现最好的轨迹 |
| `random` | 随机选择 |
| `weighted` | 性能加权采样 (性能越高权重越高) |
| `weighted_inverse` | 逆性能加权采样 (鼓励探索差轨迹) |
| `top_percent_plus_random` | 前 30% 保证选中 + 剩余随机填充 |

### 4.2 进化流程

```
Round 0: 原始轮 (Original) → 生成初始因子
Round 1: 变异轮 (Mutation) → 对现有因子变异
Round 2: 交叉轮 (Crossover) → 组合不同因子
Round 3: 变异轮 (Mutation)
Round 4: 交叉轮 (Crossover)
...
```

---

## 5. 因子生成配置 (Factor)

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `factors_per_hypothesis` | **3** | int | 🔥 每个假设生成的因子数量 |

### 5.1 复杂度约束

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `symbol_length_threshold` | **250** | 🔥 因子表达式最大字符长度 (防止过拟合关键参数) |
| `base_features_threshold` | `6` | 不同基础特征最大数量 ($close, $open 等) |
| `free_args_ratio_threshold` | `0.5` | 最大自由参数比例 (数值常量/总节点数) |

### 5.2 重复性检查

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `duplication.enabled` | `true` | 启用重复性检查 |
| `duplication.threshold` | `5` | 重复子树大小阈值 |
| `duplication.factor_zoo_path` | `null` | 因子库文件路径 |

---

## 6. 回测配置 (Backtest)

| 参数名 | 默认值 | 类型 | 说明 |
|--------|--------|------|------|
| `use_docker` | `false` | bool | 使用 Docker 环境回测 |
| `timeout` | **800** | int | 🔥 每次回测超时时间 (秒) |
| `qlib.config_name` | `conf.yaml` | str | Qlib 配置文件名 |

---

## 7. 数据配置 (Data)

> 配置文件: `alphaagent/scenarios/qlib/experiment/factor_template/conf.yaml`

### 7.1 Qlib 初始化

| 参数名 | 值 | 说明 |
|--------|-----|------|
| `provider_uri` | `~/.qlib/qlib_data/cn_data` | Qlib 数据路径 |
| `region` | `cn` | 市场区域 (cn/us) |

### 7.2 市场配置

| 参数名 | 值 | 说明 |
|--------|-----|------|
| `market` | **csi300** | 🔥 股票池 (沪深300) |
| `benchmark` | **SH000300** | 🔥 基准指数 (沪深300指数) |

### 7.3 时间范围

| 数据集 | 时间范围 | 说明 |
|--------|----------|------|
| **整体数据** | 2016-01-01 ~ 2025-12-26 | 全部数据范围 |
| **训练集** | 2016-01-01 ~ 2020-12-31 | 模型训练 (5年) |
| **验证集** | 2021-01-01 ~ 2021-12-31 | 模型验证 (1年) |
| **测试集** | 2022-01-01 ~ 2025-12-26 | 回测评估 (约4年) |

### 7.4 数据处理器

```yaml
learn_processors:
  - Fillna (feature)      # 填充缺失值
  - ProcessInf            # 处理无穷值
  - DropnaLabel           # 删除空标签
  - CSRankNorm (feature)  # 截面排名标准化 (特征)
  - CSRankNorm (label)    # 截面排名标准化 (标签)

infer_processors:
  - Fillna (feature)
  - ProcessInf
  - CSRankNorm (feature)
  - CSRankNorm (label)
```

### 7.5 标签定义

```python
label = "Ref($close, -2) / Ref($close, -1) - 1"  # T+2 日收益率
```

---

## 8. 模型训练配置 (LGBModel)

> LightGBM 模型超参数

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `loss` | `mse` | 损失函数 |
| `learning_rate` | **0.05** | 🔥 学习率 |
| `max_depth` | **8** | 🔥 树最大深度 |
| `num_leaves` | **210** | 🔥 叶节点数量 |
| `colsample_bytree` | `0.8879` | 列采样比例 |
| `subsample` | `0.8789` | 行采样比例 |
| `lambda_l1` | `205.6999` | L1 正则化 |
| `lambda_l2` | `580.9768` | L2 正则化 |
| `num_threads` | `20` | 并行线程数 |
| `early_stopping_round` | **50** | 🔥 早停轮数 |
| `num_boost_round` | **500** | 🔥 最大迭代轮数 |

---

## 9. 交易策略配置 (Strategy)

### 9.1 TopkDropout 策略

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `topk` | **50** | 🔥 持仓股票数量 |
| `n_drop` | **5** | 🔥 每日淘汰股票数量 |

### 9.2 交易成本

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `account` | `100000000` | 初始资金 (1亿) |
| `limit_threshold` | `0.095` | 涨跌停阈值 (9.5%) |
| `deal_price` | `open` | 成交价格 (开盘价) |
| `open_cost` | **0.0005** | 🔥 买入成本 (0.05%) |
| `close_cost` | **0.0015** | 🔥 卖出成本 (0.15%) |
| `min_cost` | `5` | 最小交易成本 (元) |

---

## 10. LLM 配置

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `factor_mining_timeout` | `999999` | 因子挖掘总超时 (秒) |
| `max_retries` | `3` | API 调用最大重试次数 |
| `retry_delay` | `1.0` | 重试间隔 (秒) |
| `json_mode_strict` | `true` | JSON 模式严格性 |

---

## 11. 日志配置 (Logging)

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `level` | `INFO` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `save_snapshots` | `true` | 保存中间会话快照 |
| `save_trajectory_pool` | `true` | 保存轨迹池到 JSON |

---

## 12. 路径配置

### 12.1 工作空间路径

```bash
# 自动生成 (默认)
WORKSPACE_PATH=/path/to/workspace/QuantaAlpha_workspace_exp_YYYYMMDD_HHMMSS
PICKLE_CACHE_FOLDER_PATH=/path/to/cache/pickle_cache_exp_YYYYMMDD_HHMMSS

# 手动指定
EXPERIMENT_ID=my_exp bash 运行实验.sh "方向"

# 共享目录模式
EXPERIMENT_ID=shared bash 运行实验.sh "方向"
```

### 12.2 输出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 因子库 | `all_factors_library.json` | 默认输出 |
| 因子库 (带后缀) | `all_factors_library_{suffix}.json` | 指定后缀输出 |
| 配置文件 | `alphaagent/app/qlib_rd_loop/run_config.yaml` | 主配置文件 |
| 回测配置 | `alphaagent/scenarios/qlib/experiment/factor_template/conf.yaml` | Qlib 配置 |

---

## 附录: 关键超参数汇总

| 类别 | 参数 | 默认值 | 影响 |
|------|------|--------|------|
| **规划** | `num_directions` | 10 | 初始探索方向数量 |
| **进化** | `max_rounds` | 11 | 总进化轮数 |
| **进化** | `crossover_size` | 2 | 交叉父代数量 |
| **进化** | `crossover_n` | 10 | 每轮交叉组合数 |
| **因子** | `factors_per_hypothesis` | 3 | 每假设因子数 |
| **因子** | `symbol_length_threshold` | 250 | 表达式长度上限 |
| **模型** | `learning_rate` | 0.05 | LGB 学习率 |
| **模型** | `num_boost_round` | 500 | LGB 迭代次数 |
| **策略** | `topk` | 50 | 持仓股票数 |
| **策略** | `n_drop` | 5 | 每日调仓数 |
| **数据** | `market` | csi300 | 股票池 |
| **数据** | `train` | 2016-2020 | 训练集范围 |
| **数据** | `test` | 2022-2025 | 测试集范围 |

---

*文档生成时间: 2026-01-24*

