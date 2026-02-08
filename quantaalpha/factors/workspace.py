"""
QuantaAlpha 自定义 workspace

覆盖 rdagent 的 QlibFBWorkspace，解决以下问题：
1. rdagent 默认模板配置不适合当前环境（ProcessInf 与 pandas 1.5.x 不兼容）
2. 需要使用项目级自定义配置（老版本风格的稳健参数）
3. 模板覆盖机制：先加载 rdagent 默认模板（获取 read_exp_res.py 等基础文件），
   再用项目自定义模板覆盖 YAML 配置
4. 在 workspace 目录中初始化空 git 仓库，抑制 qlib recorder 的 git 警告输出
"""

import subprocess
from pathlib import Path

from rdagent.scenarios.qlib.experiment.workspace import QlibFBWorkspace as _RdagentQlibFBWorkspace
from rdagent.log import rdagent_logger as logger

# 项目级别的自定义配置模板目录
_CUSTOM_TEMPLATE_DIR = Path(__file__).resolve().parent / "factor_template"


class QlibFBWorkspace(_RdagentQlibFBWorkspace):
    """
    覆盖 rdagent 的 QlibFBWorkspace。

    主要改进：
    - 在 rdagent 模板基础上，用项目 factor_template/ 目录中的 YAML 覆盖默认配置
    - 这样 read_exp_res.py、README.md 等基础文件仍从 rdagent 模板获取
    - 而 conf_combined_factors.yaml、conf_baseline.yaml 使用项目自定义版本
    - 在 workspace 目录中初始化空 git 仓库，避免 qlib recorder 输出大量 git 帮助信息
    """

    def __init__(self, template_folder_path: Path, *args, **kwargs) -> None:
        # 先调用父类：从 rdagent factor_template 加载所有文件到 file_dict
        super().__init__(template_folder_path, *args, **kwargs)

        # 再用项目自定义模板覆盖（如果存在）
        if _CUSTOM_TEMPLATE_DIR.exists():
            self.inject_code_from_folder(_CUSTOM_TEMPLATE_DIR)
            logger.info(f"已用项目自定义模板覆盖 rdagent 默认配置: {_CUSTOM_TEMPLATE_DIR}")

    def before_execute(self) -> None:
        """在执行前初始化空 git 仓库，避免 qlib recorder 的 git 警告噪音。"""
        super().before_execute()
        # qlib recorder 在 workspace 中执行 git diff / git status，
        # 如果不是 git 仓库会输出大量帮助信息到 stderr。
        # 初始化一个空的 git 仓库来抑制这些输出。
        git_dir = self.workspace_path / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=str(self.workspace_path),
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass  # 非关键操作，失败则忽略
