# QuantaAlpha

<div align="center">

<img src="images/overview.jpg" width="100%" alt="QuantaAlpha Overview">

**面向因子挖掘与回测的 LLM 驱动实验框架**

[English](README.md) | [中文](README_CN.md)

</div>

---

## 核心框架：基于轨迹的自进化范式

**规划 - 进化 - 约束：让 AI 在真实金融市场中生存**

QuantaAlpha 不满足于单次挖掘的成功，而是追求**轨迹级 (Trajectory) 的进化**。通过模拟真实市场中的研究迭代，它构建了一个具备逻辑自洽性与环境适应力的 Agentic Science 实验平台。

### 多样化规划初始化
> 初始化 Agent 不依赖盲目随机，而是通过 `planning` 算子并行生成差异显著的研究方向（如"微观结构动量" vs "基本面异象"），从源头规避局部最优。

### 轨迹级进化
> - **变异 (Mutation)**：精准定位失效节点（如过时的市场假设），对局部逻辑进行**定向修正**，而非全盘推翻。
> - **交叉 (Crossover)**：跨轨迹融合优势基因，例如将**机构资金流**与**散户情绪**因子非线性重组，涌现出更具鲁棒性的新逻辑。

### 结构化约束
> 引入 AST 符号校验与一致性验证器，强制要求"投资假设—语言描述—代码实现"三位一体，确保进化出的不仅是高收益代码，更是**可解释的经济学假设**。

---

## 实证表现

### 1. 巅峰性能指标

| 维度 | 指标 | 表现 |
| :--- | :--- | :--- |
| **预测效能** | 信息系数 (IC) | **0.1501** |
| | Rank IC | **0.1465** |
| **策略回报** | 年化超额收益 (ARR) | **27.75%** |
| | 最大回撤 (MDD) | **7.98%** |
| | 卡玛比率 (Calmar Ratio) | **3.4774** |

<div align="center">
<img src="images/主实验.png" width="90%" alt="主实验结果">
</div>

### 2. 零样本迁移

在 **CSI 300** 上挖掘出的因子，直接迁移至 **中证500** 和 **标普500**，四年内分别创造了 **160%** 和 **137%** 的累积超额收益。

<div align="center">
<img src="images/figure3.png" width="90%" alt="零样本迁移">
</div>

### 3. 韧性考验

<div align="center">
<img src="images/figure4.png" width="90%" alt="韧性测试">
</div>

---

## 系统要求

| 需求 | 说明 |
| :--- | :--- |
| **操作系统** | Linux（推荐 Ubuntu 20.04+）。Windows / macOS 支持将在未来版本提供 |
| **Python** | 3.10+（推荐使用 Conda） |
| **Node.js** | 18+（仅 Web 看板需要） |
| **内存** | 32 GB+（LightGBM 训练 + 因子计算） |
| **磁盘** | Qlib 数据约 50 GB，建议预留 100 GB 用于实验缓存 |
| **LLM API** | 任何 OpenAI 兼容 API（DashScope、OpenAI 等） |

---

## 项目架构

```
QuantaAlpha/
├── configs/                          # 集中配置（唯一需要修改的地方）
│   ├── .env.example                  #   环境变量模板（复制为 .env 使用）
│   ├── experiment.yaml               #   主实验参数（方向数/轮次/进化策略）
│   └── backtest.yaml                 #   独立回测参数（市场/时段/模型/策略）
│
├── quantaalpha/                      # ===== 核心 Python 包 =====
│   ├── cli.py                        #   CLI 入口（quantaalpha mine / backtest）
│   │
│   ├── pipeline/                     #   主实验工作流
│   │   ├── factor_mining.py          #     因子挖掘主入口 (@force_timeout)
│   │   ├── loop.py                   #     单方向执行循环 (propose → construct → calculate → backtest → feedback)
│   │   ├── planning.py              #     多样化方向规划（LLM 生成 N 个探索方向）
│   │   ├── settings.py               #     配置解析与环境变量注入
│   │   └── evolution/                #     进化引擎
│   │       ├── controller.py         #       进化控制器（调度 original → mutation → crossover 轮次）
│   │       ├── trajectory.py         #       轨迹池管理（评分/排序/父代选择）
│   │       ├── mutation.py           #       变异算子（定向修正失效假设）
│   │       └── crossover.py          #       交叉算子（跨轨迹基因融合）
│   │
│   ├── factors/                      #   因子定义、生成与评估
│   │   ├── proposal.py               #     假设提出（LLM 生成投资假设 + 因子描述）
│   │   ├── library.py                #     因子库管理（JSON 读写 + 缓存状态检查）
│   │   ├── runner.py                 #     因子回测运行器（验证集上快速评估）
│   │   ├── workspace.py              #     因子工作空间（文件组织与隔离）
│   │   ├── coder/                    #     因子代码生成
│   │   │   ├── factor.py             #       因子表达式生成（LLM → Qlib 表达式）
│   │   │   ├── expr_parser.py        #       表达式解析器（文本 → AST）
│   │   │   ├── factor_ast.py         #       AST 分析（复杂度/冗余度检测）
│   │   │   └── function_lib.py       #       支持的算子库（TS_MEAN, RANK, ZSCORE 等）
│   │   └── regulator/                #     质量门控
│   │       ├── factor_regulator.py   #       主调度器（复杂度 + 冗余度检验）
│   │       └── consistency_checker.py#       一致性检验（假设↔描述↔公式↔表达式）
│   │
│   ├── backtest/                     #   独立回测模块 (V2)
│   │   ├── run_backtest.py           #     CLI 入口（argparse）
│   │   ├── runner.py                 #     回测运行器（Qlib DataHandler → LGBModel → TopK 策略）
│   │   ├── factor_loader.py          #     因子加载器（JSON → Qlib 表达式 / 自定义计算）
│   │   └── custom_factor_calculator.py#    自定义因子计算（三级缓存：H5 → MD5 → 重算）
│   │
│   ├── llm/                          #   LLM 客户端
│   │   ├── client.py                 #     统一 API 客户端（支持 OpenAI 兼容接口）
│   │   └── config.py                 #     模型配置（从 .env 读取）
│   │
│   └── core/                         #   核心抽象层
│       ├── evolving_agent.py         #     进化 Agent 基类
│       ├── experiment.py             #     实验抽象
│       ├── proposal.py               #     提案基类
│       └── prompts.py                #     提示词管理
│
├── frontend-v2/                      # ===== Web 看板 (React + TypeScript) =====
│   ├── src/
│   │   ├── main.tsx                  #   React 入口
│   │   ├── App.tsx                   #   路由（display:none 保活，切页不丢状态）
│   │   ├── context/
│   │   │   └── TaskContext.tsx        #   全局状态（Mining + Backtest 任务/WS/轮询）
│   │   ├── services/
│   │   │   └── api.ts                #   API 客户端（REST + WebSocket）
│   │   ├── pages/
│   │   │   ├── HomePage.tsx          #     因子挖掘页（ChatInput + 实时图表）
│   │   │   ├── FactorLibraryPage.tsx #     因子库浏览页（搜索/筛选/详情）
│   │   │   ├── BacktestPage.tsx      #     独立回测页（选库 → 运行 → 结果展示）
│   │   │   └── SettingsPage.tsx      #     系统设置页（API/路径/参数配置）
│   │   ├── components/               #   UI 组件
│   │   │   ├── ChatInput.tsx         #     对话式输入框（高级设置面板）
│   │   │   ├── LiveCharts.tsx        #     实时图表（Recharts 折线图）
│   │   │   ├── ProgressSidebar.tsx   #     进度侧栏（阶段 + 日志流）
│   │   │   ├── ParticleBackground.tsx#     粒子动画背景
│   │   │   └── layout/Layout.tsx     #     主布局（Header + 导航 + 内容区）
│   │   └── types/index.ts            #   TypeScript 类型定义
│   │
│   ├── backend/                      #   FastAPI 后端 API
│   │   └── app.py                    #     REST + WebSocket 服务
│   │                                 #     Mining: 启动子进程 → 流式日志 → WS 推送
│   │                                 #     Backtest: 启动子进程 → 读取 metrics JSON
│   │                                 #     Factors: 读取因子库 JSON → 分页/搜索/缓存状态
│   │
│   ├── start.sh                      #   一键启动脚本（后端 8000 + 前端 3000）
│   ├── vite.config.ts                #   Vite 配置（/api → 8000, /ws → WS 8000）
│   └── package.json                  #   前端依赖
│
├── run.sh                            # 主实验启动脚本（加载 .env → 隔离工作空间 → quantaalpha mine）
├── launcher.py                       # Python 启动器
├── pyproject.toml                    # 包定义（setuptools-scm）
├── requirements.txt                  # Python 依赖清单
└── images/                           # 文档图片
```

### 数据流架构

```
用户需求 (自然语言)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  Planning 模块                                          │
│  LLM 将用户需求扩展为 N 个差异化探索方向                  │
└──────────────────┬──────────────────────────────────────┘
                   │  方向 1, 2, ..., N
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Evolution 控制器                                       │
│                                                         │
│  Round 0: 原始轮 ─── 对每个方向执行完整的 5 步循环         │
│  Round 1: 变异轮 ─── 定向修正表现不佳的假设               │
│  Round 2: 交叉轮 ─── 融合不同方向的优势因子               │
│  Round 3: 变异轮 ─── ...                                │
│  ...                                                    │
│                                                         │
│  ┌──────────────── 5 步循环 ────────────────┐           │
│  │ 1. factor_propose   : LLM 提出假设+表达式 │           │
│  │ 2. factor_construct : 解析/校验/去重       │           │
│  │ 3. factor_calculate : Qlib 计算因子值     │           │
│  │ 4. factor_backtest  : 验证集回测评估       │           │
│  │ 5. factor_feedback  : LLM 分析结果反馈     │           │
│  └────────────────────────────────────────────┘          │
│                                                         │
│  每步完成后 → 因子入库 (all_factors_library*.json)        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  独立回测模块 (Backtest V2)                              │
│                                                         │
│  加载因子库 → 三级缓存加载因子值 → LightGBM 训练          │
│  → TopK Dropout 策略 → 测试集 (2022-2025) 全周期评估     │
│                                                         │
│  三级缓存策略：                                          │
│    1. result.h5  (实验工作空间中的原始计算结果)            │
│    2. MD5 cache  (集中缓存目录，按表达式哈希索引)          │
│    3. 重算       (从表达式通过 Qlib 重新计算)             │
└─────────────────────────────────────────────────────────┘
```

### 前后端交互架构

```
┌──────────────────────────────────────────┐
│           React 前端 (:3000)              │
│                                          │
│  HomePage ──→ POST /api/v1/mining/start  │
│      ↕  WebSocket /ws/mining/{taskId}    │
│      └── 实时接收 progress/log/metrics    │
│                                          │
│  BacktestPage → POST /api/v1/backtest/start
│      ↕  WebSocket /ws/mining/{taskId}    │
│      └── 完成后读取 metrics JSON          │
│                                          │
│  FactorLibraryPage → GET /api/v1/factors │
│  SettingsPage → GET/PUT /api/v1/system/* │
└────────────┬─────────────────────────────┘
             │ Vite Proxy (/api → :8000)
             ▼
┌──────────────────────────────────────────┐
│       FastAPI 后端 (:8000)                │
│                                          │
│  Mining:                                 │
│    asyncio.subprocess → quantaalpha mine │
│    逐行读取 stdout → 解析阶段 → WS 广播   │
│                                          │
│  Backtest:                               │
│    asyncio.subprocess → run_backtest     │
│    完成后读取 *_backtest_metrics.json      │
│                                          │
│  Factors:                                │
│    直接读取 all_factors_library*.json      │
│    分页 + 搜索 + 质量分级                  │
└──────────────────────────────────────────┘
```

---

## 核心功能

- **因子挖掘**：LLM 提出假设与因子表达式，自动进行小规模回测评分
- **轨迹进化**：变异 + 交叉机制，在多个探索方向上实现因子自我进化
- **因子库**：生成 `all_factors_library*.json`，包含回测指标，供后续组合使用
- **独立回测**：从因子库自由组合因子，进行完整周期的回测评估
- **质量门控**：一致性检验、冗余度检验、复杂度检验（可配置）
- **Web 看板**：基于 React 的前端，用于实验监控、因子库浏览和独立回测

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/QuantaAlpha/QuantaAlpha.git
cd QuantaAlpha
```

### 2. 创建 Python 环境

```bash
conda create -n quantaalpha python=3.10
conda activate quantaalpha
```

### 3. 安装依赖

```bash
# 以开发模式安装包
SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pip install -e .

# 安装额外依赖
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp configs/.env.example .env
```

编辑 `.env` 文件：

```bash
# === 必填：数据路径 ===
QLIB_DATA_DIR=/path/to/your/qlib/cn_data      # Qlib 数据目录
DATA_RESULTS_DIR=/path/to/your/results         # 输出目录

# === 必填：LLM API ===
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://your-llm-provider/v1   # 如: DashScope, OpenAI
CHAT_MODEL=deepseek-v3                         # 或 gpt-4, qwen-max 等
REASONING_MODEL=deepseek-v3
```

### 5. 准备 Qlib 数据

QuantaAlpha 使用微软的 [Qlib](https://github.com/microsoft/qlib) 作为金融数据引擎。你需要 A 股市场数据，覆盖 **2016-2025 年**：

```bash
# 方式 A：使用 qlib 内置数据下载
python -c "
import qlib
from qlib.contrib.data.handler import Alpha158
qlib.init(provider_uri='~/.qlib/qlib_data/cn_data', region='cn')
"

# 方式 B：如果你已有 Qlib 数据，将 QLIB_DATA_DIR 指向它即可
# 目录需包含 calendars/、features/、instruments/ 子目录
```

### 6. 运行第一个实验

```bash
./run.sh "价量因子挖掘"
```

大功告成！实验会自动：
1. 通过 LLM 生成多样化的研究方向
2. 为每个方向提出因子假设
3. 生成并验证因子表达式
4. 在验证集（2021年）上运行回测
5. 通过变异和交叉进化因子
6. 将所有发现的因子保存到 `all_factors_library*.json`

---

## 主实验：因子挖掘

### 基本用法

```bash
# 指定研究方向运行
./run.sh "动量反转因子挖掘"

# 指定因子库后缀（输出到 all_factors_library_exp_micro.json）
./run.sh "微观结构因子" "exp_micro"
```

### 核心配置 (configs/experiment.yaml)

```yaml
planning:
  num_directions: 2          # 并行探索方向数量

execution:
  max_loops: 3               # 每个方向的迭代次数

evolution:
  max_rounds: 5              # 总进化轮数
  mutation_enabled: true     # 启用变异阶段
  crossover_enabled: true    # 启用交叉阶段

factor:
  factors_per_hypothesis: 3  # 每个假设生成的因子数
```

### 时间段说明

| 数据集 | 时间范围 | 用途 |
| :--- | :--- | :--- |
| **训练集** | 2016-01-01 ~ 2020-12-31 | 模型训练 |
| **验证集** | 2021-01-01 ~ 2021-12-31 | 挖掘过程中初步回测 |
| **测试集** | 2022-01-01 ~ 2025-12-26 | 独立回测（样本外评估） |

### 基础因子

主实验中，新挖掘的因子会与 **4 个基础因子** 组合后在验证集上进行初步回测评估：

| 名称 | 表达式 | 说明 |
| :--- | :--- | :--- |
| OPEN_RET | `($close-$open)/$open` | 日内开盘到收盘的收益率 |
| VOL_RATIO | `$volume/Mean($volume, 20)` | 成交量相对 20 日均值的比率 |
| RANGE_RET | `($high-$low)/Ref($close, 1)` | 日振幅相对前日收盘价 |
| CLOSE_RET | `$close/Ref($close, 1)-1` | 日收益率（收盘价变化率） |

### 输出

- **因子库**：`all_factors_library*.json` — 所有发现的因子及其回测指标
- **日志**：`log/` 目录下的详细执行日志
- **缓存**：由 `.env` 中的 `DATA_RESULTS_DIR` 控制

---

## 独立回测（组合因子）

挖掘完成后，从因子库中组合因子进行全周期回测，在**测试集（2022-2025）**上评估样本外表现：

```bash
# 仅使用自定义因子回测
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source custom \
  --factor-json all_factors_library.json

# 结合 Alpha158(20) 基线因子
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source combined \
  --factor-json all_factors_library.json

# 仅加载因子，不执行回测（检查因子加载是否正常）
python -m quantaalpha.backtest.run_backtest \
  -c configs/backtest.yaml \
  --factor-source custom \
  --factor-json all_factors_library.json \
  --dry-run -v
```

结果保存在 `configs/backtest.yaml` 中 `experiment.output_dir` 指定的目录。

---

## Web 看板

QuantaAlpha 包含基于 Web 的看板，用于实验监控、因子库浏览和独立回测。

### 一键启动

```bash
conda activate quantaalpha
cd frontend-v2
bash start.sh
```

该脚本会同时启动 FastAPI 后端（端口 8000）和 Vite 前端开发服务器（端口 3000）。

### 手动启动

```bash
# 终端 1：启动后端
conda activate quantaalpha
cd frontend-v2
pip install fastapi uvicorn websockets python-multipart python-dotenv
python backend/app.py

# 终端 2：启动前端
cd frontend-v2
npm install
npm run dev
```

访问 `http://localhost:3000` 即可使用看板。

### 功能

| 页面 | 功能 | 说明 |
| :--- | :--- | :--- |
| **因子挖掘** | 自然语言启动实验 | WebSocket 实时推送进度、日志、指标图表 |
| **因子库** | 浏览已挖掘因子 | 搜索、质量筛选（高/中/低）、详情查看 |
| **独立回测** | 选库运行回测 | 选择因子库 JSON → Custom/Combined 模式 → 结果指标展示 |
| **系统设置** | 配置管理 | LLM API、数据路径、实验参数 |

### API 端点

| 方法 | 路径 | 说明 |
| :--- | :--- | :--- |
| POST | `/api/v1/mining/start` | 启动因子挖掘实验 |
| GET | `/api/v1/mining/{taskId}` | 获取挖掘任务状态 |
| POST | `/api/v1/backtest/start` | 启动独立回测 |
| GET | `/api/v1/backtest/{taskId}` | 获取回测任务状态 |
| GET | `/api/v1/factors` | 分页查询因子库 |
| GET | `/api/v1/factors/libraries` | 列出所有因子库文件 |
| GET | `/api/v1/factors/cache-status` | 因子缓存状态 |
| POST | `/api/v1/factors/warm-cache` | 预热因子缓存 |
| WS | `/ws/mining/{taskId}` | WebSocket 实时推送 |

---

## 质量门控

在 `configs/experiment.yaml` 中配置：

```yaml
quality_gate:
  consistency_enabled: false     # LLM 验证 假设-描述-公式-表达式 一致性检验 默认关闭，开启会增加耗时及api消耗
  complexity_enabled: true       # 限制表达式长度和过度参数化
  redundancy_enabled: true       # 防止与已有因子高度相关
  consistency_strict_mode: false # 严格模式会拒绝不一致的因子
  max_correction_attempts: 3    # LLM 最大修正重试次数
```

---

## 资源消耗估算

| 配置 | 大约 LLM Token | 大约耗时 |
| :--- | :--- | :--- |
| 2 方向 x 3 轮 x 3 因子 | ~100K tokens | ~30-60 分钟 |
| 3 方向 x 5 轮 x 5 因子 | ~500K tokens | ~2-4 小时 |
| 5 方向 x 10 轮 x 5 因子 | ~2M tokens | ~8-16 小时 |

> Token 和时间消耗大约与 `并行方向数 x 进化轮次 x 每假设因子数` 成正比。

---

## 常见问题

| 问题 | 解决方案 |
| :--- | :--- |
| **Qlib 报错找不到数据** | 确认 `.env` 中 `QLIB_DATA_DIR` 指向包含 `calendars/`、`features/`、`instruments/` 的有效 Qlib 数据目录 |
| **LLM API 报错** | 检查 `.env` 中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。QuantaAlpha 支持任何 OpenAI 兼容 API |
| **因子无法解析** | 检查表达式函数是否在 parser 支持范围内。参见 `quantaalpha/factors/coder/function_lib.py` |
| **缓存读取失败** | 确保 `DATA_RESULTS_DIR` 目录存在且可写 |
| **回测结果为空** | 确保 Qlib 数据覆盖配置的时间段（train: 2016-2020，valid: 2021） |
| **setuptools-scm 版本错误** | 使用 `SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0 pip install -e .` |
| **后端仅支持 Linux** | Windows 和 macOS 支持将在未来版本提供。Windows 用户可使用 WSL2 |
| **前端无法连接后端** | 确保后端运行在 8000 端口，Vite 代理配置正确 |
