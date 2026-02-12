# QuantaAlpha Windows 版 — 从零启动指南

基于 `README_CN.md` 整理，从 **git clone** 到启动整个框架的完整步骤（**Windows 分支**）。

---

## 第一步：克隆项目（Windows 分支）

```powershell
cd C:\Users\16507\PythonProject\DS\quantalpha
git clone -b windows --single-branch https://github.com/QuantaAlpha/QuantaAlpha.git QuantaAlpha-fix
cd QuantaAlpha-fix
```

> 使用 `-b windows` 拉取的是 Windows 兼容分支；若用默认分支则去掉 `-b windows --single-branch`，并改目录名为 `QuantaAlpha`。

---

## 第二步：创建 Conda 环境并安装依赖

```powershell
conda create -n quantaalpha python=3.10 -y
conda activate quantaalpha
```

安装项目（开发模式）：

```powershell
set SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0
pip install -e .
pip install -r requirements.txt
```

> 若使用 PowerShell 且 `set` 无效，可改为：  
> `$env:SETUPTOOLS_SCM_PRETEND_VERSION="0.1.0"`

---

## 第三步：配置 `.env`

```powershell
copy configs\.env.example .env
```

用记事本或 VS Code 编辑 `.env`，**路径请用正斜杠**，例如：

```bash
# === 必填：数据路径 ===
QLIB_DATA_DIR=C:/Users/16507/PythonProject/DS/quantalpha/data/raw/cn_data/cn_data
DATA_RESULTS_DIR=C:/Users/16507/PythonProject/DS/quantalpha/data/results

# === 必填：LLM API ===
OPENAI_API_KEY=你的API密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
CHAT_MODEL=deepseek-chat
REASONING_MODEL=deepseek-chat

# === Windows 必填 ===
CONDA_DEFAULT_ENV=quantaalpha
```

根据你本机实际路径和 API 修改上述内容。

---

## 第四步：准备数据（若尚未准备）

需要两类数据：

1. **Qlib 行情数据** `cn_data`（回测用）
2. **价量 HDF5**：`daily_pv.h5` / `daily_pv_debug.h5`（因子挖掘用）

从 HuggingFace 下载示例：

```powershell
pip install huggingface_hub
huggingface-cli download QuantaAlpha/qlib_csi300 --repo-type dataset --local-dir ./hf_data
```

解压并放到项目约定位置（或你在 `.env` 里配置的路径）：

- 将 `cn_data` 解压到某目录，并把该目录填到 `.env` 的 `QLIB_DATA_DIR`
- 将 `daily_pv.h5` 放到 `git_ignore_folder/factor_implementation_source_data/daily_pv.h5`  
  或通过 `.env` 中的 `FACTOR_CoSTEER_DATA_FOLDER` 指定自定义目录

若你已有 `C:\Users\16507\PythonProject\DS\quantalpha\data` 下的数据，只需在 `.env` 中把 `QLIB_DATA_DIR` 和 `DATA_RESULTS_DIR` 指到对应路径即可。

---

## 第五步：启动方式（二选一）

### 方式 A：命令行 — 因子挖掘

在项目根目录（`QuantaAlpha-fix`）下：

```powershell
conda activate quantaalpha
python launcher.py mine --direction "价量因子挖掘"
```

可选：指定因子库后缀：

```powershell
python launcher.py mine --direction "价量因子挖掘" exp_micro
```

### 方式 B：Web 界面（前后端分离）

需要 **Node.js 18+**。开两个终端：

**终端 1 — 后端 API：**

```powershell
cd C:\Users\16507\PythonProject\DS\quantalpha\QuantaAlpha-fix\frontend-v2
conda activate quantaalpha
python backend/app.py
```

**终端 2 — 前端：**

```powershell
cd C:\Users\16507\PythonProject\DS\quantalpha\QuantaAlpha-fix\frontend-v2
npm install
npm run dev
```

浏览器访问：**http://localhost:3000**

---

## 第六步：独立回测（在挖掘出因子库之后）

```powershell
conda activate quantaalpha
cd C:\Users\16507\PythonProject\DS\quantalpha\QuantaAlpha-fix

python -m quantaalpha.backtest.run_backtest -c configs/backtest.yaml --factor-source custom --factor-json data/factorlib/all_factors_library.json -v
```

若因子库在其他路径，将 `data/factorlib/all_factors_library.json` 换成实际路径。

---

## 常见问题（Windows）

| 现象 | 处理 |
|------|------|
| `CondaConf conda_env_name: Input should be a valid string` | 在 `.env` 中增加 `CONDA_DEFAULT_ENV=quantaalpha` |
| `UnicodeEncodeError: 'gbk'` | 终端执行 `chcp 65001` 或设置环境变量 `PYTHONIOENCODING=utf-8` |
| 前端报错 `@radix-ui/react-hover-card` | 在 `frontend-v2` 下执行 `npm install` |
| Linux 的 `./run.sh` | Windows 用：`python launcher.py mine --direction "方向"` |

更多 Windows 差异与排错见项目内：`docs/WINDOWS_COMPAT.md`。

---

## 步骤速览

| 顺序 | 操作 |
|------|------|
| 1 | `git clone -b windows --single-branch https://github.com/QuantaAlpha/QuantaAlpha.git QuantaAlpha-fix` → `cd QuantaAlpha-fix` |
| 2 | `conda create -n quantaalpha python=3.10 -y` → `conda activate quantaalpha` |
| 3 | `set SETUPTOOLS_SCM_PRETEND_VERSION=0.1.0` → `pip install -e .` → `pip install -r requirements.txt` |
| 4 | `copy configs\.env.example .env`，编辑 `.env`（路径、API、`CONDA_DEFAULT_ENV`） |
| 5 | 准备 Qlib 数据与 HDF5（或确认现有路径与 `.env` 一致） |
| 6 | **命令行**：`python launcher.py mine --direction "价量因子挖掘"`；**Web**：先 `python backend/app.py`，再另开终端 `npm install && npm run dev`，访问 http://localhost:3000 |

按上述顺序在本地执行即可从零启动整个框架。
