# QuantaAlpha Windows 兼容性说明

本文档记录了将 QuantaAlpha（原生 Linux 项目）适配到 Windows 系统过程中遇到的
问题及对应修改方案。

---

## 设计原则

rdagent 框架原生不支持 Windows，但它的核心类（`LocalEnv`、`CondaConf` 等）是
可以在运行时覆盖的。本项目 **不修改** rdagent 安装在 `site-packages` 中的源码，
而是通过 **运行时 monkey-patch** 机制在项目代码内完成所有适配：

```
quantaalpha/compat/rdagent_patches.py   ← 所有 rdagent 补丁
```

在每个入口点（`launcher.py`、`cli.py`）启动时，自动调用：

```python
from quantaalpha.compat.rdagent_patches import apply
apply()  # Windows 上应用补丁；Linux 上自动跳过
```

**优点**：
- 所有修改都在项目代码中，可以 Git 管理
- rdagent 升级（`pip install --upgrade rdagent`）不会丢失补丁
- Linux 上完全无影响（补丁以 `sys.platform == "win32"` 守卫）

---

## 一、rdagent 运行时补丁（`quantaalpha/compat/rdagent_patches.py`）

### 补丁 1：`LocalConf.live_output` 默认值

**问题**：rdagent 默认 `live_output=True`，使用 `select.poll()` 实时读取子进程输出。Windows 上 `select.poll()` 不存在，抛出：
```
AttributeError: module 'select' has no attribute 'poll'
```

**修改**：将 `LocalConf.live_output` 在 Windows 上默认改为 `False`，子进程输出改用 `process.communicate()` 一次性读取。

| | Linux | Windows |
|:---|:---|:---|
| 默认值 | `True` | `False` |
| 读取方式 | `select.poll()` 实时流式 | `process.communicate()` 一次性 |

### 补丁 2：`CondaConf.change_bin_path` — `grep` → `findstr`

**问题**：rdagent 的 `CondaConf` 使用 `grep '^PATH='` 从 conda 环境中提取 PATH。Windows 没有 `grep` 命令，导致 `FileNotFoundError`。

**修改**：将命令替换为 Windows 自带的 `findstr "^PATH="`。

### 补丁 3：`LocalEnv.run()` — 跳过 `/bin/sh` 包装 + 内联 retry 逻辑

**问题**（两个）：

1. rdagent 将命令包装为 `/bin/sh -c 'timeout --kill-after=10 600 python main.py; ...'`。Windows 上不存在 `/bin/sh` 和 GNU `timeout`，导致执行失败。

2. rdagent 的 `Env.__run_with_retry` 是一个双下划线私有方法，Python name mangling 将其转换为 `_Env__run_with_retry`。从外部 monkey-patch 的函数中调用 `self._LocalEnv__run_with_retry()` 或 `self.__run_with_retry()` 都无法正确解析，抛出：
   ```
   AttributeError: 'QlibCondaEnv' object has no attribute '_LocalEnv__run_with_retry'
   ```

**修改**：
- 在 Windows 上跳过 `/bin/sh` 包装，直接执行原始命令，由 `subprocess.Popen(shell=True)` 通过 `cmd.exe` 处理
- 将 retry 逻辑（重试计数、超时检测、异常处理）完整内联到补丁函数中，不再调用 name-mangled 的 `__run_with_retry`

### 补丁 4：`LocalEnv._run()` — 符号链接、PATH 分隔符

**问题 4a — 符号链接需要管理员权限**：`_run()` 使用 `Path.symlink_to()` 挂载卷。Windows 创建目录符号链接需要管理员权限（或开发者模式），否则抛出：
```
OSError: [WinError 1314] 客户端没有所需的特权
```

**修改 4a**：对目录使用 `_winapi.CreateJunction()` 创建目录联接（directory junction），功能等效但无需特殊权限；对文件仍使用 `symlink_to()`。

**问题 4b — PATH 分隔符和系统 PATH**：原代码用 `:` 拼接 PATH 并添加 `/bin/`、`/usr/bin/` 等 Linux 路径，导致 Windows 上找不到 `python`、`qrun`、`conda` 等可执行文件。

**修改 4b**：Windows 上使用 `;` 拼接，并继承完整的 `os.environ["PATH"]`。

| | Linux | Windows |
|:---|:---|:---|
| 分隔符 | `:` | `;` |
| 默认路径 | `/bin/`、`/usr/bin/` | 继承 `os.environ["PATH"]` |

---

## 二、项目代码修改

### 2.1 `quantaalpha/factors/workspace.py` — QlibFBWorkspace.execute() 覆盖

**问题**：即使打了上述 rdagent 补丁，rdagent 的回测执行链路 `QlibCondaEnv → Env.run() → LocalEnv._run()` 仍然存在复杂的 symlink / PATH / shell 交互，在 Windows 上容易出问题。

**修改**：覆盖 `execute()` 方法。在 Windows 上不走 rdagent 的执行链路，而是直接使用项目自有的 `quantaalpha.utils.env.QlibLocalEnv`，通过简单的 `subprocess.run` 执行 `qrun` 和 `read_exp_res.py`。Linux 上自动退回父类 rdagent 实现。

```python
if sys.platform != "win32":
    return super().execute(...)   # Linux: 走 rdagent 原生链路
# Windows: 用项目自有的 QlibLocalEnv
from quantaalpha.utils.env import QlibLocalEnv
env = QlibLocalEnv()
env.run(entry=f"qrun {qlib_config_name}", ...)
env.run(entry="python read_exp_res.py", ...)
```

### 2.2 `quantaalpha/utils/env.py` — QlibLocalEnv 类

**问题**：rdagent 的 `QlibCondaEnv` 执行路径依赖 Docker 或 Linux shell 特性，Windows 上不可用。

**修改**：新增 `QlibLocalEnv` 类，提供本地执行环境：
- 使用 `subprocess.run()` 执行命令，支持超时
- 继承系统环境变量 `{**os.environ, **env}`，确保可执行文件可被找到
- 不涉及符号链接、shell 包装等 Linux 特性

### 2.3 `quantaalpha/core/experiment.py` — 符号链接 → 硬链接

**问题**：`link_all_files_in_folder_to_workspace()` 使用 `os.symlink()` 将数据文件链接到工作空间。Windows 创建符号链接需要管理员权限。

**修改**：按平台分发：Linux 使用 `os.symlink()`，Windows 使用 `os.link()`（硬链接，无需特殊权限）。

```python
if platform.system() == "Linux":
    os.symlink(data_file_path, workspace_data_file_path)
if platform.system() == "Windows":
    os.link(data_file_path, workspace_data_file_path)
```

### 2.4 `quantaalpha/factors/coder/factor.py` — PYTHONPATH 分隔符

**问题**：因子执行子进程需要设置 `PYTHONPATH` 以导入 `quantaalpha` 包。原代码硬编码 `:` 作为路径分隔符，Windows 上 `:` 被解释为盘符分隔符导致路径错误。

**修改**：根据平台选择分隔符：

```python
sep = ';' if sys.platform == 'win32' else ':'
env['PYTHONPATH'] = pythonpath + sep + env.get('PYTHONPATH', '')
```

### 2.5 `quantaalpha/pipeline/factor_mining.py` — 超时机制

**问题**：`force_timeout()` 装饰器使用 `signal.SIGALRM` 实现全局超时。Windows 不支持 `SIGALRM` 信号，抛出 `AttributeError`。

**修改**：Windows 上改用 daemon 线程实现超时：

```python
if sys.platform != "win32":
    # Linux: signal.SIGALRM
    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(seconds)
else:
    # Windows: daemon thread + join(timeout)
    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout=seconds)
    if worker.is_alive():
        os._exit(1)
```

### 2.6 `quantaalpha/backtest/custom_factor_calculator.py` — Unicode 编码

**问题**：进度输出使用 Unicode 符号（`✓`、`✗`、`⏳`），Windows 终端默认 GBK 编码无法显示，抛出：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2713'
```

**修改**：将 Unicode 进度符号替换为 ASCII：
- `✓` → `[OK]`
- `✗` → `[FAIL]`
- `⏳` → `[..]`

### 2.7 入口点补丁加载

**问题**：需要确保所有入口点在启动时自动应用 rdagent 补丁。

**修改**：在 `launcher.py` 和 `quantaalpha/cli.py` 中添加：

```python
from quantaalpha.compat.rdagent_patches import apply as _apply_rdagent_patches
_apply_rdagent_patches()
```

### 2.8 `.env` 配置

**问题**：Linux 上 `conda activate` 会自动设置 `CONDA_DEFAULT_ENV` 环境变量，rdagent 依赖此变量判断当前环境。Windows 上某些终端（如 PowerShell）不会自动设置。

**修改**：Windows 用户需在 `.env` 中手动添加：

```bash
CONDA_DEFAULT_ENV=quantaalpha
```

### 2.9 `frontend-v2/package.json` — 缺失前端依赖

**问题**：前端代码引用了 `@radix-ui/react-hover-card`，但 `package.json` 中未声明，`npm install` 后启动报错。

**修改**：在 `package.json` 的 `dependencies` 中添加 `@radix-ui/react-hover-card`。

---

## 文件变更汇总

| 文件 | 修改类型 | 说明 |
|:---|:---|:---|
| `quantaalpha/compat/__init__.py` | 新增 | 兼容层包 |
| `quantaalpha/compat/rdagent_patches.py` | 新增 | rdagent 运行时补丁（4 项） |
| `quantaalpha/utils/env.py` | 修改 | 新增 `QlibLocalEnv` 本地执行环境 |
| `quantaalpha/factors/workspace.py` | 修改 | Windows 上覆盖 `execute()` 使用 `QlibLocalEnv` |
| `quantaalpha/core/experiment.py` | 修改 | 符号链接 → 硬链接（Windows） |
| `quantaalpha/factors/coder/factor.py` | 修改 | PYTHONPATH 分隔符 `;` / `:` |
| `quantaalpha/pipeline/factor_mining.py` | 修改 | `SIGALRM` → daemon 线程超时 |
| `quantaalpha/backtest/custom_factor_calculator.py` | 修改 | Unicode → ASCII 进度符号 |
| `launcher.py` | 修改 | 启动时调用 `apply()` |
| `quantaalpha/cli.py` | 修改 | 启动时调用 `apply()` |
| `frontend-v2/package.json` | 修改 | 添加 `@radix-ui/react-hover-card` |
| `docs/WINDOWS_COMPAT.md` | 新增 | 本文档 |

---

## 已知限制

1. **`frontend-v2/backend/app.py` 中的符号链接**：后端 API 在初始化 qlib 数据目录时仍使用 `os.symlink()`，在 Windows 上可能需要管理员权限或开发者模式。若遇到 `WinError 1314`，可手动创建目录联接或复制数据目录。

2. **`quantaalpha/factors/runner.py` 中的符号链接**：因子运行器中有一处 `os.symlink()` 链接 `daily_pv.h5`，Windows 上对文件的符号链接通常不需要管理员权限，但如遇问题可参照 `experiment.py` 改用 `os.link()`。

3. **长路径问题**：Windows 默认最大路径长度 260 字符。如果工作空间嵌套较深，可能遇到 `FileNotFoundError`。建议在注册表中启用长路径支持或将项目放在较短的路径下。
