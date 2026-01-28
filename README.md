<h4 align="center">
  <img src="docs/_static/logo.png" alt="QuantaAlpha logo" style="width:70%; ">
  
  <!-- <a href="https://arxiv.org/abs/2502.16789"><b>📃论文链接</b>👁️</a> -->
</h3>

# QuantaAlpha - LLM驱动的Alpha因子挖掘框架

基于 KDD 2025 论文: [AlphaAgent: LLM-Driven Alpha Mining with Regularized Exploration to Counteract Alpha Decay](https://arxiv.org/abs/2502.16789)

# 📖 简介
<div align="center">
      <img src="docs/_static/workflow.png" alt="我们的核心场景" style="width:60%; ">
</div>

**QuantaAlpha** 是一个自主框架，通过三个专门的智能体有效整合LLM智能体，用于挖掘可解释且抗衰减的Alpha因子。  

- **Idea Agent（假设生成智能体）**: 基于金融理论或新兴趋势提出市场假设，指导因子创建。  
- **Factor Agent（因子构建智能体）**: 根据假设构建因子，同时融入正则化机制以避免重复和过拟合。 
- **Eval Agent（评估智能体）**: 验证实用性，执行回测，并通过反馈循环迭代优化因子。

本仓库遵循 [RD-Agent](https://github.com/microsoft/RD-Agent) 的实现。您可以在以下地址找到其仓库: [https://github.com/microsoft/RD-Agent](https://github.com/microsoft/RD-Agent)。我们要向RD-Agent团队的开创性工作和社区贡献表示诚挚的感谢。


# ⚡ 快速开始

### 🐍 创建 Conda 环境
- 使用 Python 创建新的 conda 环境（在我们的 CI 中，3.10 和 3.11 版本已充分测试）:
  ```sh
  conda create -n quantaalpha python=3.10
  ```
- 激活环境:
  ```sh
  conda activate quantaalpha
  ```

### 🛠️ 本地安装
  ```sh
  # 安装 QuantaAlpha
  pip install -e .
  ```

### 📈 数据准备
- 首先，克隆 Qlib 源代码以便在本地运行回测。
  ```
  # 克隆 Qlib 源代码
  git clone https://github.com/microsoft/qlib.git
  cd qlib
  pip install .
  cd ..
  ```

- 然后，通过 baostock 手动下载中国股票数据并转换为 Qlib 格式。
  ```sh
  # 从 baostock 下载或更新从 2015-01-01 到现在的股票数据
  python prepare_cn_data.py

  cd qlib

  # 将 csv 转换为 Qlib 格式。运行前请检查路径是否正确。 
  python scripts/dump_bin.py dump_all ... \
  --include_fields open,high,low,close,preclose,volume,amount,turn,factor \
  --csv_path  ~/.qlib/qlib_data/cn_data/raw_data_now \
  --qlib_dir ~/.qlib/qlib_data/cn_data \
  --date_field_name date \
  --symbol_field_name code

  # 收集日历数据
  python scripts/data_collector/future_calendar_collector.py --qlib_dir ~/.qlib/qlib_data/cn_data/ --region cn


  # 下载 CSI500/CSI300/CSI100 股票池
  python scripts/data_collector/cn_index/collector.py --index_name CSI500 --qlib_dir ~/.qlib/qlib_data/cn_data/ --method parse_instruments
  ```


- 或者，股票数据（已过时）将自动下载到 `~/.qlib/qlib_data/cn_data`。


- 您可以修改位于以下位置的回测配置文件：
  - 基线: `quantaalpha/scenarios/qlib/experiment/factor_template/conf.yaml`
  - 新提出的因子: `quantaalpha/scenarios/qlib/experiment/factor_template/conf_cn_combined.yaml`
  - 要更改训练/验证/测试周期，请先删除 `./git_ignore_folder` 和 `./pickle_cache` 中的所有缓存文件。 
  - 要更改市场，请删除 `./git_ignore_folder` 和 `./pickle_cache` 中的缓存文件。然后，删除目录 `quantaalpha/scenarios/qlib/experiment/factor_data_template/` 中的 `daily_pv_all.h5` 和 `daily_pv_debug.h5`。 


### ⚙️ 配置
- 对于 OpenAI 兼容的 API，请确保在 `.env` 文件中配置了 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY`。
- `REASONING_MODEL` 用于假设生成智能体和因子构建智能体，而 `CHAT_MODEL` 用于调试因子和生成反馈。
- 对于 `REASONING_MODEL`，推荐使用慢思考模型，例如 o3-mini。
- 要在本地环境（而非 Docker）中运行项目，请在 `.env` 文件中添加 `USE_LOCAL=True`。


### 🚀 运行 QuantaAlpha
- 基于 [Qlib 回测框架](http://github.com/microsoft/qlib) 运行 **QuantaAlpha**。
  ```sh
  quantaalpha mine --potential_direction "<您的市场假设>"
  ```

- 或者，运行以下命令
  ```sh
  dotenv run -- python quantaalpha/app/qlib_rd_loop/factor_mining.py --direction "<您的市场假设>"
  ```
  运行命令后，请注销并重新登录以使更改生效。 

- 多因子回测
  ```sh
  quantaalpha backtest --factor_path "<您的CSV文件路径>"
  ```

  您的因子需要存储在 `.csv` 文件中。以下是一个示例：
  ```csv
  factor_name,factor_expression
  MACD_Factor,"MACD($close)"
  RSI_Factor,"RSI($close)"
  ```


- 如果您需要重新运行基线结果或更新回测配置，请删除缓存文件夹：
  ```sh
  rm -r ./pickle_cache/*
  rm -r ./git_ignore_folder/*
  ```

### 🖥️ 监控应用程序结果
- 您可以运行以下命令来查看运行日志的演示程序。请注意，此入口已弃用。 
  ```sh
  quantaalpha ui --port 19899 --log_dir log/
  ```



### 📚 引用
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
