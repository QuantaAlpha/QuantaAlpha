# QuantaAlpha Paper Experiment Reproduction Notes

This document explains the experiment configurations used in the paper.

中文版本: [README_EXPERIMENT.md](README_EXPERIMENT.md)（相同内容的中文说明）

## 1. Initial Seed Factors
*   **File**: `experiment/original_direction.json`
*   **Meaning**: 10 groups of "direction seeds" organized based on the **Alpha158(20)** factor library (each group contains multiple factors).
*   **Usage**: When constructing the initial prompt, you may select one or multiple groups as the LLM's exploration starting point.

## 2. Main Experiment Settings (Paper Defaults)
*   **Plan parallelism**: 10 directions
*   **Evolution**: 5 epochs, 11 rounds in total; Round 1 is Origin, followed by alternating Mutation / Crossover.

## 3. IC Metric: Two Definitions (Do Not Mix)
The IC shown in the system is the correlation between "model prediction vs. future returns", used to measure ranking ability.

### 3.1 Mining-Stage IC (Mining Feedback)
*   **Purpose**: Real-time feedback to the LLM during evolution (a proxy metric).
*   **Features**: "new factors from the current round (usually 3) + 4 base price-volume factors".
*   **Backtest period**: 2021-01-01 to 2021-12-31.
*   **Definition**: **Rank IC** between the Prediction Score and T+2 returns.

### 3.2 Backtest-Stage IC (Backtest Metrics)
*   **Purpose**: Evaluate out-of-sample generalization of the final strategy.
*   **Features**: "selected full factor pool (N factors)".
*   **Backtest period**: 2022-01-01 to 2025-12-26.
*   **Definition**: **Rank IC** between the Prediction Score and T+2 returns.

### Note
*   The high IC reported in the paper's main experiment is the "ensemble factor IC" after LGBM fusion over the full factor pool. The gains mainly come from factor diversity and nonlinear complementarity introduced by self-evolution. In contrast, the experiment analysis results and the mining-stage IC tend to reflect the standalone predictive power of a single factor. They are not directly comparable due to differences in feature inputs, evaluation periods, and model training hyperparameters.

## 4. Embedding
*   **Purpose**: Factor deduplication (semantic similarity) and knowledge-base retrieval.
*   **Requirement**: The current version requires a properly configured embedding service, with no fallback logic. A future version will add supplemental handling.
