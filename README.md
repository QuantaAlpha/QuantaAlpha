# QuantaAlpha

<div align="center">
  <img src="docs/_static/logo.png" alt="QuantaAlpha logo" style="width:60%;">
</div>

**QuantaAlpha** - LLM驱动的Alpha因子挖掘框架

基于论文: [AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay](https://arxiv.org/abs/2502.16789) (KDD 2025)

## 📖 简介

QuantaAlpha 是一个自主框架，通过三个专门的智能体协同工作，用于挖掘可解释且抗衰减的Alpha因子：

- **Idea Agent (假设生成智能体)**: 基于金融理论提出市场假设，指导因子创建
- **Factor Agent (因子构建智能体)**: 根据假设构建因子，融入正则化机制避免重复和过拟合
- **Eval Agent (评估智能体)**: 执行回测验证，通过反馈循环迭代优化因子

## 📁 项目结构

```
QuantaAlpha/
├── configs/                  # 配置文件
│   ├── run_config.yaml      # 主运行配置
│   └── backtest/            # 回测配置
├── scripts/                  # 运行脚本
│   ├── run_experiment.sh    # 实验运行脚本
│   └── clean_cache.sh       # 清理缓存脚本
├── quantaalpha/             # 核心代码包
│   ├── app/                 # 应用入口
│   ├── core/                # 核心模块
│   ├── components/          # 组件模块
│   ├── scenarios/           # 场景模块
│   └── utils/               # 工具函数
├── backtest/                # 回测模块
├── tools/                   # 独立工具脚本
└── docs/                    # 文档
```

## ⚡ 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
conda create -n quantaalpha python=3.10
conda activate quantaalpha

# 安装 QuantaAlpha
pip install -e .
```

### 2. 配置 API

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入您的 API 密钥
```

### 3. 准备数据

首先安装 Qlib:

```bash
git clone https://github.com/microsoft/qlib.git
cd qlib && pip install . && cd ..
```

然后准备中国股票数据:

```bash
# 下载数据
python prepare_cn_data.py

# 转换为 Qlib 格式 (参考 Qlib 文档)
```

### 4. 运行实验

```bash
# 基本用法
bash scripts/run_experiment.sh "您的市场假设"

# 指定模型
MODEL_PRESET=gemini bash scripts/run_experiment.sh "价量因子挖掘"

# 支持的模型预设: gemini, deepseek, claude, gpt, qwen
```

### 5. 运行回测

```bash
python backtest/run_backtest.py -c configs/backtest/config.yaml \
    --factor-source custom --factor-json path/to/factors.json
```

## 🌟 核心功能

### 1. 进化探索 (交叉/变异)

QuantaAlpha 实现了进化算法驱动的因子探索：

- **变异 (Mutation)**: 在优秀因子基础上进行局部探索，生成变体因子
- **交叉 (Crossover)**: 组合多个高性能因子的特征，发现新的因子模式
- **轨迹池管理**: 跟踪所有探索轨迹，支持父代选择策略 (best/random/weighted)

### 2. 质量门控

三重质量检验机制，确保因子质量：

| 检验类型 | 功能 | 默认状态 |
|---------|------|---------|
| 一致性检验 | 验证假设→描述→表达式的逻辑一致性 | ✅ 开启 |
| 复杂度检验 | 限制符号长度、基础特征数、自由参数比例 | ✅ 开启 |
| 冗余度检验 | 基于AST子树匹配检测重复因子 | ✅ 开启 |

### 3. 因子正则化

防止过拟合的正则化机制 (论文公式):

```
R_g(f, h) = α₁·SL(f) + α₂·PC(f) + α₃·ER(f, h)
```

- **SL**: 符号长度约束 (默认 ≤250)
- **PC**: 参数复杂度约束 (自由参数比例 ≤0.5)
- **ER**: 特征使用约束 (基础特征数 ≤6)

## ⚙️ 配置说明

### 模型配置

在 `.env` 文件中配置:

```bash
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
REASONING_MODEL=google/gemini-3-pro-preview
CHAT_MODEL=google/gemini-3-pro-preview
```

### 运行配置

编辑 `configs/run_config.yaml` 自定义:

- **进化参数**: `mutation_enabled`, `crossover_enabled`, `max_rounds`
- **执行参数**: `max_loops`, `steps_per_loop`, `parallel_enabled`
- **质量门控**: `consistency_enabled`, `complexity_enabled`, `redundancy_enabled`

## 📚 引用

如果您觉得这项工作有帮助，请引用我们的论文：

```bibtex
@misc{tang2025alphaagentllmdrivenalphamining,
      title={AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay}, 
      author={Ziyi Tang and Zechuan Chen and Jiarui Yang and Jiayao Mai and Yongsen Zheng and Keze Wang and Jinrui Chen and Liang Lin},
      year={2025},
      eprint={2502.16789},
      archivePrefix={arXiv},
      primaryClass={cs.CE},
      url={https://arxiv.org/abs/2502.16789}, 
}
```

## 📄 许可证

MIT License
