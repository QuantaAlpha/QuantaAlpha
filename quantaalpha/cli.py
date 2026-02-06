"""
QuantaAlpha CLI 入口

提供以下命令:
  quantaalpha mine       - 运行因子挖掘实验
  quantaalpha backtest   - 运行因子回测
  quantaalpha ui         - 启动日志可视化 Web UI
  quantaalpha health_check - 环境健康检查
"""

from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 配置文件（优先项目根目录，回退到当前目录）
_project_root = Path(__file__).resolve().parents[1]
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv(".env")

import fire
from quantaalpha.pipeline.factor_mining import main as mine
from quantaalpha.pipeline.factor_backtest import main as backtest
from quantaalpha.app.utils.health_check import health_check
from quantaalpha.app.utils.info import collect_info


def app():
    fire.Fire(
        {
            "mine": mine,
            "backtest": backtest,
            "health_check": health_check,
            "collect_info": collect_info,
        }
    )


if __name__ == "__main__":
    app()
