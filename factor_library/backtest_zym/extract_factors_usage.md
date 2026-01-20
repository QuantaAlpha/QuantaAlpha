# 因子抽取脚本使用指南

本脚本 (`extract_factors.py`) 用于从现有的因子库 JSON 文件中，根据指定的规则抽取因子并生成新的 JSON 文件。

**脚本路径**: `/home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py`

## 功能特点

1.  **多种抽取方法**: 支持随机抽取、按指标排序抽取、按轮次 (`round_number`) 筛选。
2.  **指标排序**: 支持 IC、RankIC、年化收益 (ARR)、信息比率 (IR)、最大回撤 (MDD) 等多种指标，并支持升序或降序排列。
3.  **多轮次筛选**: 支持同时筛选多个 `round_number`（如 8、9、10）。
4.  **自动命名**: 生成的文件名会自动包含抽取方法、数量、来源及筛选的轮次信息。
5.  **综合评分**: 支持 `FITNESS` 综合指标 ($RankIC \times \sqrt{RankICIR}$)。

## 参数说明

| 参数 | 缩写 | 必填 | 默认值 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| `--source` | `-s` | **是** | - | 源因子库 JSON 文件路径。 |
| `--number` | `-n` | 否 | `None` | 抽取数量。如果不填且使用 `round_number` 方法，则保留所有匹配的因子。 |
| `--method` | `-m` | 否 | `random` | 抽取方法。可选值见下方列表。 |
| `--order` | `-o` | 否 | `desc` | 排序顺序：`asc` (从低到高), `desc` (从高到低)。仅对指标抽取有效。 |
| `--target_rounds` | `-r` | 否 | `None` | 筛选的 `round_number` 列表，支持多选（如 `8 9 10`）。可与任何方法结合使用。 |
| `--output_dir` | `-d` | 否 | `.../backtest_zym` | 输出目录。 |

### 支持的 Method (`-m`)
- `random`: 随机抽取
- `round_number`: 仅根据轮次筛选（配合 `-r` 使用）
- `IC`: Information Coefficient
- `ICIR`: IC Information Ratio
- `RANKIC`: Rank IC
- `RANKICIR`: Rank IC IR
- `ARR`: Annualized Return (年化收益)
- `IR`: Information Ratio
- `MDD`: Max Drawdown (最大回撤)
- `CR`: Calmar Ratio
- `FITNESS`: $RankIC \times \sqrt{RankICIR}$

## 使用示例

### 1. 随机抽取
从源文件中随机抽取 10 个因子。

```bash
python3 /home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py \
  -s /home/tjxy/quantagent/AlphaAgent/all_factors_library_AA.json \
  -n 10 \
  -m random
```

### 2. 按指标排序抽取
抽取 `RankIC` 最高的 20 个因子。

```bash
python3 /home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py \
  -s /home/tjxy/quantagent/AlphaAgent/all_factors_library_AA.json \
  -n 20 \
  -m RANKIC \
  -o desc
```

### 3. 按轮次筛选 (round_number)
筛选 `round_number` 为 8、9、10 的**所有**因子（不限制数量）。

```bash
python3 /home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py \
  -s /home/tjxy/quantagent/AlphaAgent/all_factors_library_AA.json \
  -m round_number \
  -r 8 9 10
```

### 4. 组合筛选 (轮次 + 指标)
从 `round_number` 为 5 的因子中，选取 `IC` 最高的 10 个。

```bash
python3 /home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py \
  -s /home/tjxy/quantagent/AlphaAgent/all_factors_library_AA.json \
  -m IC \
  -r 5 \
  -n 10
```

### 5. 组合筛选 (轮次 + 随机)
从 `round_number` 为 1 或 2 的因子中，随机抽取 15 个。

```bash
python3 /home/tjxy/quantagent/AlphaAgent/factor_library/backtest_zym/extract_factors.py \
  -s /home/tjxy/quantagent/AlphaAgent/all_factors_library_AA.json \
  -m random \
  -r 1 2 \
  -n 15
```

## 输出文件名格式

文件名会自动生成，格式如下：

`{method}_{rounds}_{number}_{source_suffix}.json`

- **method**: 抽取方法（如 `random`, `IC_desc`, `round_number`）
- **rounds**: (如果指定了 `-r`) 显示为 `_rounds_8_9_10`
- **number**: 最终抽取的因子数量
- **source_suffix**: 源文件名后缀

**示例**:
若从 `all_factors_library_QA.json` 中筛选 round 8, 9, 10 的所有因子（共 150 个），生成文件名为：
`round_number_rounds_8_9_10_150_QA.json`
