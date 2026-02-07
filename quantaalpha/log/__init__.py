"""
AlphaAgent 日志模块 - 兼容层

将 alphaagent.log 映射到 rdagent.log 的对应组件，
使得项目中所有 alphaagent.log 的导入都能正常工作。

额外提供 log_trace_path / set_trace_path 等 AlphaAgent 专用接口。
"""

from pathlib import Path
from rdagent.log import rdagent_logger as _rdagent_logger
from rdagent.log.utils import LogColors


class _AlphaAgentLoggerWrapper:
    """
    包装 rdagent_logger，添加 AlphaAgent 专用的 log_trace_path 和 set_trace_path 接口。
    其余属性和方法全部代理到 rdagent_logger。
    """

    def __init__(self, inner):
        object.__setattr__(self, "_inner", inner)

    # ---------- AlphaAgent 扩展 ----------
    @property
    def log_trace_path(self) -> Path:
        """返回当前日志跟踪路径"""
        return self._inner.storage.path

    def set_trace_path(self, path) -> None:
        """设置新的日志跟踪路径"""
        from rdagent.log.storage import FileStorage
        self._inner.storage = FileStorage(Path(path))

    # ---------- 代理到 rdagent_logger ----------
    def __getattr__(self, name):
        return getattr(self._inner, name)

    def __setattr__(self, name, value):
        if name in ("_inner",):
            object.__setattr__(self, name, value)
        else:
            setattr(self._inner, name, value)


logger = _AlphaAgentLoggerWrapper(_rdagent_logger)

__all__ = ["logger", "LogColors"]
