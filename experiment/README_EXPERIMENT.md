# QuantaAlpha 论文实验复现说明

本文用于对论文中的实验配置进行说明。

English version: [README_EXPERIMENT_EN.md](README_EXPERIMENT_EN.md) (same content in English)

## 1. 初始种子因子 (Seed Factors)
*   **文件**: `experiment/original_direction.json`
*   **含义**: 以 **Alpha158(20)** 因子库为基础整理的 10 组“方向种子”（每组若干因子）。
*   **用法**: 配置初始 Prompt 时可选取一组或多组，作为 LLM 的探索起点。

## 2. 主实验参数（论文默认）
*   **Plan 并行数**: 10 个方向（Directions）
*   **进化轮次**: 5 个 Epoch，合计 11 个 Round；Round 1 为 Origin，其后交替进行 Mutation / Crossover。

## 3. IC 指标：两种口径（务必区分）
系统展示的 IC 均为“模型预测值 vs 未来收益”的相关性指标，用于衡量选股排序能力。

### 3.1 挖掘阶段 IC（Mining Feedback）
*   **用途**: 进化过程中给 LLM 的实时反馈（代理指标）。
*   **特征**: “本轮新因子（通常 3 个）+ 4 个基础量价因子”。
*   **回测期**: 2021-01-01 至 2021-12-31 。
*   **口径**: 预测值（Prediction Score）与 T+2 收益率的 **Rank IC**。

### 3.2 回测阶段 IC（Backtest Metrics）
*   **用途**: 评估最终策略的样本外泛化能力。
*   **特征**: “筛选后的全量因子池（N 个）”。
*   **回测期**: 2022-01-01 至 2025-12-26 。
*   **口径**: 预测值（Prediction Score）与 T+2 收益率的 **Rank IC**。

### 注意
*   文中主实验展示的高 IC 均为全量因子池经 LGBM 融合后的“组合因子 IC”，其增益主要来自自进化带来的因子多样性与非线性互补；而实验分析结果与因子挖掘阶段中的 IC 偏向反映“单因子”的独立预测能力。二者不可直接比较（特征输入量、评估时段与模型训练参数有差异）

## 4. Embedding
*   **用途**: 因子去重（语义相似度）与知识库检索。
*   **要求**: 当前版本需要正确配置 Embedding 服务，无降级逻辑，后续版本会进行补充。
