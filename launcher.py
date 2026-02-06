#!/usr/bin/env python3
"""
QuantaAlpha 统一启动器

用法：
    python launcher.py mine --direction "价量因子挖掘"
    python launcher.py mine --direction "动量反转" --config configs/experiment.yaml
    python launcher.py backtest --factor-source alpha158_20
    python launcher.py health_check
"""

import sys
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    print("=" * 60)
    print("错误: 未找到 .env 配置文件")
    print()
    print("请先创建配置文件:")
    print(f"  cp configs/.env.example .env")
    print("  然后编辑 .env 填入你的数据路径和 API Key")
    print("=" * 60)
    sys.exit(1)

from quantaalpha.cli import app

if __name__ == "__main__":
    app()
